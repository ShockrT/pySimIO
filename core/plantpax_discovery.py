from __future__ import annotations

from typing import Any, Iterable

from domain.models import DeviceRecord, PlantPaxModule
from domain.plantpax_definitions import definition_for


class PlantPaxDiscoveryService:
    """Discover recognized controller-scope PlantPAx tags and categorize them."""

    def __init__(self, plc: Any) -> None:
        self.plc = plc

    def discover_controller_scope(self) -> list[PlantPaxModule]:
        tags = self.plc.list_tags("")
        return self.classify_tags(tags)

    @staticmethod
    def classify_tags(tags: Iterable[Any]) -> list[PlantPaxModule]:
        modules: list[PlantPaxModule] = []
        for tag in tags:
            name = str(getattr(tag, "tag_name", None) or getattr(tag, "name", None) or "").strip()
            data_type = str(
                getattr(tag, "data_type_name", None)
                or getattr(tag, "data_type", None)
                or getattr(tag, "type", None)
                or ""
            ).strip()
            definition = definition_for(data_type)
            if not name or definition is None:
                continue
            modules.append(
                PlantPaxModule(
                    name=name,
                    data_type=definition.data_type,
                    path=name,
                    module_type=definition.category.value,
                )
            )
        return modules

    @staticmethod
    def to_device_records(modules: Iterable[PlantPaxModule]) -> list[DeviceRecord]:
        records: list[DeviceRecord] = []
        for module in modules:
            definition = definition_for(module.data_type)
            if definition is None:
                continue
            records.append(
                DeviceRecord(
                    name=module.name,
                    data_type=definition.data_type,
                    category=definition.category.value,
                    controller_path=module.path or module.name,
                    source="plc_discovery",
                )
            )
        return records
