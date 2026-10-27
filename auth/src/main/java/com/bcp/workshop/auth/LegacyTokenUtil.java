package com.bcp.workshop.auth;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.time.Instant;
import java.util.Base64;

public final class LegacyTokenUtil {
    public static final long TTL_SECONDS = 3600;
    private static final String HMAC_ALGORITHM = "HmacSHA256";

    private LegacyTokenUtil() {}

    public static String create(String username, String role, String secret) {
        long expiry = Instant.now().plusSeconds(TTL_SECONDS).getEpochSecond();
        String payload = Base64.getEncoder().encodeToString(
                (username + "|" + role + "|" + expiry).getBytes(StandardCharsets.UTF_8));
        return payload + "." + sign(payload, secret);
    }

    private static String sign(String payload, String secret) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), HMAC_ALGORITHM));
            return Base64.getUrlEncoder().withoutPadding()
                    .encodeToString(mac.doFinal(payload.getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException error) {
            throw new IllegalStateException("Cannot sign token", error);
        }
    }
}
