"""
Configuration management for Anisette provisioning server.
Implements XDG Base Directory Specification for data storage.
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Config:
    """
    Server configuration management with XDG standards support.
    
    Configuration priority:
    1. Environment variables
    2. Default values
    
    Storage follows XDG Base Directory Specification:
    - Data: ~/.local/share/anisette/ (or XDG_DATA_HOME)
    - Config: ~/.config/anisette/ (or XDG_CONFIG_HOME)
    """

    def __init__(
        self,
        hostname: str = "0.0.0.0",
        port: int = 8000,
        storage_path: Optional[str] = None,
        config_path: Optional[str] = None,
        tls_enabled: bool = False,
        tls_cert_path: Optional[str] = None,
        tls_key_path: Optional[str] = None,
        log_level: str = "INFO",
    ) -> None:
        """
        Initialize configuration.
        
        Args:
            hostname: Server hostname/IP to bind to.
            port: Server port to bind to.
            storage_path: Directory for persistent data storage.
            config_path: Directory for configuration files.
            tls_enabled: Enable HTTPS/TLS.
            tls_cert_path: Path to TLS certificate file.
            tls_key_path: Path to TLS private key file.
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        """
        self.hostname = hostname
        self.port = port
        self.tls_enabled = tls_enabled
        self.tls_cert_path = tls_cert_path
        self.tls_key_path = tls_key_path
        self.log_level = log_level

        # Setup storage path with XDG Base Directory support
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            xdg_data_home = os.getenv(
                "XDG_DATA_HOME",
                Path.home() / ".local" / "share",
            )
            self.storage_path = Path(xdg_data_home) / "anisette"

        # Setup config path with XDG Base Directory support
        if config_path:
            self.config_path = Path(config_path)
        else:
            xdg_config_home = os.getenv(
                "XDG_CONFIG_HOME",
                Path.home() / ".config",
            )
            self.config_path = Path(xdg_config_home) / "anisette"

        # Create directories if they don't exist
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.config_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Storage path: {self.storage_path}")
        logger.info(f"Config path: {self.config_path}")

    @classmethod
    def from_env(cls) -> "Config":
        """
        Create configuration from environment variables.
        
        Environment variables:
            ANISETTE_HOSTNAME: Server hostname (default: 0.0.0.0)
            ANISETTE_PORT: Server port (default: 8000)
            ANISETTE_STORAGE_PATH: Data storage directory
            ANISETTE_CONFIG_PATH: Configuration directory
            ANISETTE_TLS_ENABLED: Enable TLS (default: false)
            ANISETTE_TLS_CERT_PATH: TLS certificate path
            ANISETTE_TLS_KEY_PATH: TLS private key path
            ANISETTE_LOG_LEVEL: Logging level (default: INFO)
        
        Returns:
            Config: Configured Config instance.
        """
        return cls(
            hostname=os.getenv("ANISETTE_HOSTNAME", "0.0.0.0"),
            port=int(os.getenv("ANISETTE_PORT", "8000")),
            storage_path=os.getenv("ANISETTE_STORAGE_PATH"),
            config_path=os.getenv("ANISETTE_CONFIG_PATH"),
            tls_enabled=os.getenv("ANISETTE_TLS_ENABLED", "false").lower() == "true",
            tls_cert_path=os.getenv("ANISETTE_TLS_CERT_PATH"),
            tls_key_path=os.getenv("ANISETTE_TLS_KEY_PATH"),
            log_level=os.getenv("ANISETTE_LOG_LEVEL", "INFO"),
        )

    def __repr__(self) -> str:
        """String representation of configuration."""
        return (
            f"Config(hostname={self.hostname}, port={self.port}, "
            f"storage_path={self.storage_path}, config_path={self.config_path}, "
            f"tls_enabled={self.tls_enabled})"
        )
