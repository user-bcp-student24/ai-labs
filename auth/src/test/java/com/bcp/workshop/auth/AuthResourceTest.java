package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import jakarta.ws.rs.core.Response;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;

import static io.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.Matchers.notNullValue;
import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

@QuarkusTest
class AuthResourceTest {
    private static final long TOKEN_LIFETIME_SECONDS = 3600;

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
    void issuesApiCompatibleHs256Token() throws Exception {
        Map<?, ?> login = given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"Workshop123!\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(200)
                .extract()
                .as(Map.class);

        String[] segments = ((String) login.get("token")).split("\\.");
        assertEquals(3, segments.length);

        ObjectMapper objectMapper = new ObjectMapper();
        Map<?, ?> header = objectMapper.readValue(Base64.getUrlDecoder().decode(segments[0]), Map.class);
        Map<?, ?> claims = objectMapper.readValue(Base64.getUrlDecoder().decode(segments[1]), Map.class);
        assertEquals("HS256", header.get("alg"));
        assertEquals("student", claims.get("sub"));
        assertEquals("STUDENT", claims.get("role"));
        assertEquals("api-pym", claims.get("iss"));
        assertEquals("PO", claims.get("aud"));
        assertEquals(TOKEN_LIFETIME_SECONDS, ((Number) login.get("expiresIn")).longValue());

        long currentTime = Instant.now().getEpochSecond();
        long expiration = ((Number) claims.get("exp")).longValue();
        assertTrue(expiration > currentTime);
        assertTrue(expiration <= currentTime + TOKEN_LIFETIME_SECONDS);

        Mac signer = Mac.getInstance("HmacSHA256");
        signer.init(new SecretKeySpec(
                System.getenv("WORKSHOP_JWT_SECRET").getBytes(StandardCharsets.UTF_8),
                "HmacSHA256"
        ));
        byte[] expectedSignature = signer.doFinal(
                (segments[0] + "." + segments[1]).getBytes(StandardCharsets.US_ASCII)
        );
        assertArrayEquals(expectedSignature, Base64.getUrlDecoder().decode(segments[2]));
    }

    @Test
    void requiresJwtSigningConfiguration() {
        String validSecret = "test-only-shared-key-with-at-least-32-bytes";

        assertThrows(IllegalStateException.class,
                () -> LegacyTokenUtil.create("student", "STUDENT", null, "api-pym", "PO"));
        assertThrows(IllegalStateException.class,
                () -> LegacyTokenUtil.create("student", "STUDENT", " ", "api-pym", "PO"));
        assertThrows(IllegalStateException.class,
                () -> LegacyTokenUtil.create("student", "STUDENT", validSecret, " ", "PO"));
        assertThrows(IllegalStateException.class,
                () -> LegacyTokenUtil.create("student", "STUDENT", validSecret, "api-pym", null));
        assertThrows(IllegalStateException.class,
                () -> LegacyTokenUtil.create("student", "STUDENT", "short", "api-pym", "PO"));
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
    void rejectsMissingLoginFields() {
        assertLoginStatus(null, 400);

        LoginRequest missingUsername = new LoginRequest();
        missingUsername.password = "Workshop123!";
        assertLoginStatus(missingUsername, 400);

        LoginRequest blankUsername = new LoginRequest();
        blankUsername.username = " ";
        blankUsername.password = "Workshop123!";
        assertLoginStatus(blankUsername, 400);

        LoginRequest missingPassword = new LoginRequest();
        missingPassword.username = "student";
        assertLoginStatus(missingPassword, 400);

        LoginRequest blankPassword = new LoginRequest();
        blankPassword.username = "student";
        blankPassword.password = " ";
        assertLoginStatus(blankPassword, 400);
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

    private static void assertLoginStatus(LoginRequest request, int expectedStatus) {
        AuthResource resource = new AuthResource();
        try (Response response = resource.login(request)) {
            assertEquals(expectedStatus, response.getStatus());
        }
    }
}
