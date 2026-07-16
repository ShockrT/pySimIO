"""
dlg_model_cfg.py
Model configuration dialog (offline-safe) for Flow/Pressure/Level/Temperature/Sensor.

- Flow:     CV->PV (linear) + k, tau, initial
- Pressure: CV->PV (linear) + relationship + k, tau, initial
- Level:    Tank/vessel integrator with geometry & per-row inlet/outlet flow sources (tag|static)
           Output is always in transmitter's level_unit ('percent'|'m'|'ft'|'in')
- Temperature: (placeholder section; keep/edit as needed)
"""

from __future__ import annotations
from typing import Optional, List, Dict
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit, QComboBox,
    QCheckBox, QPushButton, QGroupBox, QMessageBox, QWidget, QScrollArea, QToolButton,
    QSizePolicy, QLayout,
    QStackedWidget)

from persistence.project_store import ProjectStore
from domain.models import ConfiguredModel


MODEL_TYPES = ["None", "Flow", "Pressure", "Level", "Temperature", "Sensor"]


# ---------- Typed Row Widget (for Level inlet/outlet rows) ----------

class FlowSourceRow(QWidget):
    """
    One inlet/outlet row with typed attributes so IDEs can resolve them.
    Fields:
      - path_combo: flow path name (editable)
      - mode_combo: "tag" | "static"
      - tag_edit:   PLC tag for flow rate (when mode = tag)
      - val_edit:   static flow value (when mode = static)
      - val_unit:   unit for flow value/tag ("gpm","lpm","m3/s")
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.path_combo = QComboBox()
        self.mode_combo = QComboBox()
        self.tag_edit   = QLineEdit()
        self.val_edit   = QLineEdit()
        self.val_unit   = QComboBox()

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)


# ---------- Dialog ----------

class ModelConfigWizard(QDialog):
    """
    Offline-safe Model Configuration dialog.
    Pass `plc` (may be offline), and optionally an existing ConfiguredModel `pv`.
    """
    def __init__(self, plc, pv: Optional[ConfiguredModel] = None, parent=None, store: ProjectStore | None = None):
        super().__init__(parent)
        self.plc = plc
        if store is None:
            raise ValueError("ModelConfigWizard requires a ProjectStore")
        self.store = store
        self.pv: ConfiguredModel = pv if pv is not None else ConfiguredModel(name="", type="None", tag="")
        if self.pv.inputs is None:
            self.pv.inputs = {}
        if self.pv.params is None:
            self.pv.params = {}

        self.setWindowTitle("Configure Model")
        self.setMinimumWidth(820)

        self._build_ui()
        self._load_from_model()

    # ---------- UI BUILD ----------

    def _build_ui(self):
        root = QVBoxLayout(self)

        # Offline hint
        if not getattr(self.plc, "is_connected", False):
            hint = QLabel("Offline mode: lists may be empty; type values into editable fields.")
            hint.setStyleSheet("color:#888; font-style:italic;")
            root.addWidget(hint)

        # Basic metadata
        meta_grp = QGroupBox("Basic")
        meta_form = QFormLayout(meta_grp)

        self.name_edit = QLineEdit()
        self.tag_edit = QLineEdit()
        self.active_chk = QCheckBox("Active")
        self.type_combo = QComboBox()
        self.type_combo.addItems(MODEL_TYPES)
        self.type_combo.currentTextChanged.connect(self._on_type_changed)

        meta_form.addRow("Name", self.name_edit)
        meta_form.addRow("PLC Tag", self.tag_edit)
        meta_form.addRow("Type", self.type_combo)
        meta_form.addRow("", self.active_chk)

        root.addWidget(meta_grp)

        # Scrollable area for type-specific config
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_w = QWidget()
        self.scroll.setWidget(self.scroll_w)
        self.stack_layout = QVBoxLayout(self.scroll_w)
        self.stack_layout.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.scroll, 1)

        # Sections (only one is visible at a time)
        self.section_none = QLabel("Select a model type to configure.")
        self.section_flow = self._build_flow_section()
        self.section_pressure = self._build_pressure_section()
        self.section_level = self._build_level_section()
        self.section_temperature = self._build_temperature_section()
        self.section_sensor = self._build_sensor_section()

        for w in (
            self.section_none,
            self.section_flow,
            self.section_pressure,
            self.section_level,
            self.section_temperature,
            self.section_sensor,
        ):
            self.stack_layout.addWidget(w)

        # Bottom actions
        btns = QHBoxLayout()
        btns.addStretch(1)
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        self.save_btn.clicked.connect(self._on_save)
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.save_btn)
        btns.addWidget(self.cancel_btn)
        root.addLayout(btns)

        self._apply_type_visibility(self.pv.type or "None")

    # ---------- Sections per type ----------

    # FLOW (CV->PV linear) — integrated group
    def _build_flow_section(self) -> QWidget:
        w = QGroupBox("Flow (Line/Pipe)")
        form = QFormLayout(w)

        # Integrated group: Control Variable + CV→PV ranges
        self.flow_control = QComboBox(); self._populate_control_combo(self.flow_control)
        self.flow_path = QComboBox(); self._populate_flowpath_combo(self.flow_path)
        self.flow_relationship = QComboBox(); self.flow_relationship.addItems(["direct", "reverse"])
        self.flow_cv_min  = QLineEdit(); self.flow_cv_min.setPlaceholderText("0")
        self.flow_cv_max  = QLineEdit(); self.flow_cv_max.setPlaceholderText("100")
        self.flow_pv_min  = QLineEdit(); self.flow_pv_min.setPlaceholderText("0")      # eng units of flow
        self.flow_pv_max  = QLineEdit(); self.flow_pv_max.setPlaceholderText("1000")   # example eng range

        # Core params
        self.flow_k = QLineEdit(); self.flow_k.setPlaceholderText("k (default 1.0)")
        self.flow_tau = QLineEdit(); self.flow_tau.setPlaceholderText("τ (s) (default 1.0)")
        self.flow_initial = QLineEdit(); self.flow_initial.setPlaceholderText("initial (default 0.0)")

        form.addRow(self._bold_label("Definition"), QLabel(""))
        form.addRow("Control Variable", self.flow_control)
        form.addRow("Flow path", self.flow_path)
        form.addRow("CV relationship", self.flow_relationship)
        form.addRow(self._bold_label("CV→PV Ranges"), QLabel(""))
        form.addRow("CV range (min/max)", self._row2(self.flow_cv_min, self.flow_cv_max))
        form.addRow("Flow range (min/max)", self._row2(self.flow_pv_min, self.flow_pv_max))
        form.addRow(self._bold_label("Dynamics"), QLabel(""))
        form.addRow("Gain k", self.flow_k)
        form.addRow("Time constant τ", self.flow_tau)
        form.addRow("Initial value", self.flow_initial)
        return w

    # PRESSURE (CV->PV linear) — integrated group
    def _build_pressure_section(self) -> QWidget:
        w = QGroupBox("Pressure (Line/Pipe)")
        form = QFormLayout(w)

        self.press_control = QComboBox(); self._populate_control_combo(self.press_control)
        self.press_path = QComboBox(); self._populate_flowpath_combo(self.press_path)
        self.press_relationship = QComboBox(); self.press_relationship.addItems(["direct", "reverse"])
        self.press_cv_min  = QLineEdit(); self.press_cv_min.setPlaceholderText("0")
        self.press_cv_max  = QLineEdit(); self.press_cv_max.setPlaceholderText("100")
        self.press_p_min   = QLineEdit(); self.press_p_min.setPlaceholderText("0")
        self.press_p_max   = QLineEdit(); self.press_p_max.setPlaceholderText("200")
        self.press_tau     = QLineEdit(); self.press_tau.setPlaceholderText("τ (s) (default 2.0)")
        self.press_k       = QLineEdit(); self.press_k.setPlaceholderText("k (default 1.0)")
        self.press_initial = QLineEdit(); self.press_initial.setPlaceholderText("initial (psi)")

        form.addRow(self._bold_label("Definition"), QLabel(""))
        form.addRow("Control Variable", self.press_control)
        form.addRow("Flow path", self.press_path)
        form.addRow("CV relationship", self.press_relationship)
        form.addRow(self._bold_label("Ranges"), QLabel(""))
        form.addRow("CV range (min/max)", self._row2(self.press_cv_min, self.press_cv_max))
        form.addRow("Pressure range (min/max)", self._row2(self.press_p_min, self.press_p_max))
        form.addRow(self._bold_label("Dynamics"), QLabel(""))
        form.addRow("τ (s)", self.press_tau)
        form.addRow("Gain k", self.press_k)
        form.addRow("Initial (psi)", self.press_initial)

        note = QLabel("Note: Pressure is mapped linearly from CV, then filtered by τ and k.")
        note.setStyleSheet("color:#888;")
        form.addRow(note)
        return w

    # LEVEL — tank/vessel integrator with typed rows
    def _build_level_section(self) -> QWidget:
        level_group = QGroupBox("Level (Tank/Vessel)")
        outer_v = QVBoxLayout(level_group)

        # --- Geometry group ---
        geo_group = QGroupBox("Geometry")
        geo_form = QFormLayout()
        geo_group.setLayout(geo_form)

        self.level_geom_mode = QComboBox()
        self.level_geom_mode.addItems(["Volume only", "Area + Height"])
        self.level_volume = QLineEdit(); self.level_volume.setPlaceholderText("e.g. 10000")
        self.level_vol_unit = QComboBox(); self.level_vol_unit.addItems(["gal", "L", "m3"])

        self.level_area = QLineEdit(); self.level_area.setPlaceholderText("e.g. 10.0")
        self.level_area_unit = QComboBox(); self.level_area_unit.addItems(["m2", "ft2", "in2"])

        self.level_height = QLineEdit(); self.level_height.setPlaceholderText("e.g. 3.0")
        self.level_height_unit = QComboBox(); self.level_height_unit.addItems(["m", "ft", "in"])

        # compact rows with value + unit
        vol_row = QWidget(); vol_h = QHBoxLayout(vol_row); vol_h.setContentsMargins(0,0,0,0)
        vol_h.addWidget(self.level_volume); vol_h.addWidget(self.level_vol_unit)

        area_row = QWidget(); area_h = QHBoxLayout(area_row); area_h.setContentsMargins(0,0,0,0)
        area_h.addWidget(self.level_area); area_h.addWidget(self.level_area_unit)

        ht_row = QWidget(); ht_h = QHBoxLayout(ht_row); ht_h.setContentsMargins(0,0,0,0)
        ht_h.addWidget(self.level_height); ht_h.addWidget(self.level_height_unit)

        geo_form.addRow("Geometry mode", self.level_geom_mode)
        geo_form.addRow("Total volume", vol_row)
        geo_form.addRow("Area", area_row)
        geo_form.addRow("Height", ht_row)

        def _toggle_geom(mode: str):
            is_vol = (mode == "Volume only")
            self.level_volume.setEnabled(True)
            self.level_vol_unit.setEnabled(True)
            self.level_area.setEnabled(not is_vol)
            self.level_area_unit.setEnabled(not is_vol)
            self.level_height.setEnabled(not is_vol)
            self.level_height_unit.setEnabled(not is_vol)

        self.level_geom_mode.currentTextChanged.connect(_toggle_geom)
        _toggle_geom(self.level_geom_mode.currentText())

        outer_v.addWidget(geo_group)

        # --- Transmitter & dynamics ---
        cfg_group = QGroupBox("Transmitter & Dynamics")
        cfg_form = QFormLayout()
        cfg_group.setLayout(cfg_form)

        self.level_unit = QComboBox()
        self.level_unit.addItems(["percent", "m", "ft", "in"])

        self.level_initial = QLineEdit(); self.level_initial.setPlaceholderText("initial (in selected unit)")
        self.level_gain = QLineEdit(); self.level_gain.setPlaceholderText("gain (default 1.0)")

        cfg_form.addRow("Level unit", self.level_unit)
        cfg_form.addRow("Initial", self.level_initial)
        cfg_form.addRow("Gain", self.level_gain)

        outer_v.addWidget(cfg_group)

        # --- Inlets ---
        in_group = QGroupBox("Inlet Flows")
        in_v = QVBoxLayout(in_group)

        self.level_inlet_container = QWidget(in_group)
        self.level_inlet_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        self.level_inlet_layout = QVBoxLayout(self.level_inlet_container)
        self.level_inlet_layout.setContentsMargins(0, 0, 0, 0)
        self.level_inlet_layout.setSpacing(6)
        self.level_inlet_layout.setSizeConstraint(
            QLayout.SizeConstraint.SetMinAndMaxSize
        )
        in_v.addWidget(self.level_inlet_container)

        btn_in = QPushButton("+ Add inlet")
        btn_in.clicked.connect(self._on_add_inlet_clicked)
        in_v.addWidget(btn_in)

        outer_v.addWidget(in_group)

        # --- Outlets ---
        out_group = QGroupBox("Outlet Flows")
        out_v = QVBoxLayout(out_group)

        self.level_outlet_container = QWidget(out_group)
        self.level_outlet_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        self.level_outlet_layout = QVBoxLayout(self.level_outlet_container)
        self.level_outlet_layout.setContentsMargins(0, 0, 0, 0)
        self.level_outlet_layout.setSpacing(6)
        self.level_outlet_layout.setSizeConstraint(
            QLayout.SizeConstraint.SetMinAndMaxSize
        )
        out_v.addWidget(self.level_outlet_container)

        btn_out = QPushButton("+ Add outlet")
        btn_out.clicked.connect(self._on_add_outlet_clicked)
        out_v.addWidget(btn_out)

        outer_v.addWidget(out_group)

        # Ensure at least one row each
        self._add_flow_source_row(self.level_inlet_layout)
        self._add_flow_source_row(self.level_outlet_layout)

        return level_group

    # TEMPERATURE
    def _build_temperature_section(self) -> QWidget:
        root = QGroupBox("Temperature")
        outer = QVBoxLayout(root)

        process_group = QGroupBox("Process")
        process_form = QFormLayout(process_group)
        self.temp_ambient = QLineEdit()
        self.temp_pv_min = QLineEdit()
        self.temp_pv_max = QLineEdit()
        self.temp_tau = QLineEdit()
        self.temp_initial = QLineEdit()
        process_form.addRow("Ambient / neutral", self.temp_ambient)
        process_form.addRow("Temperature range", self._row2(self.temp_pv_min, self.temp_pv_max))
        process_form.addRow("Time constant tau", self.temp_tau)
        process_form.addRow("Initial temperature", self.temp_initial)
        outer.addWidget(process_group)

        heat_group = QGroupBox("Heating")
        heat_form = QFormLayout(heat_group)
        self.temp_heating_cv = QComboBox(); self._populate_control_combo(self.temp_heating_cv)
        self.temp_heating_path = QComboBox(); self._populate_flowpath_combo(self.temp_heating_path)
        self.temp_heating_cv_min = QLineEdit()
        self.temp_heating_cv_max = QLineEdit()
        self.temp_heating_gain = QLineEdit()
        heat_form.addRow("Heating CV", self.temp_heating_cv)
        heat_form.addRow("Heating flow path", self.temp_heating_path)
        heat_form.addRow("Heating CV range", self._row2(self.temp_heating_cv_min, self.temp_heating_cv_max))
        heat_form.addRow("Heating gain", self.temp_heating_gain)
        outer.addWidget(heat_group)

        cool_group = QGroupBox("Cooling")
        cool_form = QFormLayout(cool_group)
        self.temp_cooling_cv = QComboBox(); self._populate_control_combo(self.temp_cooling_cv)
        self.temp_cooling_path = QComboBox(); self._populate_flowpath_combo(self.temp_cooling_path)
        self.temp_cooling_cv_min = QLineEdit()
        self.temp_cooling_cv_max = QLineEdit()
        self.temp_cooling_gain = QLineEdit()
        cool_form.addRow("Cooling CV", self.temp_cooling_cv)
        cool_form.addRow("Cooling flow path", self.temp_cooling_path)
        cool_form.addRow("Cooling CV range", self._row2(self.temp_cooling_cv_min, self.temp_cooling_cv_max))
        cool_form.addRow("Cooling gain", self.temp_cooling_gain)
        outer.addWidget(cool_group)

        note = QLabel("Target = ambient + heating contribution - cooling contribution")
        note.setStyleSheet("color:#888;")
        outer.addWidget(note)
        return root

    def _build_sensor_section(self) -> QWidget:
        w = QGroupBox("Sensor")
        form = QFormLayout(w)
        self.sensor_initial = QLineEdit(); self.sensor_initial.setPlaceholderText("initial")
        form.addRow("Initial value", self.sensor_initial)
        return w

    # ---------- Helpers to populate combos ----------

    def _populate_control_combo(self, combo: QComboBox):
        combo.setEditable(True)

        # Start with whatever the PLC exposes; coerce to strings
        raw_items = list(getattr(self.plc, "cv_list", []) or [])

        # Also include any existing values from the current model (if present)
        for key in ("control", "heating_cv", "cooling_cv"):
            try:
                val = (self.pv.inputs or {}).get(key, "")
                if val:
                    raw_items.append(val)
            except Exception:
                pass

        # Deduplicate & normalize to strings, then sort case-insensitively
        items: list[str] = sorted(
            {str(i) for i in raw_items if i},  # set comp → unique strings
            key=lambda s: s.lower()  # callable type is unambiguous
        )

        if items:
            combo.addItems(items)
        else:
            combo.setPlaceholderText("Type a control variable")

    def _populate_flowpath_combo(self, combo: QComboBox) -> None:
        combo.setEditable(True)

        raw: list[str] = []

        # 1) From PLC/provider (if connected or available)
        provider = getattr(self.plc, "get_flowpath_names", None)
        if callable(provider):
            try:
                raw.extend([str(x) for x in (provider() or [])])
            except Exception:
                pass

        # 2) From the current project store (works in offline mode)
        raw.extend(flow_path.name for flow_path in self.store.get_flow_paths())

        # 3) From current model references (so offline users see their typed names)
        try:
            i = self.pv.inputs or {}
            for key in ("flow_path", "heating_flow_path", "cooling_flow_path"):
                v = i.get(key)
                if v:
                    raw.append(str(v))
            for coll_key in ("inlet_paths", "outlet_paths"):
                for item in (i.get(coll_key) or []):
                    name = (item or {}).get("name")
                    if name:
                        raw.append(str(name))
        except Exception:
            pass

        # Dedupe & sort (explicit lambda to satisfy type checker)
        items: list[str] = sorted({s for s in raw if s}, key=lambda s: s.lower())

        if items:
            combo.addItems(items)
        else:
            combo.setPlaceholderText("Type a flow path name")

    def _bold_label(self, text: str) -> QLabel:
        return QLabel(f"<b>{text}</b>")

    def _row2(self, a: QWidget | None, b: QWidget | None) -> QWidget:
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0)
        if a is not None:
            h.addWidget(a)
        h.addWidget(QLabel(" to "))
        if b is not None:
            h.addWidget(b)
        return w

    # ---------- Level row builder / collector ----------

    def _on_add_inlet_clicked(self, checked: bool = False) -> None:
        del checked
        row = self._add_flow_source_row(self.level_inlet_layout)
        self._reveal_level_row(row)

    def _on_add_outlet_clicked(self, checked: bool = False) -> None:
        del checked
        row = self._add_flow_source_row(self.level_outlet_layout)
        self._reveal_level_row(row)

    def _reveal_level_row(self, row: FlowSourceRow) -> None:
        row.show()
        row.updateGeometry()

        container = row.parentWidget()
        if container is not None:
            container.adjustSize()
            container.updateGeometry()

        self.scroll_w.adjustSize()
        self.scroll_w.updateGeometry()
        self.scroll.widget().adjustSize()
        self.scroll.widget().updateGeometry()

        def reveal() -> None:
            self.scroll.verticalScrollBar().setValue(
                self.scroll.verticalScrollBar().maximum()
            )
            self.scroll.ensureWidgetVisible(row, 16, 16)
            row.path_combo.setFocus()

        QTimer.singleShot(0, reveal)

    def _add_flow_source_row(self, host_layout: QVBoxLayout, prefill: Optional[Dict] = None):
        if not isinstance(host_layout, QVBoxLayout):
            raise TypeError("host_layout must be a QVBoxLayout")
        if prefill is not None and not isinstance(prefill, dict):
            prefill = None
        parent_widget = host_layout.parentWidget()
        if parent_widget is None:
            raise RuntimeError("Flow-source layout has no owning widget.")

        roww = FlowSourceRow(parent_widget)
        roww.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        roww.setMinimumHeight(0)

        # populate widgets
        self._populate_flowpath_combo(roww.path_combo)
        roww.mode_combo.addItems(["tag", "static"])
        roww.tag_edit.setPlaceholderText("PLC tag for flow rate")
        roww.val_edit.setPlaceholderText("flow value")
        roww.val_unit.addItems(["gpm", "lpm", "m3/s"])

        # Use a stacked editor so tag and static controls never overlap.
        source_stack = QStackedWidget(roww)
        source_stack.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        tag_page = QWidget(source_stack)
        tag_layout = QHBoxLayout(tag_page)
        tag_layout.setContentsMargins(0, 0, 0, 0)
        tag_layout.setSpacing(0)
        tag_layout.addWidget(roww.tag_edit)

        static_page = QWidget(source_stack)
        static_layout = QHBoxLayout(static_page)
        static_layout.setContentsMargins(0, 0, 0, 0)
        static_layout.setSpacing(6)
        static_layout.addWidget(roww.val_edit, 1)
        static_layout.addWidget(roww.val_unit, 0)

        source_stack.addWidget(tag_page)
        source_stack.addWidget(static_page)
        roww.source_stack = source_stack

        def _toggle(m: str) -> None:
            source_stack.setCurrentIndex(0 if m == "tag" else 1)

        roww.mode_combo.currentTextChanged.connect(_toggle)

        # prefill
        if prefill:
            roww.path_combo.setCurrentText(prefill.get("name", ""))
            src = prefill.get("source", {})
            roww.mode_combo.setCurrentText(src.get("mode", "tag"))
            roww.tag_edit.setText(src.get("tag", ""))
            roww.val_edit.setText("" if src.get("value") is None else str(src.get("value")))
            roww.val_unit.setCurrentText(src.get("unit", "gpm"))

        _toggle(roww.mode_combo.currentText())

        # remove button
        rm = QToolButton(); rm.setText("–"); rm.setAutoRaise(True)

        def remove_row(checked: bool = False) -> None:
            del checked
            host_layout.removeWidget(roww)
            roww.deleteLater()

            parent = host_layout.parentWidget()
            if parent is not None:
                parent.adjustSize()
                parent.updateGeometry()

            host_layout.invalidate()
            host_layout.activate()
            self.scroll_w.adjustSize()
            self.scroll_w.updateGeometry()

        rm.clicked.connect(remove_row)

        # Assemble one stable row. The stack owns the active source editor.
        lay = roww.layout()
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(8)

        roww.path_combo.setMinimumWidth(180)
        roww.mode_combo.setMinimumWidth(105)
        roww.val_unit.setMinimumWidth(90)
        rm.setMinimumWidth(34)

        lay.addWidget(roww.path_combo, 3)
        lay.addWidget(roww.mode_combo, 1)
        lay.addWidget(source_stack, 5)
        lay.addWidget(rm, 0)

        host_layout.addWidget(roww)
        roww.show()

        parent_widget.adjustSize()
        parent_widget.updateGeometry()
        host_layout.invalidate()
        host_layout.activate()

        self.scroll_w.adjustSize()
        self.scroll_w.updateGeometry()
        self.scroll.widget().adjustSize()
        self.scroll.widget().updateGeometry()
        return roww

    def _collect(self, layout: QVBoxLayout):
        names: List[Dict[str, str]] = []
        srcs: List[Dict[str, object]] = []
        for i in range(layout.count()):
            roww = layout.itemAt(i).widget()
            if not isinstance(roww, FlowSourceRow):
                continue
            name = roww.path_combo.currentText().strip()
            if not name:
                continue
            mode = roww.mode_combo.currentText()
            tag  = roww.tag_edit.text().strip()
            val  = _to_float(roww.val_edit.text())
            unit = roww.val_unit.currentText()
            if mode == "tag":
                src = {"mode": "tag", "tag": tag, "value": None, "unit": unit}
            else:
                src = {"mode": "static", "tag": "", "value": val, "unit": unit}
            names.append({"name": name})
            srcs.append(src)
        return names, srcs

    # ---------- Loading & Saving ----------

    def _load_from_model(self):
        # Basic
        self.name_edit.setText(self.pv.name or "")
        self.tag_edit.setText(self.pv.tag or "")
        self.active_chk.setChecked(bool(self.pv.active))
        self.type_combo.setCurrentText(self.pv.type or "None")
        self._apply_type_visibility(self.pv.type or "None")

        # FLOW
        if self.pv.type == "Flow":
            i = self.pv.inputs or {}
            p = self.pv.params or {}
            self.flow_control.setCurrentText(i.get("control", ""))
            self.flow_path.setCurrentText(i.get("flow_path", ""))
            self.flow_relationship.setCurrentText((p.get("cv_relationship") or "direct"))
            self.flow_cv_min.setText(_num_to_str(p.get("cv_min", 0.0)))
            self.flow_cv_max.setText(_num_to_str(p.get("cv_max", 100.0)))
            self.flow_pv_min.setText(_num_to_str(p.get("pv_min", 0.0)))
            self.flow_pv_max.setText(_num_to_str(p.get("pv_max", 1000.0)))
            self.flow_k.setText(_num_to_str(p.get("k", 1.0)))
            self.flow_tau.setText(_num_to_str(p.get("tau", 1.0)))
            self.flow_initial.setText(_num_to_str(p.get("initial", 0.0)))

        # PRESSURE
        if self.pv.type == "Pressure":
            i = self.pv.inputs or {}
            p = self.pv.params or {}
            self.press_control.setCurrentText(i.get("control", ""))
            self.press_path.setCurrentText(i.get("flow_path", ""))
            self.press_relationship.setCurrentText((p.get("cv_relationship") or "direct"))
            self.press_cv_min.setText(_num_to_str(p.get("cv_min", 0.0)))
            self.press_cv_max.setText(_num_to_str(p.get("cv_max", 100.0)))
            self.press_p_min.setText(_num_to_str(p.get("p_min", 0.0)))
            self.press_p_max.setText(_num_to_str(p.get("p_max", 200.0)))
            self.press_tau.setText(_num_to_str(p.get("tau", 2.0)))
            self.press_k.setText(_num_to_str(p.get("k", 1.0)))
            self.press_initial.setText(_num_to_str(p.get("initial", 0.0)))

        # LEVEL
        if self.pv.type == "Level":
            p = self.pv.params or {}
            i = self.pv.inputs or {}

            # geometry
            mode = p.get("geom_mode", "Volume only")
            self.level_geom_mode.setCurrentText(mode)
            self.level_volume.setText(_num_to_str(p.get("volume", "")))
            self.level_vol_unit.setCurrentText(p.get("volume_unit", "gal"))
            self.level_area.setText(_num_to_str(p.get("area", "")))
            self.level_area_unit.setCurrentText(p.get("area_unit", "m2"))
            self.level_height.setText(_num_to_str(p.get("height", "")))
            self.level_height_unit.setCurrentText(p.get("height_unit", "m"))
            self.level_geom_mode.currentTextChanged.emit(self.level_geom_mode.currentText())

            # transmitter / dynamics
            self.level_unit.setCurrentText(p.get("level_unit", "percent"))
            self.level_initial.setText(_num_to_str(p.get("initial", "")))
            self.level_gain.setText(_num_to_str(p.get("gain", 1.0)))

            # rows
            def _reset_layout(lay: QVBoxLayout) -> None:
                """Synchronously detach old rows before inserting loaded rows."""
                while lay.count():
                    item = lay.takeAt(0)
                    widget = item.widget()
                    child_layout = item.layout()

                    if widget is not None:
                        widget.hide()
                        widget.setParent(None)
                        widget.deleteLater()
                    elif child_layout is not None:
                        while child_layout.count():
                            child_item = child_layout.takeAt(0)
                            child_widget = child_item.widget()
                            if child_widget is not None:
                                child_widget.hide()
                                child_widget.setParent(None)
                                child_widget.deleteLater()

                lay.invalidate()
                lay.activate()

            _reset_layout(self.level_inlet_layout)
            _reset_layout(self.level_outlet_layout)

            in_paths = i.get("inlet_paths", [])
            in_srcs  = p.get("inlet_sources", [])
            out_paths = i.get("outlet_paths", [])
            out_srcs  = p.get("outlet_sources", [])

            if in_paths:
                for idx in range(len(in_paths)):
                    pre = {
                        "name": (in_paths[idx] or {}).get("name", ""),
                        "source": (in_srcs[idx] if idx < len(in_srcs) else {}),
                    }
                    self._add_flow_source_row(self.level_inlet_layout, prefill=pre)
            else:
                self._add_flow_source_row(self.level_inlet_layout)

            if out_paths:
                for idx in range(len(out_paths)):
                    pre = {
                        "name": (out_paths[idx] or {}).get("name", ""),
                        "source": (out_srcs[idx] if idx < len(out_srcs) else {}),
                    }
                    self._add_flow_source_row(self.level_outlet_layout, prefill=pre)
            else:
                self._add_flow_source_row(self.level_outlet_layout)

        # TEMPERATURE
        if self.pv.type == "Temperature":
            i = self.pv.inputs or {}
            p = self.pv.params or {}
            heating_cv = i.get("heating_cv") or i.get("control", "")
            self.temp_heating_cv.setCurrentText(str(heating_cv or ""))
            self.temp_cooling_cv.setCurrentText(str(i.get("cooling_cv", "") or ""))
            self.temp_heating_path.setCurrentText(str(i.get("heating_flow_path", "") or ""))
            self.temp_cooling_path.setCurrentText(str(i.get("cooling_flow_path", "") or ""))
            self.temp_heating_cv_min.setText(_num_to_str(p.get("heating_cv_min", p.get("cv_min", 0.0))))
            self.temp_heating_cv_max.setText(_num_to_str(p.get("heating_cv_max", p.get("cv_max", 100.0))))
            self.temp_cooling_cv_min.setText(_num_to_str(p.get("cooling_cv_min", 0.0)))
            self.temp_cooling_cv_max.setText(_num_to_str(p.get("cooling_cv_max", 100.0)))
            self.temp_heating_gain.setText(_num_to_str(p.get("heating_gain", p.get("k", 0.0))))
            self.temp_cooling_gain.setText(_num_to_str(p.get("cooling_gain", 0.0)))
            self.temp_ambient.setText(_num_to_str(p.get("ambient", 25.0)))
            self.temp_pv_min.setText(_num_to_str(p.get("pv_min", -273.15)))
            self.temp_pv_max.setText(_num_to_str(p.get("pv_max", 1000.0)))
            self.temp_tau.setText(_num_to_str(p.get("tau", 5.0)))
            self.temp_initial.setText(_num_to_str(p.get("initial", p.get("ambient", 25.0))))

    def _apply_type_visibility(self, mtype: str):
        sections = {
            "None": self.section_none,
            "Flow": self.section_flow,
            "Pressure": self.section_pressure,
            "Level": self.section_level,
            "Temperature": self.section_temperature,
            "Sensor": self.section_sensor,
        }
        for key, widget in sections.items():
            widget.setVisible(key == mtype)

    def _on_type_changed(self, mtype: str):
        self._apply_type_visibility(mtype)

    def _on_save(self):
        # Validate core
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Name", "Please provide a model name.")
            return

        self.pv.name = name
        self.pv.tag = self.tag_edit.text().strip()
        self.pv.active = self.active_chk.isChecked()
        self.pv.type = self.type_combo.currentText()

        t = self.pv.type
        if t == "Flow":
            self._save_flow()
        elif t == "Pressure":
            self._save_pressure()
        elif t == "Level":
            self._save_level()
        elif t == "Temperature":
            self._save_temperature()
        elif t == "Sensor":
            self._save_sensor()

        self.accept()

    # --- Save helpers per type ---

    def _save_flow(self):
        i = self.pv.inputs or {}
        p = self.pv.params or {}
        i["control"]   = self.flow_control.currentText().strip()
        i["flow_path"] = self.flow_path.currentText().strip()
        p["cv_relationship"] = self.flow_relationship.currentText() or "direct"
        p["cv_min"]    = _to_float(self.flow_cv_min.text()) if self.flow_cv_min.text() else 0.0
        p["cv_max"]    = _to_float(self.flow_cv_max.text()) if self.flow_cv_max.text() else 100.0
        p["pv_min"]    = _to_float(self.flow_pv_min.text()) if self.flow_pv_min.text() else 0.0
        p["pv_max"]    = _to_float(self.flow_pv_max.text()) if self.flow_pv_max.text() else 1000.0
        p["k"]         = _to_float(self.flow_k.text()) if self.flow_k.text() else 1.0
        p["tau"]       = _to_float(self.flow_tau.text()) if self.flow_tau.text() else 1.0
        p["initial"]   = _to_float(self.flow_initial.text()) if self.flow_initial.text() else 0.0
        self.pv.inputs = i
        self.pv.params = p

    def _save_pressure(self):
        i = self.pv.inputs or {}
        p = self.pv.params or {}
        i["control"]   = self.press_control.currentText().strip()
        i["flow_path"] = self.press_path.currentText().strip()
        p["cv_relationship"] = self.press_relationship.currentText() or "direct"
        p["cv_min"]    = _to_float(self.press_cv_min.text()) if self.press_cv_min.text() else 0.0
        p["cv_max"]    = _to_float(self.press_cv_max.text()) if self.press_cv_max.text() else 100.0
        p["p_min"]     = _to_float(self.press_p_min.text()) if self.press_p_min.text() else 0.0
        p["p_max"]     = _to_float(self.press_p_max.text()) if self.press_p_max.text() else 200.0
        p["tau"]       = _to_float(self.press_tau.text()) if self.press_tau.text() else 2.0
        p["k"]         = _to_float(self.press_k.text()) if self.press_k.text() else 1.0
        p["initial"]   = _to_float(self.press_initial.text()) if self.press_initial.text() else 0.0
        self.pv.inputs = i
        self.pv.params = p

    def _save_level(self):
        i = self.pv.inputs or {}
        p = self.pv.params or {}

        # geometry
        p["geom_mode"]   = self.level_geom_mode.currentText()
        p["volume"]      = _to_float(self.level_volume.text())
        p["volume_unit"] = self.level_vol_unit.currentText()
        p["area"]        = _to_float(self.level_area.text())
        p["area_unit"]   = self.level_area_unit.currentText()
        p["height"]      = _to_float(self.level_height.text())
        p["height_unit"] = self.level_height_unit.currentText()

        # transmitter / dynamics
        p["level_unit"]  = self.level_unit.currentText()          # "percent" | "m" | "ft" | "in"
        p["initial"]     = _to_float(self.level_initial.text())
        p["gain"]        = _to_float(self.level_gain.text()) if self.level_gain.text() else 1.0

        # flow rows
        i["inlet_paths"], p["inlet_sources"]   = self._collect(self.level_inlet_layout)
        i["outlet_paths"], p["outlet_sources"] = self._collect(self.level_outlet_layout)

        self.pv.inputs = i
        self.pv.params = p

    def _save_temperature(self):
        i = self.pv.inputs or {}
        p = self.pv.params or {}
        i.pop("control", None)
        i["heating_cv"] = self.temp_heating_cv.currentText().strip()
        i["cooling_cv"] = self.temp_cooling_cv.currentText().strip()
        i["heating_flow_path"] = self.temp_heating_path.currentText().strip()
        i["cooling_flow_path"] = self.temp_cooling_path.currentText().strip()
        p["heating_cv_min"] = _field_float(self.temp_heating_cv_min, 0.0)
        p["heating_cv_max"] = _field_float(self.temp_heating_cv_max, 100.0)
        p["cooling_cv_min"] = _field_float(self.temp_cooling_cv_min, 0.0)
        p["cooling_cv_max"] = _field_float(self.temp_cooling_cv_max, 100.0)
        p["heating_gain"] = _field_float(self.temp_heating_gain, 0.0)
        p["cooling_gain"] = _field_float(self.temp_cooling_gain, 0.0)
        p["ambient"] = _field_float(self.temp_ambient, 25.0)
        p["pv_min"] = _field_float(self.temp_pv_min, -273.15)
        p["pv_max"] = _field_float(self.temp_pv_max, 1000.0)
        p["tau"] = _field_float(self.temp_tau, 5.0)
        p["initial"] = _field_float(self.temp_initial, p["ambient"])
        self.pv.inputs = i
        self.pv.params = p

    def _save_sensor(self):
        p = self.pv.params or {}
        p["initial"] = _to_float(self.sensor_initial.text())
        self.pv.params = p


# ---- tiny parse helpers ----

def _field_float(field: QLineEdit, default: float) -> float:
    value = _to_float(field.text())
    return default if value is None else float(value)

def _to_float(s: str | None):
    try:
        return float(str(s).strip())
    except Exception:
        return None

def _num_to_str(v):
    if v is None:
        return ""
    return str(v)
