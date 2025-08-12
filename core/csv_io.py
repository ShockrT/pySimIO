# csv_io.py
from __future__ import annotations

import csv
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Iterable, List, Dict, Any, re

from core.models import ConfiguredModel

# ---- CSV SCHEMAS ----
# We include a superset of columns so the template is stable and re-usable across types.
MODEL_FIELDNAMES = [
    # core
    "name", "type", "tag", "active", "fidelity",
    # inputs (linkages)
    "inputs.inlet_flow", "inputs.outlet_flow", "inputs.control",
    # common params
    "params.initial", "params.tau", "params.k",
    # pressure-specific
    "params.k_in", "params.k_out", "params.leak",
    # level-specific
    "params.area",
    # temperature-specific
    "params.ambient",
]

FLOWPATH_FIELDNAMES = ["name", "description", "segments"]  # segments = names joined by ';'


# ---------------------------
# Models: Export / Import CSV
# ---------------------------
def export_models_csv(models: Iterable[ConfiguredModel], path: str | Path, include_example_when_empty: bool = True) -> None:
    path = Path(path)
    rows = list(_model_to_rows(models))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MODEL_FIELDNAMES)
        writer.writeheader()
        if rows:
            writer.writerows(rows)
        elif include_example_when_empty:
            # Write one example row as a template
            writer.writerow({
                "name": "PV-001",
                "type": "Flow",
                "tag": "Tank1_Flow_PV",
                "active": "True",
                "fidelity": "0",
                "inputs.control": "PUMP-01",
                "params.initial": "0",
                "params.tau": "1.5",
                "params.k": "1.0",
            })


def import_models_csv(path: str | Path) -> List[ConfiguredModel]:
    path = Path(path)
    out: List[ConfiguredModel] = []
    with path.open("r", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            # Skip blank/template rows that don't have a name or type
            if not (raw.get("name") or raw.get("type")):
                continue
            model = _row_to_model(raw)
            out.append(model)
    return out


def _model_to_rows(models: Iterable[ConfiguredModel]) -> Iterable[Dict[str, str]]:
    for m in models:
        # Base
        row: Dict[str, Any] = {
            "name": m.name,
            "type": m.type,
            "tag": m.tag,
            "active": str(bool(m.active)),
            "fidelity": str(m.fidelity),
        }
        # Inputs
        row["inputs.inlet_flow"]  = m.inputs.get("inlet_flow", "")
        row["inputs.outlet_flow"] = m.inputs.get("outlet_flow", "")
        row["inputs.control"]     = m.inputs.get("control", "")

        # Params (write all known keys if present; leave others blank)
        p = m.params or {}
        for key in ["initial", "tau", "k", "k_in", "k_out", "leak", "area", "ambient"]:
            row[f"params.{key}"] = _maybe_num_to_str(p.get(key, ""))

        # Ensure stable column order with MODEL_FIELDNAMES
        yield {k: row.get(k, "") for k in MODEL_FIELDNAMES}


def _row_to_model(row: Dict[str, str]) -> ConfiguredModel:
    # Core
    name = row.get("name", "").strip()
    mtype = (row.get("type") or "None").strip()
    tag = row.get("tag", "").strip()
    active = _parse_bool(row.get("active", "True"))
    fidelity = _parse_int_or_str(row.get("fidelity", "0"))

    # Inputs
    inputs = {}
    for k in ("inlet_flow", "outlet_flow", "control"):
        v = (row.get(f"inputs.{k}") or "").strip()
        if v:
            inputs[k] = v

    # Params
    params: Dict[str, float] = {}
    for key in ["initial", "tau", "k", "k_in", "k_out", "leak", "area", "ambient"]:
        val = row.get(f"params.{key}")
        if val is not None and str(val).strip() != "":
            num = _parse_float(val)
            if num is not None:
                params[key] = num

    # Construct via your canonical model class
    cm = ConfiguredModel(
        name=name,
        type=mtype,      # your ConfiguredModel uses 'type' as source of truth
        tag=tag,
        active=active,
        fidelity=fidelity,
        inputs=inputs,
        params=params,
    )
    return cm


# ------------------------------
# Flow Paths: Export / Import CSV
# ------------------------------
def export_flowpaths_csv(flowpaths: Iterable[Any], path: str | Path, include_example_when_empty: bool = True) -> None:
    """
    Exports a generic flowpath CSV. Works with dataclasses or simple objects
    exposing attributes by name; falls back to __dict__ if available.
    """
    path = Path(path)
    rows = list(_flowpaths_to_rows(flowpaths))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FLOWPATH_FIELDNAMES)
        writer.writeheader()
        if rows:
            writer.writerows(rows)
        elif include_example_when_empty:
            writer.writerow({
                "name": "FP-001",
                "source": "Tank-01",
                "destination": "Pump-01",
                "tag": "FlowPath_T1_to_P1",
                "max_flow": "100.0",
                "resistance_k": "2.5",
                "length": "10.0",
                "diameter": "0.05",
                "attributes_json": json.dumps({"material": "SS316", "notes": "template row"}),
            })


