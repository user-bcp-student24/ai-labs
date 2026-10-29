package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import io.quarkus.test.junit.TestProfile;
import org.junit.jupiter.api.Test;

import static com.bcp.workshop.auth.LoginClient.login;
import static org.junit.jupiter.api.Assertions.assertFalse;

@QuarkusTest
@TestProfile(DemoUsersEnabledProfile.class)
class BootstrapLogOutputTest {
    @Test
    void initializationAndLoginLogsOmitCredentialsSecretAndToken() {
        String token = login("student", "Workshop123!")
                .statusCode(200)
                .extract().path("token");
        login("student", "wrong-password")
                .statusCode(401);

        String output = LogCapture.content();
        assertFalse(output.isEmpty(), "log capture received no records");
        assertFalse(output.contains("Workshop123!"));
        assertFalse(output.contains("wrong-password"));
        assertFalse(output.contains("test-only-token-secret"));
        assertFalse(output.contains(token));
    }
}
