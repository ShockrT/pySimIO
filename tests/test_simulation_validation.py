from core.simulation_validation import (
    SimulationValidator,
    ValidationSeverity,
)
from domain.models import ConfiguredModel


def test_active_offline_model_is_warning_not_error() -> None:
    report = SimulationValidator().validate(
        [ConfiguredModel(name="Sensor", type="Sensor", active=True)]
    )
    assert report.is_valid
    assert any(
        issue.severity is ValidationSeverity.WARNING for issue in report.issues
    )


def test_duplicate_names_are_errors() -> None:
    report = SimulationValidator().validate(
        [
            ConfiguredModel(name="PV", type="Sensor"),
            ConfiguredModel(name="PV", type="Sensor"),
        ]
    )
    assert not report.is_valid
    assert "Model names must be unique." in report.by_model()["PV"]
