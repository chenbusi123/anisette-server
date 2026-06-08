"""
Device provisioning and state management.
Handles per-request and shared device data generation with persistent storage.
"""

import hashlib
import json
import logging
import secrets
import uuid
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Optional

from config import Config
from models import ADIData, DeviceInfo, DeviceState, ProvisioningRequest, ProvisioningResponse

logger = logging.getLogger(__name__)


class ProvisioningManager:
    """
    Manages device provisioning, state persistence, and ADI data generation.
    
    Provides both v1 (shared state) and v3 (per-client unique) provisioning modes.
    Uses thread-safe JSON storage for persistent device state.
    """

    SHARED_STATE_FILE = "shared_device.json"
    V1_IDENTIFIER_PREFIX = "v1_"

    def __init__(self, config: Config) -> None:
        """
        Initialize provisioning manager.
        
        Args:
            config: Server configuration instance.
        """
        self.config = config
        self.state_lock = Lock()
        self.shared_state: Optional[DeviceState] = None
        self._initialize_logging()

    def _initialize_logging(self) -> None:
        """Configure logging for provisioning manager."""
        logger.setLevel(self.config.log_level)

    def initialize(self) -> None:
        """Initialize provisioning manager and load/create shared device state."""
        try:
            self.shared_state = self._load_or_create_shared_state()
            logger.info("Provisioning manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize provisioning manager: {e}")
            raise

    def cleanup(self) -> None:
        """Clean up resources on shutdown."""
        if self.shared_state:
            self._save_device_state(self.shared_state)
            logger.info("Device state saved on shutdown")

    def get_timestamp(self) -> datetime:
        """
        Get current timestamp in UTC.
        
        Returns:
            datetime: Current UTC timestamp.
        """
        return datetime.utcnow()

    def _load_or_create_shared_state(self) -> DeviceState:
        """
        Load existing shared device state or create new one.
        
        Returns:
            DeviceState: Loaded or newly created shared device state.
        """
        state_file = self.config.storage_path / self.SHARED_STATE_FILE

        if state_file.exists():
            logger.info(f"Loading shared device state from {state_file}")
            return self._load_device_state(state_file)

        logger.info("Creating new shared device state")
        return self._generate_device_state("00008110-SHARED0000001")

    def _load_device_state(self, state_file: Path) -> DeviceState:
        """
        Load device state from JSON file.
        
        Args:
            state_file: Path to JSON state file.
            
        Returns:
            DeviceState: Loaded device state.
            
        Raises:
            ValueError: If state file is invalid.
        """
        try:
            with open(state_file, "r") as f:
                data = json.load(f)

            # Parse datetime fields
            if "provisioning_timestamp" in data:
                data["provisioning_timestamp"] = datetime.fromisoformat(
                    data["provisioning_timestamp"]
                )
            if "last_accessed" in data:
                data["last_accessed"] = datetime.fromisoformat(
                    data["last_accessed"]
                )

            return DeviceState(**data)

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to load device state: {e}")
            raise ValueError(f"Invalid device state file: {e}") from e

    def _save_device_state(self, state: DeviceState) -> None:
        """
        Save device state to JSON file.
        
        Args:
            state: Device state to save.
        """
        state_file = self.config.storage_path / self.SHARED_STATE_FILE

        with self.state_lock:
            try:
                with open(state_file, "w") as f:
                    json.dump(
                        state.model_dump(),
                        f,
                        indent=2,
                        default=str,
                    )
                logger.debug(f"Device state saved to {state_file}")
            except IOError as e:
                logger.error(f"Failed to save device state: {e}")
                raise

    def _generate_device_state(
        self,
        device_id: str,
        device_class: str = "iPhone",
        device_model: str = "iPhone15,2",
        os_version: str = "17.0",
        build_version: str = "21A329",
    ) -> DeviceState:
        """
        Generate new device state.
        
        Args:
            device_id: Device UDID.
            device_class: Device class (iPhone, iPad, etc.).
            device_model: Device model identifier.
            os_version: Operating system version.
            build_version: OS build version.
            
        Returns:
            DeviceState: Newly generated device state.
        """
        device_info = DeviceInfo(
            device_id=device_id,
            device_class=device_class,
            device_model=device_model,
            os_version=os_version,
            build_version=build_version,
        )

        machine_id = self._generate_machine_id(device_id)
        adi_data = ADIData(
            machine_id=machine_id,
            serial_number=machine_id,
            device_name=f"{device_class}",
            locale="zh_CN",
            timezone="Asia/Shanghai",
            encrypted_data=self._generate_encrypted_adi(machine_id),
        )

        now = datetime.utcnow()
        return DeviceState(
            device_info=device_info,
            adi_data=adi_data,
            provisioning_timestamp=now,
            last_accessed=now,
            v1_identifier=f"{self.V1_IDENTIFIER_PREFIX}{secrets.token_hex(8)}",
            v3_counter=0,
        )

    def _generate_machine_id(self, device_id: str) -> str:
        """
        Generate deterministic machine ID from device ID.
        
        Args:
            device_id: Device UDID.
            
        Returns:
            str: Generated machine ID (24 hex characters).
        """
        # Create deterministic but unique ID from device ID
        hash_obj = hashlib.sha256(device_id.encode())
        return hash_obj.hexdigest()[:24].upper()

    def _generate_encrypted_adi(self, machine_id: str) -> str:
        """
        Generate mock encrypted ADI payload.
        
        In a production system, this would contain actual encrypted data.
        
        Args:
            machine_id: Machine ID to include in payload.
            
        Returns:
            str: Base64-encoded mock encrypted payload.
        """
        import base64

        # Mock encrypted payload structure
        payload = {
            "machine_id": machine_id,
            "timestamp": datetime.utcnow().isoformat(),
            "nonce": secrets.token_hex(16),
        }

        payload_json = json.dumps(payload).encode()
        return base64.b64encode(payload_json).decode()

    def get_v1_data(
        self,
        request: ProvisioningRequest,
    ) -> ProvisioningResponse:
        """
        Get provisioning data for v1 endpoint (shared state).
        
        All v1 requests share the same device state and ADI data.
        State is persistent across requests.
        
        Args:
            request: Provisioning request.
            
        Returns:
            ProvisioningResponse: Provisioning response with shared device data.
        """
        with self.state_lock:
            if not self.shared_state:
                self.shared_state = self._load_or_create_shared_state()

            # Update last accessed timestamp
            self.shared_state.last_accessed = datetime.utcnow()
            self._save_device_state(self.shared_state)

            response = ProvisioningResponse(
                success=True,
                device_state=self.shared_state,
                adi_data=self.shared_state.adi_data,
                timestamp=datetime.utcnow(),
                request_id=str(uuid.uuid4()),
            )

        logger.info(
            f"V1 provisioning completed - "
            f"client_id={request.client_id}, "
            f"device_id={request.device_info.device_id}"
        )
        return response

    def get_v3_data(
        self,
        request: ProvisioningRequest,
        client_info: str,
    ) -> ProvisioningResponse:
        """
        Get provisioning data for v3 endpoint (per-client unique state).
        
        Each request generates unique device data specific to that client.
        More secure than v1 as each client gets unique ADI data.
        
        Args:
            request: Provisioning request.
            client_info: Client connection information (IP:port).
            
        Returns:
            ProvisioningResponse: Provisioning response with unique client-specific data.
        """
        # Generate unique device ID for this v3 request
        unique_suffix = hashlib.sha256(
            f"{client_info}{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:12]
        unique_device_id = f"00008110-{unique_suffix.upper()}"

        device_state = self._generate_device_state(
            device_id=unique_device_id,
            device_class=request.device_info.device_class,
            device_model=request.device_info.device_model,
            os_version=request.device_info.os_version,
            build_version=request.device_info.build_version,
        )

        response = ProvisioningResponse(
            success=True,
            device_state=device_state,
            adi_data=device_state.adi_data,
            timestamp=datetime.utcnow(),
            request_id=str(uuid.uuid4()),
        )

        logger.info(
            f"V3 provisioning completed - "
            f"client_info={client_info}, "
            f"client_id={request.client_id}, "
            f"device_id={unique_device_id}"
        )
        return response
