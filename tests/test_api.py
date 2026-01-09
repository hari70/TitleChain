"""
TitleChain Tests

Run with: pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthCheck:
    """Test API health endpoints."""
    
    def test_health(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_root(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert data["name"] == "TitleChain API"


class TestIdentity:
    """Test identity (DID) endpoints."""
    
    def test_create_identity(self, client):
        """Test creating a new identity."""
        response = client.post(
            "/identity/create",
            json={"user_id": "test_user_1", "name": "Test User"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "did" in data
        assert "did:web:" in data["did"]
        assert "test_user_1" in data["did"]
    
    def test_create_duplicate_identity(self, client):
        """Test that duplicate user IDs are rejected."""
        # Create first
        client.post("/identity/create", json={"user_id": "duplicate_test"})
        # Try to create duplicate
        response = client.post("/identity/create", json={"user_id": "duplicate_test"})
        assert response.status_code == 400
    
    def test_get_identity(self, client):
        """Test retrieving an identity."""
        # Create first
        client.post("/identity/create", json={"user_id": "get_test"})
        # Get it
        response = client.get("/identity/get_test")
        assert response.status_code == 200
        data = response.json()
        assert "did" in data
        assert "did_document" in data
    
    def test_get_nonexistent_identity(self, client):
        """Test that nonexistent identity returns 404."""
        response = client.get("/identity/nonexistent_user_xyz")
        assert response.status_code == 404


class TestTitleAnalysis:
    """Test title analysis endpoints."""
    
    def test_upload_document(self, client):
        """Test uploading a document for analysis."""
        # Create a simple test file
        test_content = b"""
        WARRANTY DEED
        Grantor: John Doe
        Grantee: Jane Smith
        Property: 123 Test Street
        """
        
        response = client.post(
            "/title/upload",
            files={"file": ("test_deed.txt", test_content, "text/plain")}
        )
        assert response.status_code == 200
        data = response.json()
        assert "analysis_id" in data
        assert data["status"] == "complete"
    
    def test_upload_invalid_file_type(self, client):
        """Test that invalid file types are rejected."""
        response = client.post(
            "/title/upload",
            files={"file": ("test.exe", b"binary content", "application/octet-stream")}
        )
        assert response.status_code == 400


class TestCredentials:
    """Test credential endpoints."""
    
    def test_full_flow(self, client):
        """Test the complete flow: identity → upload → credential."""
        # 1. Create identity
        identity_response = client.post(
            "/identity/create",
            json={"user_id": "flow_test_user"}
        )
        assert identity_response.status_code == 200
        
        # 2. Upload document
        test_content = b"""
        WARRANTY DEED
        Grantor: Test Grantor
        Grantee: Test Grantee
        Property: 456 Test Ave
        Recorded: Book 100, Page 50
        """
        upload_response = client.post(
            "/title/upload?user_id=flow_test_user",
            files={"file": ("deed.txt", test_content, "text/plain")}
        )
        assert upload_response.status_code == 200
        analysis_id = upload_response.json()["analysis_id"]
        
        # 3. Issue credential
        cred_response = client.post(
            f"/credential/issue?user_id=flow_test_user&analysis_id={analysis_id}"
        )
        assert cred_response.status_code == 200
        cred_data = cred_response.json()
        assert "credential" in cred_data
        assert "proof" in cred_data["credential"]
        
        # 4. Verify credential
        cred_id = cred_data["credential"]["id"].split(":")[-1]
        verify_response = client.get(f"/credential/verify/{cred_id}")
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["verification_result"]["valid"] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
