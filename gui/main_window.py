# gui/main_window.py
import json
from json import JSONDecodeError
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel, QHBoxLayout,
    QScrollArea, QCheckBox, QPushButton, QFrame, QMessageBox, QFileDialog
)

from core.model_loader import ModelLoader
from core.models import ConfiguredModel
from core.constants import COLUMN_HEADINGS, COLUMN_WIDTHS
from core.sim_component_factory import build_sim_component
from core.simulator import SimComponent, PressureComponent, LevelComponent
from core.plc_sim_bridge import PlcSimBridge
from gui.dlg_flowpath_cfg import FlowPathConfigWizard
from gui.dlg_model_cfg import ModelConfigWizard

from core.csv_io import (
    export_models_csv, import_models_csv,
    export_flowpaths_csv, import_flowpaths_csv
)

class MainWindow(QMainWindow):
    def __init__(self, plc=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("pySIMIO")
        self._plc = plc

        # data
        self.models: list[ConfiguredModel] = ModelLoader.load()
        self.components: dict[str, SimComponent] = {}
        self.active_only: dict[str, SimComponent] = {}
        self.value_labels: dict[str, QLabel] = {}
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self._tick)

        # plc bridge
        self.bridge = PlcSimBridge(write_fn=(self._plc.write_tag if self._plc else lambda t,v: True))

        # UI
        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)
        self._build_process_tab()
        self._build_flowpaths_tab()
        self._build_menu()

        self._refresh_pv_tab()
        self._rebuild()

    # -------- UI build --------

    def _build_menu(self):
        bar = self.menuBar()

        # File Menu
        file_menu = bar.addMenu("&File")
        act_export_models = file_menu.addAction("Export &Models (CSV)")
        act_export_models.triggered.connect(self.on_export_models_csv)
        act_import_models = file_menu.addAction("Import &Models (CSV)")
        act_import_models.triggered.connect(self.on_import_models_csv)
        file_menu.addSeparator()
        act_export_flow = file_menu.addAction("Export &Flow Paths (CSV)")
        act_export_flow.triggered.connect(self.on_export_flowpaths_csv)
        act_import_flow = file_menu.addAction("Import F&low Paths (CSV)")
        act_import_flow.triggered.connect(self.on_import_flowpaths_csv)

        # Simulation Menu
        sim_menu = bar.addMenu("&Simulation")
        act_start = QAction("Start", self); act_start.triggered.connect(self.on_start)
        act_stop = QAction("Stop", self); act_stop.triggered.connect(self.on_stop)
        sim_menu.addAction(act_start); sim_menu.addAction(act_stop)

        # Configuration Menu
        cfg_menu = bar.addMenu("&Configure")
        act_cfg_pv = QAction("Add/Edit Model...", self); act_cfg_pv.triggered.connect(self.on_configure_model)
        act_cfg_fp = QAction("Flow Paths...", self); act_cfg_fp.triggered.connect(self.on_configure_flow_paths)
        cfg_menu.addAction(act_cfg_pv); cfg_menu.addAction(act_cfg_fp)

    def _build_process_tab(self):
        tab = QWidget(); self.tabs.addTab(tab, "Process Variables")
        v = QVBoxLayout(tab)

        header = QHBoxLayout()
        for h, w in zip(COLUMN_HEADINGS, COLUMN_WIDTHS):
            lbl = QLabel(f"<b>{h}</b>"); lbl.setMinimumWidth(w)
            header.addWidget(lbl)
        header.addStretch()
        v.addLayout(header)

        area = QScrollArea(); area.setWidgetResizable(True)
        cont = QWidget(); area.setWidget(cont)
        self.process_layout = QVBoxLayout(cont)
        v.addWidget(area)

        controls = QHBoxLayout()
        self.cb_active_only = QCheckBox("Write Active Only"); self.cb_active_only.setChecked(True)
        btn_start = QPushButton("Start"); btn_start.clicked.connect(self.on_start)
        btn_stop  = QPushButton("Stop");  btn_stop.clicked.connect(self.on_stop)
        btn_scan  = QPushButton("Read from PLC"); btn_scan.clicked.connect(self.on_read_from_plc)
        for w in (self.cb_active_only, btn_start, btn_stop, btn_scan):
            controls.addWidget(w)
        controls.addStretch()
        v.addLayout(controls)

    def _build_flowpaths_tab(self):
        """Create the Flow Paths tab once; repopulate its inner layout."""
        tab = QWidget()
        outer = QVBoxLayout(tab)

        # Header row
        header = QHBoxLayout()
        for title, width in (("Name", 200), ("Description", 300), ("Segments", 400)):
            lbl = QLabel(f"<b>{title}</b>")
            lbl.setMinimumWidth(width)
            header.addWidget(lbl)
        header.addStretch(1)
        outer.addLayout(header)

        # Scroll area with a container that can be rebuilt
        area = QScrollArea()
        area.setWidgetResizable(True)
        cont = QWidget()
        area.setWidget(cont)
        self.flowpaths_layout = QVBoxLayout(cont)  # store for rebuilds
        self.flowpaths_layout.setSpacing(6)
        outer.addWidget(area)

        # Bottom controls (optional: add "New Flow Path" button)
        controls = QHBoxLayout()
        btn_new = QPushButton("New Flow Path")
        btn_new.clicked.connect(self._on_flowpath_new)
        controls.addStretch(1)
        controls.addWidget(btn_new)
        outer.addLayout(controls)

        # Keep a ref to the tab and add to the QTabWidget
        self.tabs.addTab(tab, "Flow Paths")

        # initial populate
        self._refresh_flowpaths_tab()

    # -------- Actions --------

    def on_export_models_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Models to CSV", "models.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            models = self.get_configured_models()  # <- implement or use your existing accessor
            export_models_csv(models, path, include_example_when_empty=True)
            QMessageBox.information(self, "Export Models", f"Exported {len(models)} models to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Models Failed", str(e))

    def on_import_models_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Models from CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        try:
            imported = import_models_csv(path)
            # Merge strategy: replace all or merge by name? Here we MERGE by 'name'
            existing = {m.name: m for m in self.get_configured_models()}
            for m in imported:
                existing[m.name] = m
            merged = list(existing.values())
            self.set_configured_models(merged)  # <- persist + refresh UI as you already do
            QMessageBox.information(self, "Import Models", f"Imported {len(imported)} models from:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Import Models Failed", str(e))

    def on_export_flowpaths_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Flow Paths to CSV", "flowpaths.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            flowpaths = self.get_flowpaths()  # <- implement accessor for your list
            export_flowpaths_csv(flowpaths, path, include_example_when_empty=True)
            QMessageBox.information(self, "Export Flow Paths", f"Exported {len(flowpaths)} flow paths to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Flow Paths Failed", str(e))

    def on_import_flowpaths_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Flow Paths from CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        try:
            # If you have a FlowPath dataclass/ctor, pass it as flowpath_ctor=FlowPath
            imported = import_flowpaths_csv(path, flowpath_ctor=None)
            # Merge by 'name'
            existing = {fp.name: fp for fp in self.get_flowpaths()}
            for fp in imported:
                key = fp.get("name") if isinstance(fp, dict) else getattr(fp, "name", None)
                if key:
                    existing[key] = fp
            merged = list(existing.values())
            self.set_flowpaths(merged)  # <- persist + refresh UI
            QMessageBox.information(self, "Import Flow Paths", f"Imported {len(imported)} flow paths from:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Import Flow Paths Failed", str(e))

    def on_configure_model(self):
        # Very simple: open dialog for first PV (or you can build a selection)
        pv = self.models[0] if self.models else ConfiguredModel(name="NewPV", type="Sensor", tag="", active=False)
        dlg = ModelConfigWizard(self._plc, pv)
        if dlg.exec():
            # Expect dlg to save into pv_models.json
            self.models = ModelLoader.load()
            self._refresh_pv_tab()
            self._rebuild()

    def on_configure_flow_paths(self):
        dlg = FlowPathConfigWizard(self._plc)
        if dlg.exec():
            pass  # no-op; dialog persists to its own json

    def _on_flowpath_new(self):
        from gui.dlg_flowpath_cfg import FlowPathConfigWizard  # adjust import to your path
        dlg = FlowPathConfigWizard(self._plc, parent=self)
        if dlg.exec():
            # Wizard already saved to JSON; just refresh
            self._refresh_flowpaths_tab()

    def _on_flowpath_edit(self, fp: dict):
        """Open wizard prefilled. Your wizard supports presets (if not, you can load/edit and resave here)."""
        try:
            from gui.dlg_flowpath_cfg import FlowPathConfigWizard
        except Exception:
            # fallback to the path you’re using
            from dlg_flowpath_cfg import FlowPathConfigWizard

        dlg = FlowPathConfigWizard(
            self._plc,
            parent=self,
            preset_name=fp.get("name"),
            preset_description=fp.get("description", ""),
            preset_segments=fp.get("segments", []),
        )
        if dlg.exec():
            self._refresh_flowpaths_tab()

    def _on_flowpath_remove(self, name: str):
        if not name:
            return
        rows = [fp for fp in self.get_flowpaths() if fp.get("name") != name]
        self.set_flowpaths(rows)  # persists and refreshes
        QMessageBox.information(self, "Flow Path Removed", f"Removed flow path: {name}")

    def on_start(self):
        try:
            if not (self._plc and self._plc.is_connected()):
                QMessageBox.warning(self, "PLC Not Connected", "Please connect to a PLC first.")
                return
        except Exception:
            pass
        self._rebuild()
        self.timer.start()

    def on_stop(self):
        self.timer.stop()
        self.bridge.stop()

    def on_read_from_plc(self):
        # Placeholder
        QMessageBox.information(self, "Read from PLC", "Discovery not wired yet in this window. (Optional)")

    # -------- Sim orchestration --------

    def _rebuild(self):
        self.components.clear()
        self.active_only.clear()
        self.bridge.stop()

        # build components
        for cm in self.models:
            comp = build_sim_component(cm)
            self.components[cm.name] = comp
            if cm.active and cm.tag:
                self.bridge.register_source(cm.tag, comp.current_value)
                self.active_only[cm.name] = comp
        self.bridge.start()

        # dynamic wiring (pressure/level pulling from flows)
        self._pressure_links = {}
        self._level_links = {}
        for cm in self.models:
            if cm.type.lower() == "pressure":
                self._pressure_links[cm.name] = (cm.inputs.get("inlet_flow"), cm.inputs.get("outlet_flow"))
            elif cm.type.lower() == "level":
                self._level_links[cm.name] = (cm.inputs.get("inlet_flow"), cm.inputs.get("outlet_flow"))

    def _tick(self):
        dt = 0.2
        # Wire flows each tick and update
        for name, comp in self.components.items():
            if isinstance(comp, PressureComponent):
                inlet, outlet = self._pressure_links.get(name, (None, None))
                qin = self.components[inlet].current_value() if inlet in self.components else 0.0
                qout = self.components[outlet].current_value() if outlet in self.components else 0.0
                comp.set_flows(qin, qout)
            elif isinstance(comp, LevelComponent):
                inlet, outlet = self._level_links.get(name, (None, None))
                qin = self.components[inlet].current_value() if inlet in self.components else 0.0
                qout = self.components[outlet].current_value() if outlet in self.components else 0.0
                comp.set_flows(qin, qout)

        for comp in self.components.values():
            comp.update(dt)

        self.bridge.tick()
        self._refresh_values()

    # -------- UI helpers --------

    def get_configured_models(self) -> list[ConfiguredModel]:
        return list(self.models)

    def set_configured_models(self, models: list[ConfiguredModel]) -> None:
        # Persist and refresh
        self.models = list(models)
        ModelLoader.save(self.models)
        # Make sure your UI rebuilds the list and the components
        self._refresh_pv_tab()
        self._rebuild()

    def get_flowpaths(self) -> list[dict]:
        """
        Returns a list of dicts: {"name": str, "description": str, "segments": [str]}
        """
        try:
            with open("./assets/flowpaths.json", "r", encoding="utf-8") as f:
                data = json.load(f) or {}
        except (FileNotFoundError, JSONDecodeError):
            data = {}

        out = []
        for name, entry in data.items():
            out.append({
                "name": name,
                "description": entry.get("description", ""),
                "segments": list(entry.get("segments", [])),  # names only
            })
        return out

    def set_flowpaths(self, items: list[dict]) -> None:
        """
        Accepts a list of dicts in the same shape and writes flowpaths.json.
        """
        data = {}
        for fp in items:
            name = (fp.get("name") or "").strip()
            if not name:
                continue
            data[name] = {
                "description": fp.get("description", ""),
                "segments": list(fp.get("segments", [])),
            }

        Path("./assets").mkdir(parents=True, exist_ok=True)
        with open("./assets/flowpaths.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        self._refresh_pv_tab()

    def _refresh_pv_tab(self):
        # rebuild process list
        layout = self.process_layout
        # clear
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()

        self.value_labels.clear()
        for cm in self.models:
            row = QHBoxLayout()
            row.addWidget(QLabel(cm.name))
            row.addWidget(QLabel(cm.type))
            row.addWidget(QLabel(cm.tag))
            row.addWidget(QLabel("Yes" if cm.active else "No"))
            val_lbl = QLabel("—")
            self.value_labels[cm.name] = val_lbl
            row.addWidget(val_lbl)
            row.addStretch()
            line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setFrameShadow(QFrame.Shadow.Sunken)
            wrap = QVBoxLayout(); wrap.addLayout(row); wrap.addWidget(line)
            cont = QWidget(); cont.setLayout(wrap)
            self.process_layout.addWidget(cont)

        self.process_layout.addStretch()

    def _refresh_flowpaths_tab(self):
        """Rebuild the rows from JSON."""
        if not hasattr(self, "flowpaths_layout"):
            return  # tab not built yet

        # clear previous rows
        layout = self.flowpaths_layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # build rows
        rows = self.get_flowpaths()
        if not rows:
            empty = QLabel("No flow paths configured yet.")
            empty.setStyleSheet("color:#888;")
            layout.addWidget(empty)
            return

        for fp in rows:
            layout.addWidget(self._build_flowpath_row(fp))

    def _refresh_values(self):
        for name, lbl in self.value_labels.items():
            comp = self.components.get(name)
            if comp:
                try:
                    v = comp.current_value()
                    lbl.setText(f"{v:.3f}")
                except Exception:
                    lbl.setText("ERR")

    def _build_flowpath_row(self, fp: dict) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        # Name as a button to open editor
        btn_name = QPushButton(fp.get("name", ""))
        btn_name.setFlat(True)
        btn_name.setStyleSheet("text-align:left;")
        btn_name.clicked.connect(lambda: self._on_flowpath_edit(fp))
        btn_name.setMinimumWidth(200)

        # Description
        desc = QLabel(fp.get("description", ""))
        desc.setWordWrap(True)
        desc.setMinimumWidth(300)

        # Segments: join names
        segs = fp.get("segments", [])
        seg_label = QLabel(", ".join(segs))
        seg_label.setWordWrap(True)
        seg_label.setMinimumWidth(400)

        # Remove button
        btn_remove = QPushButton("Remove")
        btn_remove.clicked.connect(lambda: self._on_flowpath_remove(fp.get("name", "")))

        row_layout.addWidget(btn_name, 0)
        row_layout.addWidget(desc,    1)
        row_layout.addWidget(seg_label, 2)
        row_layout.addStretch(1)
        row_layout.addWidget(btn_remove, 0)

        # separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)

        wrapper = QWidget()
        v = QVBoxLayout(wrapper)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        v.addWidget(row)
        v.addWidget(sep)

        return wrapper