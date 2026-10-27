package com.bcp.workshop.auth;

import org.junit.jupiter.api.Test;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class LegacyTokenUtilTest {
    private static final String TEST_SECRET = "test-only-token-secret";

    @Test
    void createsPayloadAndHmacSignature() throws Exception {
        String token = LegacyTokenUtil.create("student", "STUDENT", TEST_SECRET);
        String[] segments = token.split("\\.");

        assertEquals(2, segments.length);
        String decoded = new String(Base64.getDecoder().decode(segments[0]), StandardCharsets.UTF_8);
        String[] fields = decoded.split("\\|");
        assertEquals("student", fields[0]);
        assertEquals("STUDENT", fields[1]);
        assertTrue(Long.parseLong(fields[2]) > Instant.now().getEpochSecond());
        assertEquals(hmacSha256Base64Url(segments[0], TEST_SECRET), segments[1]);
    }

    @Test
    void signatureDependsOnSecret() throws Exception {
        String token = LegacyTokenUtil.create("student", "STUDENT", TEST_SECRET);
        String payload = token.split("\\.")[0];
        assertNotEquals(hmacSha256Base64Url(payload, "other-secret"), token.split("\\.")[1]);
    }

    private static String hmacSha256Base64Url(String payload, String secret) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        return Base64.getUrlEncoder().withoutPadding()
                .encodeToString(mac.doFinal(payload.getBytes(StandardCharsets.UTF_8)));
    }
}
