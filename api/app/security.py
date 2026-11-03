from __future__ import annotations

import os

import jwt
from fastapi import Header, HTTPException

JWT_SECRET_ENV = "WORKSHOP_JWT_SECRET"
JWT_ISSUER_ENV = "WORKSHOP_JWT_ISSUER"
JWT_AUDIENCE_ENV = "WORKSHOP_JWT_AUDIENCE"
JWT_ALGORITHM = "HS256"
MINIMUM_SECRET_BYTES = 32
MAXIMUM_TOKEN_LENGTH = 8192
REQUIRED_CLAIMS = ["exp", "iss", "aud", "sub"]


def verified_identity(authorization: str = Header(default="")) -> dict[str, str]:
    scheme, separator, encoded_token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not encoded_token:
        raise HTTPException(status_code=401, detail="Invalid token")

    secret = os.getenv(JWT_SECRET_ENV, "")
    issuer = os.getenv(JWT_ISSUER_ENV, "")
    audience = os.getenv(JWT_AUDIENCE_ENV, "")
    if not secret or len(secret.encode("utf-8")) < MINIMUM_SECRET_BYTES or not issuer or not audience:
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    if len(encoded_token) > MAXIMUM_TOKEN_LENGTH:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        claims = jwt.decode(
            encoded_token,
            secret,
            algorithms=[JWT_ALGORITHM],
            issuer=issuer,
            audience=audience,
            options={"require": REQUIRED_CLAIMS},
        )
        username = claims["sub"]
        role = claims.get("role", "")
        if not isinstance(username, str) or not username or not isinstance(role, str):
            raise jwt.InvalidTokenError("invalid identity claims")
        return {"username": username, "role": role}
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=401, detail="Invalid token") from error