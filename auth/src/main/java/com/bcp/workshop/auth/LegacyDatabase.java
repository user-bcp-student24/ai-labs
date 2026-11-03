package com.bcp.workshop.auth;

import jakarta.annotation.PostConstruct;
import jakarta.enterprise.context.ApplicationScoped;
import org.jboss.logging.Logger;

import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;

@ApplicationScoped
public class LegacyDatabase {
    private static final String DB_URL = System.getenv().getOrDefault("AUTH_DB_URL", "jdbc:sqlite:./data/workshop.db");
    private static final Logger LOG = Logger.getLogger(LegacyDatabase.class);
    private static final PasswordHasher PASSWORD_HASHER = new PasswordHasher();

    @PostConstruct
    void initialize() {
        try {
            Files.createDirectories(Path.of("data"));
            try (Connection connection = DriverManager.getConnection(DB_URL); Statement statement = connection.createStatement()) {
                statement.executeUpdate("CREATE TABLE IF NOT EXISTS legacy_users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT NOT NULL, display_name TEXT NOT NULL, role TEXT NOT NULL)");
                insertDefaultUser(connection, "student", "Workshop123!", "Workshop Student", "STUDENT");
                insertDefaultUser(connection, "trainer", "Trainer123!", "Workshop Trainer", "TRAINER");
                migratePlaintextPasswords(connection, PASSWORD_HASHER);
            }
        } catch (Exception error) {
            LOG.error("Could not initialize authentication database", error);
            throw new IllegalStateException("Could not initialize authentication database", error);
        }
    }

    public UserRecord findByCredentials(String username, String password) {
        String sql = "SELECT id, username, display_name, role, password FROM legacy_users WHERE username = ?";
        try (Connection connection = DriverManager.getConnection(DB_URL);
             PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, username);
            try (ResultSet result = statement.executeQuery()) {
                if (!result.next() || !PASSWORD_HASHER.verify(password, result.getString("password"))) {
                    return null;
                }
                return new UserRecord(result.getLong("id"), result.getString("username"), result.getString("display_name"), result.getString("role"));
            }
        } catch (SQLException error) {
            LOG.error("Could not query authentication database", error);
            throw new IllegalStateException("Could not query authentication database", error);
        }
    }

    private static void insertDefaultUser(
            Connection connection,
            String username,
            String password,
            String displayName,
            String role
    ) throws SQLException {
        String sql = "INSERT OR IGNORE INTO legacy_users(username, password, display_name, role) VALUES (?, ?, ?, ?)";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, username);
            statement.setString(2, PASSWORD_HASHER.hash(password));
            statement.setString(3, displayName);
            statement.setString(4, role);
            statement.executeUpdate();
        }
    }

    static void migratePlaintextPasswords(Connection connection, PasswordHasher passwordHasher) throws SQLException {
        List<PasswordEntry> plaintextPasswords = new ArrayList<>();
        try (Statement statement = connection.createStatement();
             ResultSet result = statement.executeQuery("SELECT id, password FROM legacy_users")) {
            while (result.next()) {
                String storedPassword = result.getString("password");
                if (!passwordHasher.isEncoded(storedPassword)) {
                    plaintextPasswords.add(new PasswordEntry(result.getLong("id"), storedPassword));
                }
            }
        }

        String updateSql = "UPDATE legacy_users SET password = ? WHERE id = ?";
        try (PreparedStatement statement = connection.prepareStatement(updateSql)) {
            for (PasswordEntry entry : plaintextPasswords) {
                statement.setString(1, passwordHasher.hash(entry.password()));
                statement.setLong(2, entry.id());
                statement.addBatch();
            }
            statement.executeBatch();
        }
    }

    private record PasswordEntry(long id, String password) {}
}
