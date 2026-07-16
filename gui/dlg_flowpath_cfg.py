from __future__ import annotations

from PyQt6 import QtWidgets
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QToolButton,
    QVBoxLayout,
)

from persistence.project_store import ProjectStore
from domain.models import FlowPath


class FlowPathConfigWizard(QtWidgets.QDialog):
    def __init__(
        self,
        plc=None,
        parent=None,
        flowpath: FlowPath | None = None,
        store: ProjectStore | None = None,
    ) -> None:
        super().__init__(parent)
        self.plc = plc
        if store is None:
            raise ValueError("FlowPathConfigWizard requires a ProjectStore")
        self.store = store
        self.original_name = flowpath.name if flowpath else None
        self.setWindowTitle("Flow Path Configuration")
        self.setMinimumWidth(620)

        root = QVBoxLayout(self)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit(flowpath.name if flowpath else "")
        name_row.addWidget(self.name_edit, 1)
        root.addLayout(name_row)

        desc_row = QHBoxLayout()
        desc_row.addWidget(QLabel("Description:"))
        self.desc_edit = QLineEdit(flowpath.description if flowpath else "")
        desc_row.addWidget(self.desc_edit, 1)
        root.addLayout(desc_row)

        root.addWidget(QLabel("Segments (valves):"))
        segment_container = QtWidgets.QWidget()
        self.segment_layout = QVBoxLayout(segment_container)
        self.segment_layout.setContentsMargins(0, 0, 0, 0)
        root.addWidget(segment_container)

        add_row = QHBoxLayout()
        add_button = QPushButton("+ Add segment")
        add_button.clicked.connect(self._on_add_segment_clicked)
        add_row.addStretch(1)
        add_row.addWidget(add_button)
        root.addLayout(add_row)

        if not self._plc_connected():
            offline = QLabel("Offline mode: valve names can be entered manually.")
            offline.setStyleSheet("color:#888; font-style:italic;")
            root.addWidget(offline)

        actions = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        save_button.clicked.connect(self._save)
        cancel_button.clicked.connect(self.reject)
        actions.addStretch(1)
        actions.addWidget(save_button)
        actions.addWidget(cancel_button)
        root.addLayout(actions)

        segments = flowpath.segments if flowpath else []
        for segment in segments or [""]:
            self._add_segment_row(segment)

    def _plc_connected(self) -> bool:
        checker = getattr(self.plc, "is_connected", None)
        return bool(checker()) if callable(checker) else False

    def _known_valves(self) -> list[str]:
        names: list[str] = []
        names.extend(str(item) for item in (getattr(self.plc, "valve_list", []) or []))
        for flowpath in self.store.get_flow_paths():
            names.extend(flowpath.segments)
        return sorted({name.strip() for name in names if name.strip()}, key=str.casefold)

    def _on_add_segment_clicked(self, checked: bool = False) -> None:
        del checked
        self._add_segment_row()

    def _add_segment_row(self, preset: str = "") -> None:
        preset_text = preset if isinstance(preset, str) else ""

        row = QHBoxLayout()
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(self._known_valves())
        combo.setCurrentText(preset_text)
        combo.setPlaceholderText("Type a valve name")

        remove_button = QToolButton()
        remove_button.setText("–")
        remove_button.clicked.connect(
            lambda checked=False, target=row: self._remove_segment_row(target)
        )

        row.addWidget(combo, 1)
        row.addWidget(remove_button)
        row.segment_combo = combo  # type: ignore[attr-defined]
        self.segment_layout.addLayout(row)

    def _remove_segment_row(self, row: QHBoxLayout) -> None:
        if self.segment_layout.count() == 1:
            row.segment_combo.setCurrentText("")  # type: ignore[attr-defined]
            return
        while row.count():
            widget = row.takeAt(0).widget()
            if widget is not None:
                widget.deleteLater()
        self.segment_layout.removeItem(row)

    def _segments(self) -> list[str]:
        result: list[str] = []
        for index in range(self.segment_layout.count()):
            row = self.segment_layout.itemAt(index).layout()
            combo = getattr(row, "segment_combo", None)
            if combo is not None:
                value = combo.currentText().strip()
                if value:
                    result.append(value)
        return result

    def _save(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Enter a flow path name.")
            return

        segments = self._segments()
        if not segments:
            QMessageBox.warning(self, "No segments", "Add at least one valve segment.")
            return

        flowpath = FlowPath(
            name=name,
            description=self.desc_edit.text().strip(),
            segments=segments,
        )
        self.store.upsert_flow_path(flowpath, previous_name=self.original_name)
        self.accept()
