"""
Pydantic data models for request/response schemas.
Defines device information, ADI data, and provisioning responses.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DeviceInfo(BaseModel):
    """
    Device information used for provisioning.
    
    Attributes:
        device_id: Unique device identifier (UDID).
        device_class: Device class (iPhone, iPad, etc.).
        device_model: Device model identifier.
        os_version: Operating system version.
        build_version: OS build version.
    """

    device_id: str = Field(..., description="Unique device identifier (UDID)")
    device_class: str = Field(..., description="Device class (iPhone, iPad, etc.)")
    device_model: str = Field(..., description="Device model identifier")
    os_version: str = Field(..., description="Operating system version")
    build_version: str = Field(..., description="OS build version")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "device_id": "00008110-001234567890AB",
                "device_class": "iPhone",
                "device_model": "iPhone15,2",
                "os_version": "17.0",
                "build_version": "21A329",
            }
        }


class ADIData(BaseModel):
    """
    Apple Device Information (ADI) data for authentication.
    
    Contains encrypted device identifier and machine name for Apple services.
    
    Attributes:
        machine_id: Unique machine identifier.
        serial_number: Device serial number.
        device_name: Human-readable device name.
        locale: Device locale/language setting.
        timezone: Device timezone.
        encrypted_data: Encrypted ADI payload.
    """

    machine_id: str = Field(..., description="Unique machine identifier")
    serial_number: str = Field(..., description="Device serial number")
    device_name: str = Field(..., description="Human-readable device name")
    locale: str = Field(default="zh_CN", description="Device locale")
    timezone: str = Field(default="Asia/Shanghai", description="Device timezone")
    encrypted_data: str = Field(..., description="Encrypted ADI payload")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "machine_id": "ABC123DEF456",
                "serial_number": "ABC123DEF456",
                "device_name": "iPhone",
                "locale": "zh_CN",
                "timezone": "Asia/Shanghai",
                "encrypted_data": "base64_encoded_encrypted_payload",
            }
        }


class DeviceState(BaseModel):
    """
    Persistent device state stored in JSON.
    
    Attributes:
        device_info: Device information.
        adi_data: Apple Device Information.
        provisioning_timestamp: When device was provisioned.
        last_accessed: Last access timestamp.
        v1_identifier: Shared identifier for v1 endpoint.
        v3_counter: Counter for unique v3 requests.
    """

    device_info: DeviceInfo
    adi_data: ADIData
    provisioning_timestamp: datetime
    last_accessed: datetime
    v1_identifier: str = Field(..., description="Shared identifier for v1 endpoint")
    v3_counter: int = Field(default=0, description="Counter for unique v3 requests")

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class ProvisioningRequest(BaseModel):
    """
    Request model for provisioning endpoints.
    
    Attributes:
        client_id: Optional client identifier.
        device_info: Device information for provisioning.
    """

    client_id: Optional[str] = Field(
        default=None,
        description="Optional client identifier",
    )
    device_info: DeviceInfo

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "client_id": "com.example.app",
                "device_info": {
                    "device_id": "00008110-001234567890AB",
                    "device_class": "iPhone",
                    "device_model": "iPhone15,2",
                    "os_version": "17.0",
                    "build_version": "21A329",
                },
            }
        }


class ProvisioningResponse(BaseModel):
    """
    Response model for provisioning endpoints.
    
    Attributes:
        success: Whether provisioning was successful.
        device_state: Device state information.
        adi_data: Apple Device Information for authentication.
        timestamp: Response timestamp.
        request_id: Unique request identifier.
    """

    success: bool = Field(default=True, description="Provisioning success status")
    device_state: DeviceState
    adi_data: ADIData
    timestamp: datetime
    request_id: str = Field(..., description="Unique request identifier")

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class HealthResponse(BaseModel):
    """
    Response model for health check endpoint.
    
    Attributes:
        status: Server health status.
        version: Server version.
        timestamp: Check timestamp.
    """

    status: str = Field(default="healthy", description="Health status")
    version: str = Field(..., description="Server version")
    timestamp: datetime = Field(..., description="Check timestamp")

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
