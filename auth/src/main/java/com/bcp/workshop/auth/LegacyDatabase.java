package com.bcp.workshop.auth;

import jakarta.annotation.PostConstruct;
import jakarta.enterprise.context.ApplicationScoped;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.jboss.logging.Logger;

import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;

@ApplicationScoped
public class LegacyDatabase {
    private static final Logger LOG = Logger.getLogger(LegacyDatabase.class);

    @ConfigProperty(name = "auth.db.url", defaultValue = "jdbc:sqlite:./data/workshop.db")
    String dbUrl;

    @ConfigProperty(name = "workshop.bootstrap.demo-users.enabled", defaultValue = "false")
    boolean demoUsersEnabled;

    @PostConstruct
    void initialize() {
        try {
            Files.createDirectories(Path.of("data"));
            try (Connection connection = DriverManager.getConnection(dbUrl); Statement statement = connection.createStatement()) {
                statement.executeUpdate("CREATE TABLE IF NOT EXISTS legacy_users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT NOT NULL, display_name TEXT NOT NULL, role TEXT NOT NULL)");
                if (demoUsersEnabled) {
                    statement.executeUpdate("INSERT OR IGNORE INTO legacy_users(username,password,display_name,role) VALUES ('student','Workshop123!','Workshop Student','STUDENT')");
                    statement.executeUpdate("INSERT OR IGNORE INTO legacy_users(username,password,display_name,role) VALUES ('trainer','Trainer123!','Workshop Trainer','TRAINER')");
                }
            }
        } catch (Exception error) {
            LOG.errorf("Legacy database initialization failed: %s", error.getClass().getName());
        }
    }

    public UserRecord findByCredentials(String username, String password) {
        String sql = "SELECT id, username, display_name, role FROM legacy_users WHERE username = ? AND password = ?";
        try (Connection connection = DriverManager.getConnection(dbUrl);
             PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, username);
            statement.setString(2, password);
            try (ResultSet result = statement.executeQuery()) {
                if (result.next()) {
                    return new UserRecord(result.getLong("id"), result.getString("username"), result.getString("display_name"), result.getString("role"));
                }
            }
        } catch (Exception error) {
            LOG.errorf("Credential lookup failed: %s", error.getClass().getName());
        }
        return null;
    }
}
