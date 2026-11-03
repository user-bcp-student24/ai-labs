package com.bcp.workshop.auth;

import io.smallrye.jwt.algorithm.SignatureAlgorithm;
import io.smallrye.jwt.build.Jwt;

import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.Instant;

public final class LegacyTokenUtil {
    private static final String SECRET_ENV = "WORKSHOP_JWT_SECRET";
    private static final String ISSUER_ENV = "WORKSHOP_JWT_ISSUER";
    private static final String AUDIENCE_ENV = "WORKSHOP_JWT_AUDIENCE";
    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final int MINIMUM_SECRET_BYTES = 32;
    public static final long TOKEN_LIFETIME_SECONDS = 3600;

    private LegacyTokenUtil() {}

    public static String create(String username, String role) {
        return create(
                username,
                role,
                System.getenv(SECRET_ENV),
                System.getenv(ISSUER_ENV),
                System.getenv(AUDIENCE_ENV)
        );
    }

    static String create(String username, String role, String secret, String issuer, String audience) {
        secret = requiredSetting(SECRET_ENV, secret);
        byte[] secretBytes = secret.getBytes(StandardCharsets.UTF_8);
        if (secretBytes.length < MINIMUM_SECRET_BYTES) {
            throw new IllegalStateException(SECRET_ENV + " must contain at least "
                    + MINIMUM_SECRET_BYTES + " bytes");
        }

        issuer = requiredSetting(ISSUER_ENV, issuer);
        audience = requiredSetting(AUDIENCE_ENV, audience);
        SecretKeySpec signingKey = new SecretKeySpec(secretBytes, HMAC_ALGORITHM);

        return Jwt.claims()
                .subject(username)
                .claim("role", role)
                .issuer(issuer)
                .audience(audience)
                .expiresAt(Instant.now().plusSeconds(TOKEN_LIFETIME_SECONDS))
                .jws()
                .algorithm(SignatureAlgorithm.HS256)
                .sign(signingKey);
    }

    private static String requiredSetting(String name, String value) {
        if (value == null || value.isBlank()) {
            throw new IllegalStateException(name + " is required to issue authentication tokens");
        }
        return value;
    }
}
