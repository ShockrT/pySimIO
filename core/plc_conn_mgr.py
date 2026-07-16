from __future__ import annotations

import logging
from typing import Any

from pycomm3 import LogixDriver, Tag

logger = logging.getLogger("PLCConnectionManager")


class PLCConnectionManager:
    """Owns a Logix connection without forcing I/O during object construction."""

    def __init__(self, ip_address: str, slot: int = 0, name: str = ""):
        self.ip_address = ip_address.strip()
        self.slot = int(slot)
        self.name = name.strip() or self.ip_address
        self.path = f"{self.ip_address}/{self.slot}"
        self.driver: LogixDriver | None = None

    def connect(self) -> bool:
        if self.is_connected():
            return True
        self.close()
        try:
            self.driver = LogixDriver(self.path)
            self.driver.open()
            connected = self.is_connected()
            if connected:
                logger.info("Connected to PLC at %s", self.path)
            return connected
        except Exception:
            logger.exception("Failed to connect to PLC at %s", self.path)
            self.driver = None
            return False

    def is_connected(self) -> bool:
        return self.driver is not None and bool(getattr(self.driver, "connected", False))

    def read_tag(self, tag: str) -> Any | None:
        if not self.is_connected():
            return None
        try:
            result = self.driver.read(tag)
            return result.value if result and result.error is None else None
        except Exception:
            logger.exception("Exception reading %s", tag)
            return None

    def read_tags(self, tag_list: list[str]) -> dict[str, Any]:
        if not self.is_connected() or not tag_list:
            return {}
        try:
            results = self.driver.read(*tag_list)
            if not isinstance(results, list):
                results = [results]
            return {result.tag: result.value for result in results if result and result.error is None}
        except Exception:
            logger.exception("Exception during batch read")
            return {}

    def write_tag(self, tag: str, value: Any) -> bool:
        if not self.is_connected():
            return False
        try:
            result = self.driver.write((tag, value))
            return bool(result and result.error is None)
        except Exception:
            logger.exception("Exception writing %s", tag)
            return False

    def get_metadata(self, base_tag: str) -> dict[str, Any]:
        suffixes = ("EU", "EUMin", "EUMax")
        values = self.read_tags([f"{base_tag}.{suffix}" for suffix in suffixes])
        return {suffix: values.get(f"{base_tag}.{suffix}") for suffix in suffixes}

    def list_tags(self, base_path: str = "") -> list[Tag]:
        if not self.is_connected():
            return []
        try:
            return list(self.driver.browse(base_path))
        except Exception:
            logger.exception("Exception browsing tags under %s", base_path)
            return []

    def close(self) -> None:
        if self.driver is not None:
            try:
                self.driver.close()
            except Exception:
                logger.exception("Error closing PLC connection")
            finally:
                self.driver = None
