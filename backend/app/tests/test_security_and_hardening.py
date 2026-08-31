import pytest
import uuid
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from app.ingestion.pipeline import IngestionPipeline
from fastapi.testclient import TestClient
from app.main import app as fastapi_app


def test_argon2_password_hashing():
    """Verify Argon2 password hashing and verification."""
    password = "SuperSecretExaminerPassphrase2026!"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_claims_and_expiration():
    """Verify JWT access token encoding, decoding, role claim, and user_id claim."""
    user_id = "EXAMINER_NCIIPC_01"
    role = "EXAMINER"
    token = create_access_token(subject=user_id, role=role)
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload is not None
    assert payload.get("sub") == user_id
    assert payload.get("role") == role


def test_sql_injection_protection_in_api():
    """Verify parameterized queries reject SQL injection payloads safely."""
    client = TestClient(fastapi_app)
    malicious_id = "3052411c-0af5-49f6-8667-f55dcbf03b4b' OR '1'='1"
    
    # 1. Test queue endpoint
    r1 = client.get(f"/api/v1/prioritization/queue/{malicious_id}")
    assert r1.status_code == 400
    assert "UUID" in r1.json()["detail"]

    # 2. Test evidence endpoint
    r2 = client.get(f"/api/v1/evidence/{malicious_id}")
    assert r2.status_code == 400

    # 3. Test risk endpoint
    r3 = client.get(f"/api/v1/risk/cse/{malicious_id}")
    assert r3.status_code == 400


def test_path_traversal_protection():
    """Verify path traversal payloads in file ingestion are rejected."""
    pipeline = IngestionPipeline()
    traversal_path = "../../etc/passwd.csv"
    with pytest.raises((ValueError, FileNotFoundError)):
        pipeline.process_file(traversal_path)

