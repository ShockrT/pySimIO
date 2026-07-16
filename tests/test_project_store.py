from pathlib import Path

from domain.models import ConfiguredModel
from persistence.project_store import PROJECT_EXTENSION, ProjectStore


def test_new_project_is_untitled_and_clean() -> None:
    store = ProjectStore()
    assert store.path is None
    assert store.display_name == "Untitled"
    assert not store.is_dirty


def test_mutation_marks_dirty_without_writing(tmp_path: Path) -> None:
    path = tmp_path / "plant.pysimio"
    store = ProjectStore(path)
    store.set_models([ConfiguredModel(name="FIT_101", type="Sensor")])
    assert store.is_dirty
    assert not path.exists()


def test_save_is_explicit(tmp_path: Path) -> None:
    store = ProjectStore()
    store.set_models([ConfiguredModel(name="FIT_101", type="Sensor")])
    saved = store.save_as(tmp_path / "plant")
    assert saved.suffix == PROJECT_EXTENSION
    assert saved.exists()
    assert not store.is_dirty


def test_open_replaces_document_and_marks_clean(tmp_path: Path) -> None:
    original = ProjectStore()
    original.set_models([ConfiguredModel(name="LIT_101", type="Sensor")])
    path = original.save_as(tmp_path / "plant.pysimio")
    opened = ProjectStore()
    opened.open(path)
    assert opened.get_models()[0].name == "LIT_101"
    assert not opened.is_dirty


def test_invalid_project_shape_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.pysimio"
    path.write_text('{"models": {}}', encoding="utf-8")
    store = ProjectStore()
    try:
        store.open(path)
    except ValueError as exc:
        assert "models" in str(exc)
    else:
        raise AssertionError("Expected invalid project structure to fail")
