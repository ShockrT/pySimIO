"""Validation services for configured pySIMIO models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from domain.models import ConfiguredModel


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(slots=True, frozen=True)
class ValidationIssue:
    model_name: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR


@dataclass(slots=True)
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [item for item in self.issues if item.severity is ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [item for item in self.issues if item.severity is ValidationSeverity.WARNING]

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def by_model(self) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for issue in self.errors:
            grouped.setdefault(issue.model_name, []).append(issue.message)
        return grouped

    def format_for_dialog(self) -> str:
        if not self.issues:
            return "No validation issues were found."
        lines: list[str] = []
        for issue in self.issues:
            label = "Error" if issue.severity is ValidationSeverity.ERROR else "Warning"
            lines.append(f"{issue.model_name}: {label} - {issue.message}")
        return "\n".join(lines)


def _number(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


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


class SimulationValidator:
    """Validate model configuration independently of component construction."""

    SUPPORTED_TYPES = {"flow", "pressure", "level", "temperature", "sensor"}

    def validate(self, models: Iterable[ConfiguredModel]) -> ValidationReport:
        model_list = list(models)
        report = ValidationReport()
        names: dict[str, int] = {}

        for model in model_list:
            key = model.name.strip().casefold()
            if key:
                names[key] = names.get(key, 0) + 1
            report.issues.extend(self.validate_model(model))

        for model in model_list:
            key = model.name.strip().casefold()
            if key and names.get(key, 0) > 1:
                report.issues.append(
                    ValidationIssue(model.name, "Model names must be unique.")
                )

        known_names = {model.name.strip() for model in model_list if model.name.strip()}
        for model in model_list:
            model_type = (model.type or "None").strip().lower()
            if model_type in {"flow", "pressure", "temperature"}:
                control = str((model.inputs or {}).get("control") or "").strip()
                if control and control not in known_names and not model.tag:
                    report.issues.append(
                        ValidationIssue(
                            model.name or "<unnamed>",
                            f"Control source '{control}' is not another configured model. "
                            "It will require a PLC/external value at runtime.",
                            ValidationSeverity.WARNING,
                        )
                    )
            elif model_type == "sensor":
                source = str((model.inputs or {}).get("source") or "").strip()
                if source and source not in known_names:
                    report.issues.append(
                        ValidationIssue(
                            model.name or "<unnamed>",
                            f"Sensor source '{source}' does not match a configured model.",
                            ValidationSeverity.WARNING,
                        )
                    )

        return report

    def validate_model(self, model: ConfiguredModel) -> list[ValidationIssue]:
        name = model.name.strip() or "<unnamed>"
        model_type = (model.type or "None").strip().lower()
        params = model.params or {}
        inputs = model.inputs or {}
        issues: list[ValidationIssue] = []

        if not model.name.strip():
            issues.append(ValidationIssue(name, "Model name is required."))

        if model_type in {"", "none"}:
            return issues

        if model_type not in self.SUPPORTED_TYPES:
            issues.append(ValidationIssue(name, f"Unsupported model type '{model.type}'."))
            return issues

        if model_type in {"flow", "pressure"}:
            if not str(inputs.get("control") or "").strip():
                issues.append(ValidationIssue(name, "A control variable is required."))
            if _number(params.get("cv_min"), 0.0) == _number(params.get("cv_max"), 100.0):
                issues.append(ValidationIssue(name, "CV minimum and maximum cannot be equal."))
            if _number(params.get("tau"), 1.0) <= 0.0:
                issues.append(ValidationIssue(name, "Time constant must be greater than zero."))

        if model_type == "temperature":
            heating_cv = str(inputs.get("heating_cv") or inputs.get("control") or "").strip()
            cooling_cv = str(inputs.get("cooling_cv") or "").strip()
            if not heating_cv and not cooling_cv:
                issues.append(ValidationIssue(name, "At least one heating or cooling control variable is required."))
            if heating_cv and _number(params.get("heating_cv_min", params.get("cv_min")), 0.0) == _number(params.get("heating_cv_max", params.get("cv_max")), 100.0):
                issues.append(ValidationIssue(name, "Heating CV minimum and maximum cannot be equal."))
            if cooling_cv and _number(params.get("cooling_cv_min"), 0.0) == _number(params.get("cooling_cv_max"), 100.0):
                issues.append(ValidationIssue(name, "Cooling CV minimum and maximum cannot be equal."))
            if _number(params.get("tau"), 5.0) <= 0.0:
                issues.append(ValidationIssue(name, "Time constant must be greater than zero."))

        if model_type == "level":
            mode = str(params.get("geom_mode") or "Volume only")
            if mode == "Volume only":
                volume = _volume_to_m3(
                    params.get("volume"), str(params.get("volume_unit") or "gal")
                )
                if volume <= 0.0:
                    issues.append(ValidationIssue(name, "Total volume must be greater than zero."))
            else:
                area = _area_to_m2(
                    params.get("area"), str(params.get("area_unit") or "m2")
                )
                height = _length_to_m(
                    params.get("height"), str(params.get("height_unit") or "m")
                )
                if area <= 0.0:
                    issues.append(ValidationIssue(name, "Area must be greater than zero."))
                if height <= 0.0:
                    issues.append(ValidationIssue(name, "Height must be greater than zero."))

            inlet_paths = list(inputs.get("inlet_paths") or [])
            outlet_paths = list(inputs.get("outlet_paths") or [])
            if not inlet_paths and not outlet_paths:
                issues.append(
                    ValidationIssue(
                        name,
                        "No inlet or outlet sources are configured; level will remain constant.",
                        ValidationSeverity.WARNING,
                    )
                )

        if model.active and not model.tag:
            issues.append(
                ValidationIssue(
                    name,
                    "The model is active but has no PLC tag; it will run offline only.",
                    ValidationSeverity.WARNING,
                )
            )

        return issues


def validate_model(model: ConfiguredModel) -> list[str]:
    """Compatibility helper returning only error messages for one model."""
    validator = SimulationValidator()
    return [
        issue.message
        for issue in validator.validate_model(model)
        if issue.severity is ValidationSeverity.ERROR
    ]