def import_flowpaths_csv(path: str | Path, flowpath_ctor=None) -> List[Any]:
    out: List[Any] = []
    path = Path(path)
    with path.open("r", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            name = (raw.get("name") or "").strip()
            if not name:
                continue
            desc = (raw.get("description") or "").strip()
            segs_raw = (raw.get("segments") or "").strip()
            # accept ; or , as separators
            seg_names = [s.strip() for s in re.split(r"[;,]", segs_raw) if s.strip()] if segs_raw else []

            item = {"name": name, "description": desc, "segments": seg_names}

            # If a ctor was supplied, we *could* attempt to construct FlowPath objects,
            # but that would require Valve instances; keeping dicts is simpler,
            # and your set_flowpaths writes JSON in the wizard's schema.
            out.append(item)
    return out


def _flowpaths_to_rows(flowpaths: Iterable[Any]) -> Iterable[Dict[str, str]]:
    for fp in flowpaths:
        # Accept dicts, dataclasses, or objects with __dict__
        if isinstance(fp, dict):
            name = fp.get("name", "")
            description = fp.get("description", "")
            segs = fp.get("segments", [])
        elif is_dataclass(fp):
            data = asdict(fp)
            name = data.get("name", "")
            description = data.get("description", "")
            # segments might be a list of Valve dicts -> use 'name' if present
            raw = data.get("segments", [])
            segs = [(s.get("name") if isinstance(s, dict) else getattr(s, "name", str(s))) for s in raw]
        elif hasattr(fp, "__dict__"):
            data = dict(fp.__dict__)
            name = data.get("name", "")
            description = data.get("description", "")
            raw = data.get("segments", [])
            segs = [getattr(s, "name", str(s)) for s in raw]
        else:
            continue

        yield {
            "name": name,
            "description": description,
            "segments": ";".join([s for s in segs if s]),
        }


def _row_to_flowpath(row: Dict[str, str], flowpath_ctor=None) -> Any:
    attrs: Dict[str, Any] = {
        "name": row.get("name", "").strip(),
        "source": row.get("source", "").strip(),
        "destination": row.get("destination", "").strip(),
        "tag": row.get("tag", "").strip(),
    }
    for num_key in ("max_flow", "resistance_k", "length", "diameter"):
        v = row.get(num_key)
        if v is not None and str(v).strip() != "":
            num = _parse_float(v)
            if num is not None:
                attrs[num_key] = num

    # Merge extras from attributes_json
    extras_raw = row.get("attributes_json")
    if extras_raw:
        try:
            extras = json.loads(extras_raw)
            if isinstance(extras, dict):
                # don't clobber already-parsed known keys
                for k, v in extras.items():
                    attrs.setdefault(k, v)
        except Exception:
            pass

    if flowpath_ctor is None:
        return attrs
    try:
        return flowpath_ctor(**attrs)
    except TypeError:
        # Constructor mismatch; return dict so caller can adapt
        return attrs


# ---- small parsing helpers ----
def _parse_bool(s: str | None) -> bool:
    if s is None:
        return True
    return str(s).strip().lower() in ("1", "true", "yes", "y", "on")


def _parse_int_or_str(s: str | None):
    if s is None:
        return 0
    try:
        return int(str(s).strip())
    except Exception:
        return str(s).strip()


def _parse_float(s: str | None):
    try:
        return float(str(s).strip())
    except Exception:
        return None


def _maybe_num_to_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v)
