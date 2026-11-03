package com.bcp.workshop.auth;

import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;

public final class PasswordHasher {
    private static final String ALGORITHM = "PBKDF2WithHmacSHA256";
    private static final String ENCODING_PREFIX = "pbkdf2_sha256";
    private static final int ITERATIONS = 210_000;
    private static final int MINIMUM_ITERATIONS = 100_000;
    private static final int MAXIMUM_ITERATIONS = 1_000_000;
    private static final int SALT_BYTES = 16;
    private static final int HASH_BITS = 256;
    private static final SecureRandom RANDOM = new SecureRandom();

    public String hash(String password) {
        byte[] salt = new byte[SALT_BYTES];
        RANDOM.nextBytes(salt);
        byte[] derivedKey = deriveKey(password, salt, ITERATIONS);
        return ENCODING_PREFIX + "$" + ITERATIONS + "$"
                + Base64.getEncoder().encodeToString(salt) + "$"
                + Base64.getEncoder().encodeToString(derivedKey);
    }

    public boolean verify(String password, String encodedPassword) {
        String[] parts = encodedPassword == null ? new String[0] : encodedPassword.split("\\$", -1);
        if (parts.length != 4 || !ENCODING_PREFIX.equals(parts[0])) {
            return false;
        }

        try {
            int iterations = Integer.parseInt(parts[1]);
            if (iterations < MINIMUM_ITERATIONS || iterations > MAXIMUM_ITERATIONS) {
                return false;
            }
            byte[] salt = Base64.getDecoder().decode(parts[2]);
            byte[] expectedKey = Base64.getDecoder().decode(parts[3]);
            if (salt.length != SALT_BYTES || expectedKey.length * Byte.SIZE != HASH_BITS) {
                return false;
            }
            byte[] actualKey = deriveKey(password, salt, iterations);
            return MessageDigest.isEqual(expectedKey, actualKey);
        } catch (IllegalArgumentException error) {
            return false;
        }
    }

    boolean isEncoded(String value) {
        if (value == null) {
            return false;
        }
        String[] parts = value.split("\\$", -1);
        if (parts.length != 4 || !ENCODING_PREFIX.equals(parts[0])) {
            return false;
        }
        try {
            int iterations = Integer.parseInt(parts[1]);
            byte[] salt = Base64.getDecoder().decode(parts[2]);
            byte[] hash = Base64.getDecoder().decode(parts[3]);
            return iterations >= MINIMUM_ITERATIONS
                    && iterations <= MAXIMUM_ITERATIONS
                    && salt.length == SALT_BYTES
                    && hash.length * Byte.SIZE == HASH_BITS;
        } catch (IllegalArgumentException error) {
            return false;
        }
    }

    private byte[] deriveKey(String password, byte[] salt, int iterations) {
        PBEKeySpec keySpec = new PBEKeySpec(password.toCharArray(), salt, iterations, HASH_BITS);
        try {
            return SecretKeyFactory.getInstance(ALGORITHM).generateSecret(keySpec).getEncoded();
        } catch (GeneralSecurityException error) {
            throw new IllegalStateException("Password hashing is unavailable", error);
        } finally {
            keySpec.clearPassword();
        }
    }
}