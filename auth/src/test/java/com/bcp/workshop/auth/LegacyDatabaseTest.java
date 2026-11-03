package com.bcp.workshop.auth;

import org.junit.jupiter.api.Test;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class LegacyDatabaseTest {
    private final PasswordHasher passwordHasher = new PasswordHasher();

    @Test
    void migratesPlaintextPasswordsAndKeepsExistingHashes() throws Exception {
        Class.forName("org.sqlite.JDBC");
        try (Connection connection = DriverManager.getConnection("jdbc:sqlite::memory:");
             Statement statement = connection.createStatement()) {
            statement.executeUpdate("CREATE TABLE legacy_users (id INTEGER PRIMARY KEY, password TEXT NOT NULL)");
            statement.executeUpdate("INSERT INTO legacy_users(id, password) VALUES (1, 'Workshop123!')");
            String alreadyHashed = passwordHasher.hash("Trainer123!");
            try (PreparedStatement insert = connection.prepareStatement(
                    "INSERT INTO legacy_users(id, password) VALUES (?, ?)")) {
                insert.setInt(1, 2);
                insert.setString(2, alreadyHashed);
                insert.executeUpdate();
            }

            LegacyDatabase.migratePlaintextPasswords(connection, passwordHasher);

            try (ResultSet result = statement.executeQuery("SELECT id, password FROM legacy_users ORDER BY id")) {
                result.next();
                String migratedPassword = result.getString("password");
                assertTrue(passwordHasher.isEncoded(migratedPassword));
                assertTrue(passwordHasher.verify("Workshop123!", migratedPassword));
                result.next();
                assertEquals(alreadyHashed, result.getString("password"));
            }
        }
    }
}