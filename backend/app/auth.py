import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

TOKEN_SECRET = os.getenv("TOKEN_SECRET", "")
bearer = HTTPBearer(auto_error=False)

def _secret():
    secret = TOKEN_SECRET or os.getenv("TOKEN_SECRET", "")
    if not secret or secret == "change-this-before-deploying":
        raise HTTPException(503, "Authentication is not configured. Set a strong TOKEN_SECRET in backend/.env.")
    return secret.encode()

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    rounds = 310_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    return f"pbkdf2_sha256${rounds}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt, expected = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(),
            base64.urlsafe_b64decode(salt), int(rounds)
        )
        return hmac.compare_digest(actual, base64.urlsafe_b64decode(expected))
    except Exception:
        return False

def create_token(user_id: int) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": str(user_id), "iat": int(time.time()), "exp": int(time.time()) + 60 * 60 * 24 * 7}
    encode = lambda obj: base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode()).rstrip(b"=").decode()
    body = f"{encode(header)}.{encode(payload)}"
    signature = hmac.new(_secret(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"

def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Please sign in to continue.")
    try:
        header, payload, signature = credentials.credentials.split(".")
        body = f"{header}.{payload}"
        expected = base64.urlsafe_b64encode(
            hmac.new(_secret(), body.encode(), hashlib.sha256).digest()
        ).rstrip(b"=").decode()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature")
        decoded = payload + "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(decoded))
        if int(data["exp"]) < int(time.time()):
            raise ValueError("expired")
        return int(data["sub"])
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, "Your session is invalid or expired. Please sign in again.")
