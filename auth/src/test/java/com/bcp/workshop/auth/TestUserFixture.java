package com.bcp.workshop.auth;

import org.eclipse.microprofile.config.ConfigProvider;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;

final class TestUserFixture {
    static final String USERNAME = "auth-test-user";
    static final String ROLE = "STUDENT";
    static final String DISPLAY_NAME = "Auth <Test> & User";

    private TestUserFixture() {}

    static String password() {
        return ConfigProvider.getConfig().getValue("workshop.test-user.password", String.class);
    }

    static void prepare() throws SQLException {
        String url = ConfigProvider.getConfig().getValue("auth.db.url", String.class);
        try (Connection connection = DriverManager.getConnection(url);
             PreparedStatement delete = connection.prepareStatement("DELETE FROM legacy_users WHERE username = ?");
             PreparedStatement insert = connection.prepareStatement(
                     "INSERT INTO legacy_users(username,password,display_name,role) VALUES (?,?,?,?)")) {
            delete.setString(1, USERNAME);
            delete.executeUpdate();
            insert.setString(1, USERNAME);
            insert.setString(2, password());
            insert.setString(3, DISPLAY_NAME);
            insert.setString(4, ROLE);
            insert.executeUpdate();
        }
    }
}
