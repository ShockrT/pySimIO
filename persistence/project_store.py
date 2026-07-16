from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping

from domain.models import ConfiguredModel, DeviceRecord, FlowPath, PlantPaxModule
from core.plantpax_discovery import PlantPaxDiscoveryService


SCHEMA_VERSION = 3
PROJECT_EXTENSION = ".pysimio"


class ProjectStore:
    """In-memory project document with explicit, atomic file saves."""

    def __init__(self, path: str | Path | None = None):
        self.path: Path | None = self._normalize_path(path) if path else None
        self._document: dict[str, Any] = self.empty_document()
        self._dirty = False

    @staticmethod
    def empty_document() -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "models": [],
            "flow_paths": [],
            "devices": [],
            "discovered_modules": [],
            "plc_profiles": [],
            "metadata": {},
        }

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    @property
    def has_path(self) -> bool:
        return self.path is not None

    @property
    def display_name(self) -> str:
        return self.path.stem if self.path else "Untitled"

    def new(self) -> dict[str, Any]:
        self.path = None
        self._document = self.empty_document()
        self._dirty = False
        return self.document()

    def load(self, path: str | Path | None = None, *, force: bool = False) -> dict[str, Any]:
        if path is not None:
            self.path = self._normalize_path(path)
            force = True
        if not force:
            return self.document()
        if self.path is None:
            self._document = self.empty_document()
            self._dirty = False
            return self.document()
        if not self.path.exists():
            raise FileNotFoundError(f"Project file does not exist: {self.path}")
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Unable to read project file {self.path}: {exc}") from exc
        self._document = self._normalize(raw)
        self._dirty = False
        return self.document()

    def open(self, path: str | Path) -> dict[str, Any]:
        return self.load(path, force=True)

    def save(self, document: Mapping[str, Any] | None = None, *, path: str | Path | None = None) -> Path:
        if document is not None:
            self._document = self._normalize(document)
            self._dirty = True
        if path is not None:
            self.path = self._normalize_path(path)
        if self.path is None:
            raise ValueError("A project path is required. Use Save As first.")

        normalized = self._normalize(self._document)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(normalized, handle, indent=2, sort_keys=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise
        self._document = normalized
        self._dirty = False
        return self.path

    def save_as(self, path: str | Path) -> Path:
        return self.save(path=path)

    def document(self) -> dict[str, Any]:
        return deepcopy(self._document)

    def get_models(self) -> list[ConfiguredModel]:
        return [ConfiguredModel.from_dict(item) for item in self._document["models"]]

    def set_models(self, models: Iterable[ConfiguredModel]) -> None:
        self._document["models"] = [item.to_dict() for item in models]
        self._dirty = True

    def upsert_model(self, model: ConfiguredModel) -> None:
        items = self.get_models()
        key = model.name.casefold()
        for index, current in enumerate(items):
            if current.name.casefold() == key:
                items[index] = model
                break
        else:
            items.append(model)
        self.set_models(items)

    def remove_model(self, name: str) -> bool:
        items = self.get_models()
        kept = [item for item in items if item.name.casefold() != name.casefold()]
        if len(kept) == len(items):
            return False
        self.set_models(kept)
        return True

    def get_devices(self) -> list[DeviceRecord]:
        return [DeviceRecord.from_dict(item) for item in self._document["devices"]]

    def set_devices(self, devices: Iterable[DeviceRecord]) -> None:
        self._document["devices"] = [item.to_dict() for item in devices]
        self._dirty = True

    def upsert_device(self, device: DeviceRecord) -> None:
        items = self.get_devices()
        identity = device.controller_path.casefold() or device.name.casefold()
        for index, current in enumerate(items):
            current_identity = current.controller_path.casefold() or current.name.casefold()
            if current_identity == identity:
                # Preserve user ownership while refreshing discovery metadata.
                source = current.source if current.source == "manual" else device.source
                items[index] = DeviceRecord(
                    name=device.name,
                    data_type=device.data_type,
                    category=device.category,
                    controller_path=device.controller_path,
                    source=source,
                )
                break
        else:
            items.append(device)
        self.set_devices(items)

    def get_flow_paths(self) -> list[FlowPath]:
        return [FlowPath.from_dict(item) for item in self._document["flow_paths"]]

    def set_flow_paths(self, flow_paths: Iterable[FlowPath]) -> None:
        self._document["flow_paths"] = [item.to_dict() for item in flow_paths]
        self._dirty = True

    def upsert_flow_path(self, flow_path: FlowPath, *, previous_name: str | None = None) -> None:
        items = self.get_flow_paths()
        keys = {flow_path.name.casefold()}
        if previous_name:
            keys.add(previous_name.casefold())
        items = [item for item in items if item.name.casefold() not in keys]
        items.append(flow_path)
        self.set_flow_paths(items)

    def remove_flow_path(self, name: str) -> bool:
        items = self.get_flow_paths()
        kept = [item for item in items if item.name.casefold() != name.casefold()]
        if len(kept) == len(items):
            return False
        self.set_flow_paths(kept)
        return True

    def get_discovered_modules(self) -> list[PlantPaxModule]:
        return [PlantPaxModule.from_dict(item) for item in self._document["discovered_modules"]]

    def set_discovered_modules(self, modules: Iterable[PlantPaxModule]) -> None:
        self._document["discovered_modules"] = [item.to_dict() for item in modules]
        self._dirty = True

    def sync_discovered_modules(self, modules: Iterable[PlantPaxModule]) -> dict[str, list[str]]:
        incoming = list(modules)
        existing = self.get_models()
        by_identity: dict[str, ConfiguredModel] = {}
        for item in existing:
            if item.name:
                by_identity[item.name.casefold()] = item
            if item.tag:
                by_identity[item.tag.casefold()] = item
        added: list[str] = []
        matched: list[str] = []
        for module in incoming:
            key = module.name.casefold()
            current = by_identity.get(key)
            if current:
                current.discovered_data_type = module.data_type
                current.discovered_path = module.path
                matched.append(module.name)
            else:
                created = ConfiguredModel(
                    name=module.name,
                    tag=module.name,
                    type="None",
                    active=False,
                    source="plc_discovery",
                    discovered_data_type=module.data_type,
                    discovered_path=module.path,
                )
                existing.append(created)
                by_identity[key] = created
                added.append(module.name)
        self._document["discovered_modules"] = [item.to_dict() for item in incoming]
        self._document["models"] = [item.to_dict() for item in existing]
        for device in PlantPaxDiscoveryService.to_device_records(incoming):
            self.upsert_device(device)
        self._dirty = True
        return {"added": added, "matched": matched}

    def get_plc_profiles(self) -> list[dict[str, Any]]:
        return deepcopy(self._document["plc_profiles"])

    def upsert_plc_profile(self, profile: Mapping[str, Any]) -> None:
        profiles = list(self._document["plc_profiles"])
        name = str(profile.get("name") or "").casefold()
        profiles = [item for item in profiles if str(item.get("name") or "").casefold() != name]
        profiles.append(dict(profile))
        self._document["plc_profiles"] = profiles
        self._dirty = True

    def get_metadata(self) -> dict[str, Any]:
        return deepcopy(self._document["metadata"])

    def update_metadata(self, values: Mapping[str, Any]) -> None:
        self._document["metadata"].update(dict(values))
        self._dirty = True

    @staticmethod
    def _normalize_path(path: str | Path) -> Path:
        result = Path(path).expanduser()
        if result.suffix.lower() != PROJECT_EXTENSION:
            result = result.with_suffix(PROJECT_EXTENSION)
        return result

    def _normalize(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        doc = self.empty_document()
        if isinstance(raw, list):
            raw = {"models": raw}
        if not isinstance(raw, Mapping):
            raise ValueError("Project root must be a JSON object.")
        for key in doc:
            if key in raw:
                doc[key] = deepcopy(raw[key])
        doc["schema_version"] = SCHEMA_VERSION
        for key in ("models", "flow_paths", "devices", "discovered_modules", "plc_profiles"):
            if not isinstance(doc[key], list):
                raise ValueError(f"Project field '{key}' must be a list.")
        if not isinstance(doc["metadata"], dict):
            raise ValueError("Project field 'metadata' must be an object.")
        return doc
