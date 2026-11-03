package com.bcp.workshop.auth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PasswordHasherTest {
    private final PasswordHasher passwordHasher = new PasswordHasher();

    @Test
    void createsDifferentSaltedHashesForSamePassword() {
        String firstHash = passwordHasher.hash("Workshop123!");
        String secondHash = passwordHasher.hash("Workshop123!");

        assertNotEquals(firstHash, secondHash);
        assertTrue(passwordHasher.verify("Workshop123!", firstHash));
        assertTrue(passwordHasher.verify("Workshop123!", secondHash));
    }

    @Test
    void rejectsWrongPasswordAndPlaintextValue() {
        String encodedPassword = passwordHasher.hash("Workshop123!");

        assertFalse(passwordHasher.verify("wrong-password", encodedPassword));
        assertFalse(passwordHasher.verify("Workshop123!", "Workshop123!"));
    }

    @Test
    void recognizesOnlyValidEncodedHashesDuringMigration() {
        String encodedPassword = passwordHasher.hash("Workshop123!");

        assertTrue(passwordHasher.isEncoded(encodedPassword));
        assertFalse(passwordHasher.isEncoded("not-a-hash"));
        assertFalse(passwordHasher.isEncoded("pbkdf2_sha256$999999999$bad$bad"));
    }
}