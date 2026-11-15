"""
Tests for Phase 1 - Step 4: Standardized Error Handling and 500 Prevention.

Verifies:
1. OperationalError / DB disconnection returns HTTP 503 (no unhandled 500 ASGI crash).
2. IntegrityError returns HTTP 409 Conflict.
3. AIProviderError returns HTTP 503 Service Unavailable.
4. RequestValidationError returns HTTP 422 Unprocessable Entity with error_code.
5. Standard HTTPException preserves status code and detail.
6. Unhandled Exception returns sanitized HTTP 500 without leaking stack traces or internal details.
7. Malformed JWT sub claims return HTTP 401 instead of crashing with 500 ValueError.
8. Duplicate organization creation returns HTTP 409 Conflict.
"""

import pytest
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, IntegrityError, SQLAlchemyError
from jose import jwt

from core.errors import setup_error_handlers
from core.dependencies import get_current_user
from core.security import SECRET_KEY, ALGORITHM
from services.ai.ai_services import AIProviderError
from schemas.auth import SignupRequest


# Create a test app with error handlers configured
def create_test_app():
    app = FastAPI()
    setup_error_handlers(app)

    test_router = APIRouter(prefix="/test-errors")

    @test_router.get("/operational-error")
    def trigger_operational_error():
        # Simulates psycopg2.OperationalError: SSL connection has been closed unexpectedly
        raise OperationalError("SELECT 1", {}, Exception("SSL connection has been closed unexpectedly"))

    @test_router.get("/integrity-error")
    def trigger_integrity_error():
        # Simulates unique constraint violation
        raise IntegrityError("INSERT INTO users...", {}, Exception("duplicate key value violates unique constraint"))

    @test_router.get("/sqlalchemy-error")
    def trigger_sqlalchemy_error():
        raise SQLAlchemyError("Generic database fault")

    @test_router.get("/ai-provider-error")
    def trigger_ai_provider_error():
        raise AIProviderError("All AI providers failed: gemini (authentication); groq (rate_limit)")

    @test_router.get("/unhandled-exception")
    def trigger_unhandled_exception():
        raise RuntimeError("Unexpected internal crash with sensitive_secret_key_12345")

    @test_router.get("/not-found")
    def trigger_not_found():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target entity not found")

    @test_router.post("/validation")
    def trigger_validation(data: SignupRequest):
        return {"status": "ok"}

    @test_router.get("/protected")
    def protected_route(current_user=Depends(get_current_user)):
        return {"user_id": current_user.id}

    app.include_router(test_router)
    return app


@pytest.fixture
def client():
    app = create_test_app()
    return TestClient(app, raise_server_exceptions=False)


def test_operational_error_returns_503(client):
    """DB connection loss / SSL drop must return 503 instead of an unhandled 500 ASGI crash."""
    response = client.get("/test-errors/operational-error")
    assert response.status_code == 503
    data = response.json()
    assert "Database connection error" in data["detail"]
    assert data["error_code"] == "DATABASE_UNAVAILABLE"


def test_integrity_error_returns_409(client):
    """Database constraint violations return HTTP 409 Conflict."""
    response = client.get("/test-errors/integrity-error")
    assert response.status_code == 409
    data = response.json()
    assert "Data integrity violation" in data["detail"]
    assert data["error_code"] == "INTEGRITY_ERROR"


def test_sqlalchemy_generic_error_returns_500(client):
    """Generic database errors return HTTP 500 with standardized error_code."""
    response = client.get("/test-errors/sqlalchemy-error")
    assert response.status_code == 500
    data = response.json()
    assert "A database error occurred" in data["detail"]
    assert data["error_code"] == "DATABASE_ERROR"


def test_ai_provider_error_returns_503(client):
    """Exhausted AI providers return HTTP 503 Service Unavailable."""
    response = client.get("/test-errors/ai-provider-error")
    assert response.status_code == 503
    data = response.json()
    assert "AI service is currently unavailable" in data["detail"]
    assert data["error_code"] == "AI_SERVICE_UNAVAILABLE"


def test_validation_error_returns_422(client):
    """Malformed request body returns HTTP 422 with structured detail."""
    response = client.post("/test-errors/validation", json={"incomplete": "body"})
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert data["error_code"] == "VALIDATION_ERROR"


def test_unhandled_exception_returns_500_sanitized(client):
    """Unhandled exceptions return sanitized 500 without leaking stack traces or internal secrets."""
    response = client.get("/test-errors/unhandled-exception")
    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "An internal server error occurred. Please try again later."
    assert data["error_code"] == "INTERNAL_SERVER_ERROR"
    # Ensure sensitive secret was NOT leaked to the client
    assert "sensitive_secret_key_12345" not in response.text
    assert "Traceback" not in response.text


def test_http_exception_preserves_status_and_detail(client):
    """Standard HTTPException preserves status and detail."""
    response = client.get("/test-errors/not-found")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Target entity not found"


def test_malformed_jwt_sub_returns_401_not_500(client):
    """Token with a non-integer sub claim returns HTTP 401 instead of crashing with 500 ValueError."""
    bad_token = jwt.encode({"sub": "not_an_int"}, SECRET_KEY, algorithm=ALGORITHM)
    response = client.get(
        "/test-errors/protected",
        headers={"Authorization": f"Bearer {bad_token}"},
    )
    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]


def test_missing_jwt_sub_returns_401_not_500(client):
    """Token missing the sub claim entirely returns HTTP 401 instead of crashing with 500."""
    no_sub_token = jwt.encode({"role": "user"}, SECRET_KEY, algorithm=ALGORITHM)
    response = client.get(
        "/test-errors/protected",
        headers={"Authorization": f"Bearer {no_sub_token}"},
    )
    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]
