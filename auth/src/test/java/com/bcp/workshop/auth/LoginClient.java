package com.bcp.workshop.auth;

import io.restassured.response.ValidatableResponse;

import static io.restassured.RestAssured.given;

final class LoginClient {
    private LoginClient() {}

    static ValidatableResponse login(String username, String password) {
        return given()
                .contentType("application/json")
                .body(String.format("{\"username\":\"%s\",\"password\":\"%s\"}", username, password))
                .when().post("/auth/login")
                .then();
    }
}
