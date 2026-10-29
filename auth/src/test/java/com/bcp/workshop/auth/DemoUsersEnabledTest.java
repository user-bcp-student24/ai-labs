package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import io.quarkus.test.junit.TestProfile;
import org.junit.jupiter.api.Test;

import static com.bcp.workshop.auth.LoginClient.login;
import static org.hamcrest.Matchers.notNullValue;

@QuarkusTest
@TestProfile(DemoUsersEnabledProfile.class)
class DemoUsersEnabledTest {
    @Test
    void demoAccountsAuthenticateOnlyWhenEnabledExplicitly() {
        login("student", "Workshop123!")
                .statusCode(200)
                .body("token", notNullValue());
    }
}
