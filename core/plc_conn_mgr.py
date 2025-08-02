from pycomm3 import LogixDriver, CommError
from typing import Optional, Any
import logging
from constants import PV_MODULE_TYPES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PLCConnectionManager:
    def __init__(self, ip_address: str, slot: int = 0):
        """
        :param ip_address: IP address of the PLC (e.g., '192.168.1.10')
        :param slot: Slot number of the processor (usually 0)
        """
        self.ip_address = ip_address
        self.slot = slot
        self.driver: Optional[LogixDriver] = None
        self.connected = False

    def connect(self) -> bool:
        try:
            self.driver = LogixDriver(f"{self.ip_address}/{self.slot}")
            self.driver.open()
            self.connected = True
            logger.info(f"Connected to PLC at {self.ip_address}/{self.slot}")
            return True
        except CommError as e:
            logger.error(f"Connection failed: {e}")
            self.connected = False
            return False

    def disconnect(self):
        if self.driver:
            self.driver.close()
            self.connected = False
            logger.info("Disconnected from PLC.")

    def read_tag(self, tag_name: str) -> Optional[Any]:
        if not self.connected or not self.driver:
            raise RuntimeError("Not connected to PLC.")
        try:
            result = self.driver.read(tag_name)
            return result.value
        except CommError as e:
            logger.error(f"Failed to read tag '{tag_name}': {e}")
            return None

    def write_tag(self, tag_name: str, value: Any) -> bool:
        if not self.connected or not self.driver:
            raise RuntimeError("Not connected to PLC.")
        try:
            self.driver.write(tag_name, value)
            return True
        except CommError as e:
            logger.error(f"Failed to write tag '{tag_name}': {e}")
            return False

    def list_tags(self, program_scope: Optional[str] = None) -> list[str]:
        if not self.connected or not self.driver:
            raise RuntimeError("Not connected to PLC.")
        try:
            tags_dict = self.driver.tags  # <- This is a dict of {name: LogixTag}
            if program_scope:
                return [name for name, tag in tags_dict.items() if tag.program == program_scope]
            return list(tags_dict.keys())
        except CommError as e:
            logger.error(f"Failed to list tags: {e}")
            return []

    def is_connected(self) -> bool:
        return self.connected and self.driver is not None and self.driver.connected

    def get_tag_metadata(self, tag_name: str) -> Optional[dict]:
        if not self.connected or not self.driver:
            raise RuntimeError("Not connected to PLC.")
        try:
            tags = [tag for tag in self.driver.tags.get(tag_name) if tag.name == tag_name]
            if not tags:
                logger.error(f"Tag '{tag_name}' not found.")
                return None

            tag = tags[0]
            return {
                "name": tag.name,
                "data_type": tag.data_type,
                "dimensions": tag.dimensions,
                "is_atomic": tag.is_atomic,
                "structure": tag.structure if not tag.is_atomic else None,
                "program": tag.program
            }
        except CommError as e:
            logger.error(f"Failed to get metadata for '{tag_name}': {e}")
            return None

    def get_analog_input_tags(self) -> list[dict]:
        """
        Returns a list of tags with data_type == 'P_ANALOG_INPUT'
        """
        if not self.connected or not self.driver:
            raise RuntimeError("Not connected to PLC.")

        try:
            return [
                {
                    "name": tag.name,
                    "data_type": tag.data_type,
                    "dimensions": tag.dimensions,
                    "structure": tag.structure,
                    "program": tag.program
                }
                for tag in self.driver.tags.values()
                if tag.data_type in PV_MODULE_TYPES
            ]
        except CommError as e:
            logger.error(f"Failed to filter analog input tags: {e}")
            return []

