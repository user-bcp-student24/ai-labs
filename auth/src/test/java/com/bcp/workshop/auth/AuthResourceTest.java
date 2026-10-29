package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import io.restassured.response.ValidatableResponse;
import jakarta.inject.Inject;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.sql.SQLException;
import java.time.Instant;
import java.util.Base64;

import static io.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.Matchers.notNullValue;
import static org.hamcrest.Matchers.nullValue;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

@QuarkusTest
class AuthResourceTest {
    private static final String TEST_SECRET = "test-only-token-secret";

    @Inject
    LegacyDatabase database;

    @BeforeAll
    static void registerSqliteDriver() throws ClassNotFoundException {
        Class.forName("org.sqlite.JDBC");
    }

    @BeforeEach
    void prepareTestAccount() throws SQLException {
        database.findByCredentials(TestUserFixture.USERNAME, "");
        TestUserFixture.prepare();
    }

    @Test
    void logsInWithWorkshopUser() {
        login(String.format("{\"username\":\"%s\",\"password\":\"%s\",\"client\":\"angular-workshop\"}",
                TestUserFixture.USERNAME, TestUserFixture.password()))
                .statusCode(200)
                .body("user.username", is(TestUserFixture.USERNAME))
                .body("user.displayName", is("Auth &lt;Test&gt; &amp; User"))
                .body("user.role", is("STUDENT"))
                .body("token", notNullValue())
                .body("expiresIn", is(3600))
                .body("debug", notNullValue());
    }

    @Test
    void returnedTokenCarriesIdentityAndHmacSignature() throws Exception {
        String token = login(credentials(TestUserFixture.USERNAME, TestUserFixture.password()))
                .statusCode(200)
                .extract().path("token");
        String[] segments = token.split("\\.");
        String[] fields = new String(Base64.getDecoder().decode(segments[0]), StandardCharsets.UTF_8).split("\\|");

        assertEquals(TestUserFixture.USERNAME, fields[0]);
        assertEquals("STUDENT", fields[1]);
        assertTrue(Long.parseLong(fields[2]) > Instant.now().getEpochSecond());
        assertEquals(hmacSha256Base64Url(segments[0], TEST_SECRET), segments[1]);
    }

    @Test
    void rejectsEmptyBodyWithBadRequest() {
        login("")
                .statusCode(400)
                .body("message", is("Request is null"));
    }

    @Test
    void rejectsBlankUsernameWithBadRequest() {
        login(credentials("   ", TestUserFixture.password()))
                .statusCode(400)
                .body("message", is("Username is required"));
    }

    @Test
    void rejectsBlankPasswordWithBadRequest() {
        login(credentials(TestUserFixture.USERNAME, "  "))
                .statusCode(400)
                .body("message", is("Password is required"));
    }

    @Test
    void rejectsUnknownUserWithoutToken() {
        login(credentials("no-such-user", TestUserFixture.password()))
                .statusCode(401)
                .body("message", is("Invalid user no-such-user or password"))
                .body("token", nullValue())
                .body("expiresIn", nullValue());
    }

    @Test
    void rejectsWrongPasswordWithoutToken() {
        login(credentials(TestUserFixture.USERNAME, "wrong-password"))
                .statusCode(401)
                .body("message", is("Invalid user " + TestUserFixture.USERNAME + " or password"))
                .body("token", nullValue())
                .body("expiresIn", nullValue());
    }

    @Test
    void rejectsSqlMetacharactersInCredentialsAsData() {
        login(credentials("nobody' OR '1'='1", "x' OR '1'='1"))
                .statusCode(401)
                .body("token", nullValue())
                .body("expiresIn", nullValue());
    }

    private static String credentials(String username, String password) {
        return "{\"username\":\"" + username + "\",\"password\":\"" + password + "\"}";
    }

    private static ValidatableResponse login(String body) {
        return given()
                .contentType("application/json")
                .body(body)
                .when().post("/auth/login")
                .then();
    }

    private static String hmacSha256Base64Url(String payload, String secret) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        return Base64.getUrlEncoder().withoutPadding()
                .encodeToString(mac.doFinal(payload.getBytes(StandardCharsets.UTF_8)));
    }
}
