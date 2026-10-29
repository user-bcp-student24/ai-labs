package com.bcp.workshop.auth;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

final class TemporaryDatabase {
    private TemporaryDatabase() {}

    static String newJdbcUrl() {
        try {
            Class.forName("org.sqlite.JDBC");
            Path file = Files.createTempFile("auth-bootstrap-", ".db");
            Files.delete(file);
            return "jdbc:sqlite:" + file.toAbsolutePath();
        } catch (IOException | ClassNotFoundException error) {
            throw new IllegalStateException(error);
        }
    }
}
