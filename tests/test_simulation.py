"""Focused unit tests for the pySIMIO simulation core."""

from domain.models import ConfiguredModel
from core.sim_component_factory import build_simulation


def test_none_models_are_skipped() -> None:
    result = build_simulation([ConfiguredModel(name="Unconfigured", type="None")])
    assert result.components == {}
    assert result.errors == {}


def test_flow_maps_control_and_uses_first_order_response() -> None:
    models = [
        ConfiguredModel(name="CV", type="Sensor", params={"initial": 50.0}),
        ConfiguredModel(
            name="Flow",
            type="Flow",
            inputs={"control": "CV"},
            params={"cv_min": 0, "cv_max": 100, "pv_min": 0, "pv_max": 10, "tau": 1, "initial": 0},
        ),
    ]
    result = build_simulation(models)
    assert result.orchestrator is not None
    result.orchestrator.update(0.5)
    assert result.components["Flow"].current_value() == 2.5


def test_reverse_action_inverts_mapping() -> None:
    models = [
        ConfiguredModel(name="CV", type="Sensor", params={"initial": 25.0}),
        ConfiguredModel(
            name="Pressure",
            type="Pressure",
            inputs={"control": "CV"},
            params={
                "cv_min": 0,
                "cv_max": 100,
                "p_min": 0,
                "p_max": 200,
                "cv_relationship": "reverse",
                "tau": 1,
                "initial": 0,
            },
        ),
    ]
    result = build_simulation(models)
    assert result.orchestrator is not None
    result.orchestrator.update(1.0)
    assert result.components["Pressure"].current_value() == 150.0


def test_level_clamps_at_full_scale() -> None:
    model = ConfiguredModel(
        name="Tank",
        type="Level",
        inputs={"inlet_paths": [{"name": "Feed"}], "outlet_paths": []},
        params={
            "geom_mode": "Area + Height",
            "area": 1,
            "area_unit": "m2",
            "height": 1,
            "height_unit": "m",
            "level_unit": "percent",
            "initial": 0,
            "inlet_sources": [{"mode": "static", "value": 2, "unit": "m3/s"}],
        },
    )
    result = build_simulation([model])
    assert result.orchestrator is not None
    result.orchestrator.update(1.0)
    assert result.components["Tank"].current_value() == 100.0


def test_invalid_models_are_reported_not_raised() -> None:
    model = ConfiguredModel(name="Bad Flow", type="Flow", inputs={}, params={"cv_min": 0, "cv_max": 0})
    result = build_simulation([model])
    assert "Bad Flow" in result.errors
    assert "Bad Flow" not in result.components


def test_flow_target_is_zero_when_assigned_path_is_closed() -> None:
    models = [
        ConfiguredModel(name="CV", type="Sensor", params={"initial": 100.0}),
        ConfiguredModel(
            name="Flow",
            type="Flow",
            inputs={"control": "CV", "flow_path": "Feed"},
            params={"cv_min": 0, "cv_max": 100, "pv_min": 0, "pv_max": 10, "tau": 1, "initial": 5},
        ),
    ]
    result = build_simulation(models)
    assert result.orchestrator is not None
    result.orchestrator.update(1.0, is_path_open=lambda name: False)
    assert result.components["Flow"].current_value() == 0.0


def test_temperature_paths_gate_heating_and_cooling_independently() -> None:
    models = [
        ConfiguredModel(name="HeatCV", type="Sensor", params={"initial": 100}),
        ConfiguredModel(name="CoolCV", type="Sensor", params={"initial": 100}),
        ConfiguredModel(
            name="Temperature",
            type="Temperature",
            inputs={
                "heating_cv": "HeatCV",
                "cooling_cv": "CoolCV",
                "heating_flow_path": "Steam",
                "cooling_flow_path": "Water",
            },
            params={
                "ambient": 20,
                "heating_cv_min": 0,
                "heating_cv_max": 100,
                "cooling_cv_min": 0,
                "cooling_cv_max": 100,
                "heating_gain": 80,
                "cooling_gain": 40,
                "tau": 1,
                "initial": 20,
            },
        ),
    ]
    result = build_simulation(models)
    assert result.orchestrator is not None
    result.orchestrator.update(1.0, is_path_open=lambda name: name == "Steam")
    assert result.components["Temperature"].current_value() == 100.0
