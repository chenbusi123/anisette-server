"""
Test suite for Anisette provisioning server.
Tests API endpoints and core provisioning functionality.
"""

import json
from datetime import datetime
from unittest import TestCase

from fastapi.testclient import TestClient

from app import app
from models import DeviceInfo, ProvisioningRequest

client = TestClient(app)


class TestHealthEndpoint(TestCase):
    """Tests for health check endpoint."""

    def test_health_check_returns_healthy(self) -> None:
        """Verify health endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    def test_health_check_has_valid_timestamp(self) -> None:
        """Verify health timestamp is valid ISO format."""
        response = client.get("/health")
        data = response.json()
        timestamp = data["timestamp"]

        # Should be parseable as ISO datetime
        datetime.fromisoformat(timestamp)


class TestRootEndpoint(TestCase):
    """Tests for root endpoint."""

    def test_root_returns_api_info(self) -> None:
        """Verify root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Anisette Provisioning Server"
        assert "endpoints" in data
        assert "/health" in data["endpoints"]
        assert "/1 (POST)" in data["endpoints"]
        assert "/3 (POST)" in data["endpoints"]


class TestV1ProvisioningEndpoint(TestCase):
    """Tests for V1 provisioning endpoint."""

    def _create_request_payload(self) -> dict:
        """Create valid provisioning request payload."""
        return {
            "client_id": "com.example.test",
            "device_info": {
                "device_id": "00008110-001234567890AB",
                "device_class": "iPhone",
                "device_model": "iPhone15,2",
                "os_version": "17.0",
                "build_version": "21A329",
            },
        }

    def test_v1_provisioning_success(self) -> None:
        """Verify V1 provisioning returns valid response."""
        payload = self._create_request_payload()
        response = client.post("/1", json=payload)

        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "request_id" in data
        assert "timestamp" in data
        assert "device_state" in data
        assert "adi_data" in data

    def test_v1_shared_state_persistence(self) -> None:
        """Verify V1 returns consistent device state."""
        payload = self._create_request_payload()

        # First request
        response1 = client.post("/1", json=payload)
        device_state1 = response1.json()["device_state"]

        # Second request
        response2 = client.post("/1", json=payload)
        device_state2 = response2.json()["device_state"]

        # Device state should be same (shared)
        assert device_state1["adi_data"]["machine_id"] == device_state2["adi_data"]["machine_id"]

    def test_v1_invalid_request_returns_400(self) -> None:
        """Verify V1 returns 400 for invalid request."""
        invalid_payload = {"client_id": "test"}  # Missing device_info

        response = client.post("/1", json=invalid_payload)
        assert response.status_code == 400

    def test_v1_response_has_valid_adi_data(self) -> None:
        """Verify V1 response contains valid ADI data."""
        payload = self._create_request_payload()
        response = client.post("/1", json=payload)

        adi_data = response.json()["adi_data"]
        assert "machine_id" in adi_data
        assert "serial_number" in adi_data
        assert "device_name" in adi_data
        assert "encrypted_data" in adi_data
        assert adi_data["locale"] == "en_US"
        assert adi_data["timezone"] == "UTC"


class TestV3ProvisioningEndpoint(TestCase):
    """Tests for V3 provisioning endpoint."""

    def _create_request_payload(self) -> dict:
        """Create valid provisioning request payload."""
        return {
            "client_id": "com.example.test",
            "device_info": {
                "device_id": "00008110-001234567890AB",
                "device_class": "iPhone",
                "device_model": "iPhone15,2",
                "os_version": "17.0",
                "build_version": "21A329",
            },
        }

    def test_v3_provisioning_success(self) -> None:
        """Verify V3 provisioning returns valid response."""
        payload = self._create_request_payload()
        response = client.post("/3", json=payload)

        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "request_id" in data
        assert "timestamp" in data
        assert "device_state" in data
        assert "adi_data" in data

    def test_v3_generates_unique_state(self) -> None:
        """Verify V3 generates unique device state per request."""
        payload = self._create_request_payload()

        # First request
        response1 = client.post("/3", json=payload)
        device_state1 = response1.json()["device_state"]

        # Second request
        response2 = client.post("/3", json=payload)
        device_state2 = response2.json()["device_state"]

        # Device state should be different (unique per client)
        assert device_state1["adi_data"]["machine_id"] != device_state2["adi_data"]["machine_id"]

    def test_v3_invalid_request_returns_400(self) -> None:
        """Verify V3 returns 400 for invalid request."""
        invalid_payload = {"client_id": "test"}  # Missing device_info

        response = client.post("/3", json=invalid_payload)
        assert response.status_code == 400

    def test_v3_response_has_valid_adi_data(self) -> None:
        """Verify V3 response contains valid ADI data."""
        payload = self._create_request_payload()
        response = client.post("/3", json=payload)

        adi_data = response.json()["adi_data"]
        assert "machine_id" in adi_data
        assert "serial_number" in adi_data
        assert "device_name" in adi_data
        assert "encrypted_data" in adi_data
        assert adi_data["locale"] == "en_US"
        assert adi_data["timezone"] == "UTC"

    def test_v3_includes_unique_device_id(self) -> None:
        """Verify V3 generates unique device IDs."""
        payload = self._create_request_payload()

        # First request
        response1 = client.post("/3", json=payload)
        device_state1 = response1.json()["device_state"]

        # Second request
        response2 = client.post("/3", json=payload)
        device_state2 = response2.json()["device_state"]

        # Device IDs should be different
        id1 = device_state1["device_info"]["device_id"]
        id2 = device_state2["device_info"]["device_id"]
        assert id1 != id2


class TestDataModels(TestCase):
    """Tests for Pydantic data models."""

    def test_device_info_model(self) -> None:
        """Test DeviceInfo model validation."""
        data = {
            "device_id": "00008110-001234567890AB",
            "device_class": "iPhone",
            "device_model": "iPhone15,2",
            "os_version": "17.0",
            "build_version": "21A329",
        }

        device_info = DeviceInfo(**data)
        assert device_info.device_id == data["device_id"]

    def test_provisioning_request_model(self) -> None:
        """Test ProvisioningRequest model validation."""
        data = {
            "client_id": "com.example.test",
            "device_info": {
                "device_id": "00008110-001234567890AB",
                "device_class": "iPhone",
                "device_model": "iPhone15,2",
                "os_version": "17.0",
                "build_version": "21A329",
            },
        }

        request = ProvisioningRequest(**data)
        assert request.client_id == data["client_id"]


if __name__ == "__main__":
    import unittest

    unittest.main()
