import os
from json import JSONDecodeError
from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QMessageBox, QComboBox, QHBoxLayout, QToolButton, QPushButton, QLabel, QVBoxLayout, \
    QLineEdit

from core.data import FlowPath, Valve
import json

class FlowPathConfigWizard(QtWidgets.QDialog):
    flow_path_saved = pyqtSignal(str)  # Emit the new flow path name

    def __init__(self, plc, parent=None, preset_name: str | None = None, preset_description: str | None = None,
                 preset_segments: list[str] | None = None):
        super().__init__(parent)
        self.plc = plc
        self.setWindowTitle("Flow Path Configuration")
        root = QVBoxLayout(self)

        # --- name / description controls (use your existing ones if you already had them) ---
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit(preset_name or "")
        name_row.addWidget(self.name_edit, 1)
        root.addLayout(name_row)

        desc_row = QHBoxLayout()
        desc_row.addWidget(QLabel("Description:"))
        self.desc_edit = QLineEdit(preset_description or "")
        desc_row.addWidget(self.desc_edit, 1)
        root.addLayout(desc_row)

        # --- segments area (replaces your listbox) ---
        root.addWidget(QLabel("Segments (valves):"))

        seg_container = QtWidgets.QWidget()
        self.seg_layout = QVBoxLayout(seg_container)
        self.seg_layout.setContentsMargins(0, 0, 0, 0)
        self.seg_layout.setSpacing(6)
        root.addWidget(seg_container)

        # add row button
        add_row = QHBoxLayout()
        self.btn_add_seg = QPushButton("+ Add segment")
        self.btn_add_seg.clicked.connect(lambda: self._add_segment_row())
        add_row.addStretch(1)
        add_row.addWidget(self.btn_add_seg)
        root.addLayout(add_row)

        # offline banner if needed
        if not getattr(self.plc, "is_connected", False):
            offline = QLabel("Offline mode: type valve names manually or pick from any cached suggestions.")
            offline.setStyleSheet("color:#888; font-style: italic;")
            root.addWidget(offline)

        # action buttons
        actions = QHBoxLayout()
        self.btn_save = QPushButton("Save")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_save.clicked.connect(self._on_save)
        self.btn_cancel.clicked.connect(self.reject)
        actions.addStretch(1)
        actions.addWidget(self.btn_save)
        actions.addWidget(self.btn_cancel)
        root.addLayout(actions)

        # initialize rows
        if preset_segments:
            for s in preset_segments:
                self._add_segment_row(preset=s)
        else:
            self._add_segment_row()  # start with one empty row

    def _known_valves(self) -> list[str]:
        """Collect suggestions from PLC (if online) plus any cached names from existing flowpaths.json."""
        names = list(getattr(self.plc, "valve_list", []) or [])

        # augment with names seen in saved flowpaths (optional but helpful offline)
        try:
            with open("./assets/flowpaths.json", "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            for fp in data.values():
                for seg in fp.get("segments", []):
                    if isinstance(seg, str):
                        names.append(seg)
                    else:
                        nm = seg.get("name") if isinstance(seg, dict) else getattr(seg, "name", None)
                        if nm:
                            names.append(nm)
        except Exception:
            pass

        # unique + sorted
        names = [n for n in names if n]
        return sorted(set(names), key=str.lower)

    def _add_segment_row(self, preset: str | None = None):
        row = QHBoxLayout()

        combo = QComboBox()
        combo.setEditable(True)

        vals = self._known_valves()
        if vals:
            combo.addItems(vals)
        else:
            combo.setPlaceholderText("Type a valve name")

        if preset:
            combo.setCurrentText(preset)

        btn_remove = QToolButton()
        btn_remove.setText("–")
        btn_remove.setAutoRaise(True)
        btn_remove.clicked.connect(lambda: self._remove_segment_row(row))

        row.addWidget(combo, 1)
        row.addWidget(btn_remove, 0)

        # stash a reference so we can find the combo later
        row._seg_combo = combo  # type: ignore[attr-defined]

        self.seg_layout.addLayout(row)

    def _remove_segment_row(self, row_layout: QHBoxLayout):
        # keep at least one row
        if self.seg_layout.count() <= 1:
            # clear the one combo instead
            for i in range(row_layout.count()):
                w = row_layout.itemAt(i).widget()
                if isinstance(w, QComboBox):
                    w.setCurrentText("")
            return

        while row_layout.count():
            item = row_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self.seg_layout.removeItem(row_layout)

    def _collect_segments(self) -> list[str]:
        segs: list[str] = []
        for i in range(self.seg_layout.count()):
            item = self.seg_layout.itemAt(i)
            row = item.layout()
            if not isinstance(row, QHBoxLayout):
                continue
            # stored combo on the row for easy access
            combo = getattr(row, "_seg_combo", None)
            if isinstance(combo, QComboBox):
                name = combo.currentText().strip()
                if name:
                    segs.append(name)
        return segs

    def _on_save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Please enter a Flow Path name.")
            return

        segs = self._collect_segments()
        if not segs:
            QMessageBox.warning(self, "No segments", "Add at least one valve segment (or type a name).")
            return

        desc = self.desc_edit.text().strip()

        # Persist using wizard’s JSON schema:
        #   ./assets/flowpaths.json -> { "<name>": {"description": "...", "segments": ["V1","V2",...]} }
        os.makedirs("./assets", exist_ok=True)
        try:
            try:
                with open("./assets/flowpaths.json", "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
            except FileNotFoundError:
                data = {}

            data[name] = {"description": desc, "segments": segs}

            with open("./assets/flowpaths.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))
            return

        self.accept()