package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import io.quarkus.test.junit.TestProfile;
import jakarta.inject.Inject;
import org.eclipse.microprofile.config.ConfigProvider;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;

import static com.bcp.workshop.auth.LoginClient.login;
import static org.hamcrest.Matchers.nullValue;
import static org.junit.jupiter.api.Assertions.assertEquals;

@QuarkusTest
@TestProfile(NoDemoUsersProfile.class)
class BootstrapWithoutDemoUsersTest {
    @Inject
    LegacyDatabase database;

    @BeforeEach
    void initializeFreshDatabase() {
        database.findByCredentials("bootstrap-probe", "");
    }

    @Test
    void freshProductionLikeDatabaseCreatesNoFixedBootstrapAccounts() throws SQLException {
        assertEquals(0, countFixedBootstrapAccounts());
    }

    @Test
    void fixedBootstrapCredentialsDoNotReturnToken() {
        login("student", "Workshop123!")
                .statusCode(401)
                .body("token", nullValue());
        login("trainer", "Trainer123!")
                .statusCode(401)
                .body("token", nullValue());
    }

    @Test
    void loginWithoutProvisionedAccountReturnsNoTokenOrExpiry() {
        login("no-such-user", "Workshop123!")
                .statusCode(401)
                .body("token", nullValue())
                .body("expiresIn", nullValue());
    }

    private static int countFixedBootstrapAccounts() throws SQLException {
        String url = ConfigProvider.getConfig().getValue("auth.db.url", String.class);
        try (Connection connection = DriverManager.getConnection(url);
             Statement statement = connection.createStatement();
             ResultSet result = statement.executeQuery(
                     "SELECT COUNT(*) FROM legacy_users WHERE username IN ('student','trainer')")) {
            result.next();
            return result.getInt(1);
        }
    }
}
