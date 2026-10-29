package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTestProfile;

import java.util.Map;

public class DemoUsersEnabledProfile implements QuarkusTestProfile {
    @Override
    public Map<String, String> getConfigOverrides() {
        LogCapture.install();
        return Map.of(
                "auth.db.url", TemporaryDatabase.newJdbcUrl(),
                "workshop.bootstrap.demo-users.enabled", "true");
    }
}
