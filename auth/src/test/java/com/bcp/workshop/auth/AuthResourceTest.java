package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import jakarta.ws.rs.core.Response;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static io.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.Matchers.notNullValue;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;

@QuarkusTest
class AuthResourceTest {
    @Test
    void logsInWithWorkshopUser() {
        given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"Workshop123!\",\"client\":\"angular-workshop\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(200)
                .body("user.username", is("student"))
                .body("token", notNullValue());
    }

    @Test
    void rejectsInvalidCredentials() {
        given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"incorrect\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(401)
                .body("message", is("Invalid user student or password"));
    }

    @Test
    void treatsQuoteInUsernameAsData() {
        given()
                .contentType("application/json")
                .body("{\"username\":\"student'\",\"password\":\"Workshop123!\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(401);
    }

    @Test
    void doesNotAllowCorsFromUnlistedOrigin() {
        io.restassured.response.Response response = given()
                .header("Origin", "https://untrusted.invalid")
                .header("Access-Control-Request-Method", "POST")
                .when().options("/auth/login")
                .then()
                .extract()
                .response();

        assertNull(response.getHeader("Access-Control-Allow-Origin"));
    }

    @Test
    void doesNotReturnInternalExceptionDetails() {
        AuthResource resource = new AuthResource();
        resource.database = new LegacyDatabase() {
            @Override
            public UserRecord findByCredentials(String username, String password) {
                throw new IllegalStateException("sensitive database detail");
            }
        };
        LoginRequest request = new LoginRequest();
        request.username = "student";
        request.password = "Workshop123!";

        try (Response response = resource.login(request)) {
            assertEquals(500, response.getStatus());
            Map<?, ?> body = (Map<?, ?>) response.getEntity();
            assertEquals("Internal server error", body.get("message"));
            assertFalse(body.containsKey("exception"));
            assertFalse(body.toString().contains("sensitive database detail"));
        }
    }
}
