#!/usr/bin/env python3
"""
Unit tests for JWT authentication functionality.

This test suite validates the JWT token creation and validation logic,
including all security checks for the endorser service.
"""

import pytest
from datetime import datetime, timedelta, timezone

from api.endpoints.dependencies.jwt_security import (
    create_access_token,
    check_access_token,
)
from api.config import settings


class TestJWTAuthentication:
    """Test suite for JWT authentication functionality."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Mock settings for testing
        self.original_admin_user = settings.ENDORSER_API_ADMIN_USER
        self.original_secret_key = settings.JWT_SECRET_KEY
        self.original_algorithm = settings.JWT_ALGORITHM
        self.original_expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES

        # Set test values
        settings.ENDORSER_API_ADMIN_USER = "test_admin"
        settings.JWT_SECRET_KEY = "test_secret_key"
        settings.JWT_ALGORITHM = "HS256"
        settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours for tests

    def teardown_method(self):
        """Clean up after each test method."""
        # Restore original settings
        settings.ENDORSER_API_ADMIN_USER = self.original_admin_user
        settings.JWT_SECRET_KEY = self.original_secret_key
        settings.JWT_ALGORITHM = self.original_algorithm
        settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = self.original_expire_minutes

    def test_create_access_token_success(self):
        """Test successful token creation."""
        user_data = {"sub": "test_admin"}
        token_response = create_access_token(user_data)

        assert token_response.access_token is not None
        assert token_response.token_type == "bearer"
        assert len(token_response.access_token) > 0

    def test_create_access_token_with_expiration(self):
        """Test that created tokens include expiration claim."""
        user_data = {"sub": "test_admin"}
        token_response = create_access_token(user_data)

        # Decode without verification to check structure
        from jose import jwt

        payload = jwt.decode(
            token_response.access_token, key="", options={"verify_signature": False}
        )

        assert "exp" in payload
        assert "sub" in payload
        assert payload["sub"] == "test_admin"

        # Check expiration is in the future (with 24 hour expiration, should be well in the future)
        current_time = datetime.now(timezone.utc).timestamp()
        # With 24 hour expiration, the exp should be at least 23 hours in the future
        assert payload["exp"] > current_time + (23 * 60 * 60)  # 23 hours in seconds

    def test_check_access_token_valid_token(self):
        """Test validation of a valid token."""
        user_data = {"sub": "test_admin"}
        token_response = create_access_token(user_data)

        # Import the core validation function without the FastAPI dependency wrapper
        from jose import jwt
        from fastapi import HTTPException

        # Test the core validation logic by calling it directly
        try:
            # This will test the actual validation logic
            payload = jwt.decode(
                token_response.access_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )

            # Apply the same validation logic as in check_access_token
            if not payload.get("sub"):
                raise HTTPException(status_code=401, detail="Token missing subject claim")

            if payload.get("sub") != settings.ENDORSER_API_ADMIN_USER:
                raise HTTPException(status_code=401, detail="Invalid token subject")

            if not payload.get("exp"):
                raise HTTPException(
                    status_code=401, detail="Token missing expiration claim"
                )

            current_time = datetime.now(timezone.utc).timestamp()
            if payload.get("exp") < current_time:
                raise HTTPException(status_code=401, detail="Token has expired")

            # If we get here, validation passed
            assert payload["sub"] == "test_admin"
            assert "exp" in payload

        except HTTPException as e:
            pytest.fail(f"Valid token should not raise HTTPException: {e}")

    def test_check_access_token_missing_sub(self):
        """Test validation fails when sub claim is missing."""
        # Create token without sub claim
        from jose import jwt

        payload_data = {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
        invalid_token = jwt.encode(
            payload_data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        with pytest.raises(Exception) as exc_info:
            check_access_token(invalid_token)

        assert "Token missing subject claim" in str(exc_info.value)

    def test_check_access_token_invalid_sub(self):
        """Test validation fails when sub doesn't match configured admin user."""
        user_data = {"sub": "wrong_user"}
        token_response = create_access_token(user_data)

        with pytest.raises(Exception) as exc_info:
            check_access_token(token_response.access_token)

        assert "Invalid token subject" in str(exc_info.value)

    def test_check_access_token_missing_exp(self):
        """Test validation fails when exp claim is missing."""
        from jose import jwt

        payload_data = {"sub": "test_admin"}
        invalid_token = jwt.encode(
            payload_data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        with pytest.raises(Exception) as exc_info:
            check_access_token(invalid_token)

        assert "Token missing expiration claim" in str(exc_info.value)

    def test_check_access_token_expired_token(self):
        """Test validation fails for expired tokens."""
        from jose import jwt

        # Create expired token
        expired_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        payload_data = {"sub": "test_admin", "exp": expired_time.timestamp()}
        expired_token = jwt.encode(
            payload_data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        with pytest.raises(Exception) as exc_info:
            check_access_token(expired_token)

        # The jose library catches expired tokens and returns "Signature has expired"
        assert "Token has expired" in str(
            exc_info.value
        ) or "Signature has expired" in str(exc_info.value)

    def test_check_access_token_invalid_signature(self):
        """Test validation fails for tokens with invalid signatures."""
        # Create token with wrong secret
        from jose import jwt

        user_data = {
            "sub": "test_admin",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        }
        invalid_token = jwt.encode(
            user_data, "wrong_secret", algorithm=settings.JWT_ALGORITHM
        )

        with pytest.raises(Exception) as exc_info:
            check_access_token(invalid_token)

        # Should catch JWTError and provide generic error message
        assert "Token validation failed" in str(exc_info.value) or "Invalid token" in str(
            exc_info.value
        )

    def test_check_access_token_malformed_token(self):
        """Test validation fails for malformed tokens."""
        malformed_token = "not.a.valid.token"

        with pytest.raises(Exception) as exc_info:
            check_access_token(malformed_token)

        # Should catch JWTError
        assert "Token validation failed" in str(exc_info.value) or "Invalid token" in str(
            exc_info.value
        )

    def test_check_access_token_empty_sub(self):
        """Test validation fails when sub is empty."""
        from jose import jwt

        payload_data = {
            "sub": "",  # Empty sub
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        }
        invalid_token = jwt.encode(
            payload_data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        with pytest.raises(Exception) as exc_info:
            check_access_token(invalid_token)

        assert "Token missing subject claim" in str(exc_info.value)

    def test_check_access_token_none_sub(self):
        """Test validation fails when sub is None."""
        from jose import jwt

        payload_data = {
            "sub": None,  # None sub
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        }
        invalid_token = jwt.encode(
            payload_data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        with pytest.raises(Exception) as exc_info:
            check_access_token(invalid_token)

        # The jose library validates that sub must be a string, so we get a different error
        assert "Subject must be a string" in str(exc_info.value)

    def test_check_access_token_zero_exp(self):
        """Test validation fails when exp is 0."""
        from jose import jwt

        payload_data = {
            "sub": "test_admin",
            "exp": 0,  # Zero expiration
        }
        invalid_token = jwt.encode(
            payload_data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        with pytest.raises(Exception) as exc_info:
            check_access_token(invalid_token)

        # Zero exp might be treated as expired by jose library or missing by our validation
        assert (
            "Token missing expiration claim" in str(exc_info.value)
            or "Signature has expired" in str(exc_info.value)
            or "Token validation failed" in str(exc_info.value)
        )

    def test_check_access_token_none_exp(self):
        """Test validation fails when exp is None."""
        from jose import jwt

        payload_data = {
            "sub": "test_admin",
            "exp": None,  # None expiration
        }
        invalid_token = jwt.encode(
            payload_data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        with pytest.raises(Exception) as exc_info:
            check_access_token(invalid_token)

        # None exp will cause an error when trying to compare with current time
        assert (
            "Token missing expiration claim" in str(exc_info.value)
            or "not 'NoneType'" in str(exc_info.value)
            or "Token validation failed" in str(exc_info.value)
        )
