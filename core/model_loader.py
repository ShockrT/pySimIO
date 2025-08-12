# core/model_loader.py
from __future__ import annotations
import json
from pathlib import Path
from typing import List
from core.models import ConfiguredModel

MODELS_PATH = Path("./assets/pv_models.json")

class ModelLoader:
    @staticmethod
    def load() -> List[ConfiguredModel]:
        if not MODELS_PATH.exists(): return []
        data = json.loads(MODELS_PATH.read_text(encoding="utf-8") or "[]")
        out: List[ConfiguredModel] = []
        for obj in data:
            out.append(ConfiguredModel(
                name=obj.get("name","PV"),
                type=obj.get("type", obj.get("model_type", "None")),
                tag=obj.get("tag",""),
                active=bool(obj.get("active", True)),
                fidelity=obj.get("fidelity", 0),
                inputs=obj.get("inputs", {}) or {},
                params=obj.get("params", {}) or {},
            ))
        return out

    @staticmethod
    def save(models: List[ConfiguredModel]) -> None:
        serial = [{
            "name": m.name, "type": m.type, "tag": m.tag, "active": m.active,
            "fidelity": m.fidelity, "inputs": m.inputs, "params": m.params
        } for m in models]
        MODELS_PATH.write_text(json.dumps(serial, indent=2), encoding="utf-8")
