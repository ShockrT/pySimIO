"""Build, wire, and update simulation components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

from domain.models import ConfiguredModel
from core.simulation_validation import validate_model
from core.simulator import (
    FlowComponent,
    LevelComponent,
    PressureComponent,
    Sensor,
    SimComponent,
    TemperatureComponent,
)

ReadValue = Callable[[str], float | None]
IsPathOpen = Callable[[str], bool]


@dataclass(slots=True)
class SimulationBuild:
    components: dict[str, SimComponent] = field(default_factory=dict)
    orchestrator: "Orchestrator | None" = None
    errors: dict[str, list[str]] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _number(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _map_range(
    value: float,
    src_min: float,
    src_max: float,
    dst_min: float,
    dst_max: float,
    reverse: bool,
) -> float:
    fraction = (value - src_min) / (src_max - src_min)
    fraction = min(max(fraction, 0.0), 1.0)
    if reverse:
        fraction = 1.0 - fraction
    return dst_min + fraction * (dst_max - dst_min)


def _volume_to_m3(value, unit: str) -> float:
    amount = _number(value, 0.0)
    normalized = (unit or "m3").lower()
    if normalized in {"gal", "gallon", "gallons", "usgal", "us_gal"}:
        return amount * 0.003785411784
    if normalized in {"l", "liter", "liters"}:
        return amount / 1000.0
    return amount


def _area_to_m2(value, unit: str) -> float:
    amount = _number(value, 0.0)
    normalized = (unit or "m2").lower()
    if normalized in {"ft2", "sqft"}:
        return amount * 0.09290304
    if normalized in {"in2", "sqin"}:
        return amount * 0.00064516
    return amount


def _length_to_m(value, unit: str) -> float:
    amount = _number(value, 0.0)
    normalized = (unit or "m").lower()
    if normalized == "ft":
        return amount * 0.3048
    if normalized == "in":
        return amount * 0.0254
    return amount


def _flow_to_m3s(value: float, unit: str) -> float:
    normalized = (unit or "m3/s").lower()
    if normalized == "gpm":
        return float(value) * 0.003785411784 / 60.0
    if normalized == "lpm":
        return float(value) / 1000.0 / 60.0
    return float(value)


def _normalized_control(value: float, minimum: float, maximum: float) -> float:
    if maximum == minimum:
        return 0.0
    return min(max((value - minimum) / (maximum - minimum), 0.0), 1.0)


def build_sim_component(model: ConfiguredModel) -> SimComponent | None:
    model_type = (model.type or "None").strip().lower()
    params = model.params or {}

    if model_type in {"", "none"}:
        return None
    if model_type == "sensor":
        return Sensor(
            model.name,
            initial=_number(params.get("initial"), 0.0),
            noise_std=_number(params.get("noise_std"), 0.0),
            lag_samples=int(_number(params.get("lag_samples"), 0.0)),
        )
    if model_type == "flow":
        return FlowComponent(
            model.name,
            tau=_number(params.get("tau"), 1.0),
            initial=_number(params.get("initial"), 0.0),
        )
    if model_type == "pressure":
        return PressureComponent(
            model.name,
            tau=_number(params.get("tau"), 2.0),
            initial=_number(params.get("initial"), 0.0),
        )
    if model_type == "temperature":
        return TemperatureComponent(
            model.name,
            tau=_number(params.get("tau"), 5.0),
            initial=_number(params.get("initial"), 25.0),
        )
    if model_type == "level":
        mode = str(params.get("geom_mode") or "Volume only")
        if mode == "Volume only":
            volume = _volume_to_m3(
                params.get("volume"), str(params.get("volume_unit") or "gal")
            )
            area = _area_to_m2(
                params.get("area"), str(params.get("area_unit") or "m2")
            ) or 1.0
            height = volume / area
        else:
            area = _area_to_m2(
                params.get("area"), str(params.get("area_unit") or "m2")
            )
            height = _length_to_m(
                params.get("height"), str(params.get("height_unit") or "m")
            )
        return LevelComponent(
            model.name,
            area_m2=area,
            height_m=height,
            level_unit=str(params.get("level_unit") or "percent"),
            initial_output=params.get("initial"),
            gain=_number(params.get("gain"), 1.0),
        )
    raise TypeError(f"Unsupported model type: {model.type}")


def build_simulation(models: Iterable[ConfiguredModel]) -> SimulationBuild:
    errors: dict[str, list[str]] = {}
    components: dict[str, SimComponent] = {}
    valid_models: list[ConfiguredModel] = []

    for model in models:
        model_errors = validate_model(model)
        if model_errors:
            errors[model.name or "<unnamed>"] = model_errors
            continue
        component = build_sim_component(model)
        if component is not None:
            components[model.name] = component
            valid_models.append(model)

    return SimulationBuild(
        components=components,
        orchestrator=Orchestrator(valid_models, components),
        errors=errors,
    )


class Orchestrator:
    """Single owner of component input wiring and deterministic update order."""

    def __init__(
        self,
        models: list[ConfiguredModel],
        components: dict[str, SimComponent],
    ) -> None:
        self.models = models
        self.components = components

    def update(
        self,
        dt: float,
        *,
        read_value: ReadValue | None = None,
        is_path_open: IsPathOpen | None = None,
    ) -> None:
        reader = read_value or (lambda _name: None)
        path_open = is_path_open or (lambda _name: True)

        for model in self.models:
            component = self.components[model.name]
            model_type = model.type.lower()
            if model_type in {"flow", "pressure", "temperature"}:
                self._wire_target_model(model, component, reader, path_open)
            elif model_type == "sensor":
                self._wire_sensor(model, component)

        for model in self.models:
            if model.type.lower() != "level":
                self.components[model.name].update(dt)

        for model in self.models:
            if model.type.lower() == "level":
                component = self.components[model.name]
                self._wire_level(model, component, reader)
                component.update(dt)

    def _resolve(self, name: str, reader: ReadValue) -> float:
        component = self.components.get(name)
        if component is not None:
            return component.current_value()
        value = reader(name)
        return 0.0 if value is None else float(value)

    def _wire_target_model(
        self,
        model: ConfiguredModel,
        component: SimComponent,
        reader: ReadValue,
        is_path_open: IsPathOpen,
    ) -> None:
        params = model.params or {}
        inputs = model.inputs or {}
        if model.type.lower() == "temperature":
            heating_name = str(inputs.get("heating_cv") or inputs.get("control") or "").strip()
            cooling_name = str(inputs.get("cooling_cv") or "").strip()
            heating_path = str(inputs.get("heating_flow_path") or "").strip()
            cooling_path = str(inputs.get("cooling_flow_path") or "").strip()
            heating = self._resolve(heating_name, reader) if heating_name and is_path_open(heating_path) else 0.0
            cooling = self._resolve(cooling_name, reader) if cooling_name and is_path_open(cooling_path) else 0.0
            heat_fraction = _normalized_control(
                heating,
                _number(params.get("heating_cv_min", params.get("cv_min")), 0.0),
                _number(params.get("heating_cv_max", params.get("cv_max")), 100.0),
            )
            cool_fraction = _normalized_control(
                cooling,
                _number(params.get("cooling_cv_min"), 0.0),
                _number(params.get("cooling_cv_max"), 100.0),
            )
            target = (
                _number(params.get("ambient"), 25.0)
                + heat_fraction * _number(params.get("heating_gain", params.get("k")), 0.0)
                - cool_fraction * _number(params.get("cooling_gain"), 0.0)
            )
            target = min(max(target, _number(params.get("pv_min"), -273.15)), _number(params.get("pv_max"), 1000.0))
        else:
            control = str(inputs.get("control") or "").strip()
            cv = self._resolve(control, reader)
            cv_min = _number(params.get("cv_min"), 0.0)
            cv_max = _number(params.get("cv_max"), 100.0)
            reverse = str(params.get("cv_relationship") or "direct").lower() == "reverse"
            if model.type.lower() == "pressure":
                out_min = _number(params.get("p_min"), 0.0)
                out_max = _number(params.get("p_max"), 200.0)
            else:
                out_min = _number(params.get("pv_min"), 0.0)
                out_max = _number(params.get("pv_max"), 1000.0)
            target = _map_range(cv, cv_min, cv_max, out_min, out_max, reverse)
            target *= _number(params.get("k"), 1.0)
            flow_path = str(inputs.get("flow_path") or "").strip()
            if flow_path and not is_path_open(flow_path):
                target = _number(params.get("closed_path_value"), 0.0)
        setter = getattr(component, "set_target", None)
        if callable(setter):
            setter(target)

    def _wire_sensor(
        self,
        model: ConfiguredModel,
        component: SimComponent,
    ) -> None:
        if not isinstance(component, Sensor):
            return
        source_name = str((model.inputs or {}).get("source") or "").strip()
        source = self.components.get(source_name)
        component.set_source(source.current_value if source else None)

    def _wire_level(
        self,
        model: ConfiguredModel,
        component: SimComponent,
        reader: ReadValue,
    ) -> None:
        if not isinstance(component, LevelComponent):
            return
        inputs = model.inputs or {}
        params = model.params or {}
        qin = self._sum_flow_sources(
            inputs.get("inlet_paths"), params.get("inlet_sources"), reader
        )
        qout = self._sum_flow_sources(
            inputs.get("outlet_paths"), params.get("outlet_sources"), reader
        )
        component.set_flows(qin, qout)

    def _sum_flow_sources(self, paths, sources, reader: ReadValue) -> float:
        total = 0.0
        paths = paths or []
        sources = sources or []

        for index, item in enumerate(paths):
            source = sources[index] if index < len(sources) else {}
            mode = str(source.get("mode") or "").lower()
            unit = str(source.get("unit") or "m3/s")

            if mode == "static":
                total += _flow_to_m3s(_number(source.get("value"), 0.0), unit)
            elif mode == "tag":
                value = reader(str(source.get("tag") or ""))
                total += _flow_to_m3s(0.0 if value is None else float(value), unit)
            else:
                name = str(
                    (item or {}).get("name")
                    if isinstance(item, dict)
                    else item or ""
                )
                total += self._resolve(name, reader)
        return total
