"""Main pySIMIO window and project-document lifecycle."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from core.csv_io import export_flowpaths_csv, export_models_csv, import_flowpaths_csv, import_models_csv
from core.simulation_manager import RuntimeState, SimulationManager
from domain.models import ConfiguredModel, FlowPath
from gui.dlg_model_cfg import ModelConfigWizard
from persistence.project_store import PROJECT_EXTENSION, ProjectStore

PROJECT_FILTER = f"pySIMIO Project (*{PROJECT_EXTENSION})"
MAX_RECENT_PROJECTS = 8


class MainWindow(QMainWindow):
    def __init__(self, store: ProjectStore, plc=None, parent=None):
        super().__init__(parent)
        self.store = store
        self.models = self.store.get_models()
        self._settings = QSettings()
        self._last_values: dict[str, float] = {}

        self.runtime = SimulationManager(store, plc, parent=self)
        self.runtime.values_changed.connect(self._refresh_values)
        self.runtime.state_changed.connect(self._on_runtime_state_changed)
        self.runtime.faulted.connect(self._on_runtime_fault)

        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)
        self._build_process_tab()
        self._build_flowpaths_tab()
        self._build_menu()
        self._build_project_toolbar()
        self._build_status_bar()
        self._refresh_all()
        self._on_runtime_state_changed(self.runtime.state)

    @property
    def _plc(self):
        return self.runtime.plc

    # Project lifecycle -------------------------------------------------
    def on_new_project(self) -> None:
        if not self._confirm_discard_changes():
            return
        self.runtime.stop()
        self.store.new()
        self._project_changed()

    def on_open_project(self) -> None:
        if not self._confirm_discard_changes():
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open pySIMIO Project",
            self._last_project_directory(),
            PROJECT_FILTER,
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if path:
            self._open_project_path(path)

    def on_save_project(self) -> bool:
        if not self.store.has_path:
            return self.on_save_project_as()
        try:
            saved = self.store.save()
        except Exception as exc:
            QMessageBox.critical(self, "Save Project Failed", str(exc))
            return False
        self._remember_project(saved)
        self._update_window_title()
        self.statusBar().showMessage(f"Saved {saved.name}", 3000)
        return True

    def on_save_project_as(self) -> bool:
        initial = str(self.store.path) if self.store.path else str(Path(self._last_project_directory()) / "Untitled.pysimio")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save pySIMIO Project",
            initial,
            PROJECT_FILTER,
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if not path:
            return False
        try:
            saved = self.store.save_as(path)
        except Exception as exc:
            QMessageBox.critical(self, "Save Project Failed", str(exc))
            return False
        self._remember_project(saved)
        self._update_window_title()
        self.statusBar().showMessage(f"Saved {saved.name}", 3000)
        return True

    def _open_project_path(self, path: str | Path) -> bool:
        try:
            self.runtime.stop()
            self.store.open(path)
        except Exception as exc:
            QMessageBox.critical(self, "Open Project Failed", f"Unable to open:\n{path}\n\n{exc}")
            return False
        self._remember_project(self.store.path)
        self._project_changed()
        return True

    def _project_changed(self) -> None:
        self.models = self.store.get_models()
        self.runtime.build()
        self._refresh_all()

    def _confirm_discard_changes(self) -> bool:
        if not self.store.is_dirty:
            return True
        result = QMessageBox.warning(
            self,
            "Unsaved Changes",
            "The current project has unsaved changes.",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if result is QMessageBox.StandardButton.Cancel:
            return False
        if result is QMessageBox.StandardButton.Save:
            return self.on_save_project()
        return True

    # Menus/status ------------------------------------------------------
    def _build_menu(self) -> None:
        menu_bar = self.menuBar()
        menu_bar.setNativeMenuBar(False)
        file_menu = menu_bar.addMenu("&File")
        self.act_new = QAction("&New Project", self)
        self.act_new.setShortcut(QKeySequence.StandardKey.New)
        self.act_new.triggered.connect(lambda checked=False: self.on_new_project())
        self.act_open = QAction("&Open Project...", self)
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(lambda checked=False: self.on_open_project())
        self.act_save = QAction("&Save Project", self)
        self.act_save.setShortcut(QKeySequence.StandardKey.Save)
        self.act_save.triggered.connect(lambda checked=False: self.on_save_project())
        self.act_save_as = QAction("Save Project &As...", self)
        self.act_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.act_save_as.triggered.connect(lambda checked=False: self.on_save_project_as())
        self.recent_menu = QMenu("Open &Recent", self)
        self.recent_menu.aboutToShow.connect(self._rebuild_recent_menu)
        self.act_exit = QAction("E&xit", self)
        self.act_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self.act_exit.triggered.connect(lambda checked=False: self.close())
        file_menu.addActions([self.act_new, self.act_open, self.act_save, self.act_save_as])
        file_menu.addMenu(self.recent_menu)
        file_menu.addSeparator()
        import_menu = file_menu.addMenu("&Import")
        import_menu.addAction("Models from CSV...", self.on_import_models_csv)
        import_menu.addAction("Flow Paths from CSV...", self.on_import_flowpaths_csv)
        export_menu = file_menu.addMenu("&Export")
        export_menu.addAction("Models to CSV...", self.on_export_models_csv)
        export_menu.addAction("Flow Paths to CSV...", self.on_export_flowpaths_csv)
        file_menu.addSeparator()
        file_menu.addAction(self.act_exit)

        sim_menu = menu_bar.addMenu("&Simulation")
        self.act_start = QAction("Start", self)
        self.act_start.triggered.connect(self.on_start)
        self.act_stop = QAction("Stop", self)
        self.act_stop.triggered.connect(self.on_stop)
        self.act_reset = QAction("Reset", self)
        self.act_reset.triggered.connect(self.on_reset)
        self.act_validate = QAction("Validate", self)
        self.act_validate.triggered.connect(self.on_validate)
        sim_menu.addActions([self.act_start, self.act_stop, self.act_reset, self.act_validate])

        cfg_menu = menu_bar.addMenu("&Configure")
        cfg_menu.addAction("Add Model...", self.on_add_model)
        cfg_menu.addAction("Edit Selected Model...", self.on_configure_model)
        cfg_menu.addAction("Flow Paths...", self.on_configure_flow_paths)

    def _build_project_toolbar(self) -> None:
        toolbar = QToolBar("Project", self)
        toolbar.setObjectName("project_toolbar")
        toolbar.setMovable(False)
        toolbar.addAction(self.act_new)
        toolbar.addAction(self.act_open)
        toolbar.addAction(self.act_save)
        toolbar.addAction(self.act_save_as)
        self.addToolBar(toolbar)

    def _build_status_bar(self) -> None:
        self.project_status = QLabel()
        self.plc_status = QLabel()
        self.runtime_status = QLabel()
        self.statusBar().addWidget(self.project_status, 1)
        self.statusBar().addPermanentWidget(self.plc_status)
        self.statusBar().addPermanentWidget(self.runtime_status)
        self._refresh_connection_status()

    # Process variables ------------------------------------------------
    def _build_process_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        toolbar = QToolBar("Process Variable Actions", tab)
        toolbar.setMovable(False)
        toolbar.addAction("Add", self.on_add_model)
        toolbar.addAction("Edit", self.on_configure_model)
        toolbar.addAction("Remove", self.on_remove_model)
        toolbar.addSeparator()
        toolbar.addAction("Start", self.on_start)
        toolbar.addAction("Stop", self.on_stop)
        toolbar.addAction("Reset", self.on_reset)
        toolbar.addAction("Validate", self.on_validate)
        toolbar.addSeparator()
        self.scan_action = toolbar.addAction("Read from PLC", self.on_read_from_plc)
        layout.addWidget(toolbar)

        self.process_table = QTableWidget(0, 7, tab)
        self.process_table.setHorizontalHeaderLabels(["Name", "PLC Tag", "Model Type", "Active", "Current Value", "Source", "Status"])
        self._configure_table(self.process_table)
        self.process_table.doubleClicked.connect(self.on_configure_model)
        header = self.process_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.process_table)
        self.tabs.addTab(tab, "Process Variables")

    def _refresh_pv_table(self) -> None:
        selected = self._selected_model_name()
        self.process_table.setSortingEnabled(False)
        self.process_table.setRowCount(0)
        for model in self.models:
            row = self.process_table.rowCount()
            self.process_table.insertRow(row)
            values = [
                model.name,
                model.tag or "—",
                model.type,
                "Yes" if model.active else "No",
                self._format_value(self._last_values.get(model.name)),
                model.source or "manual",
                self._model_status(model),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in {3, 4, 6}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.process_table.setItem(row, column, item)
        self.process_table.setSortingEnabled(True)
        self._restore_row_selection(self.process_table, selected)

    def on_remove_model(self) -> None:
        model = self._get_selected_model(show_message=True)
        if model is None:
            return
        if QMessageBox.question(self, "Remove Process Variable", f"Remove '{model.name}' from this project?") is QMessageBox.StandardButton.Yes:
            if self.store.remove_model(model.name):
                self._reload_models()

    # Flow paths --------------------------------------------------------
    def _build_flowpaths_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        toolbar = QToolBar("Flow Path Actions", tab)
        toolbar.setMovable(False)
        toolbar.addAction("New", self._on_flowpath_new)
        toolbar.addAction("Edit", self._on_selected_flowpath_edit)
        toolbar.addAction("Remove", self._on_selected_flowpath_remove)
        layout.addWidget(toolbar)
        self.flowpaths_table = QTableWidget(0, 4, tab)
        self.flowpaths_table.setHorizontalHeaderLabels(["Name", "Description", "Segments", "Segment Count"])
        self._configure_table(self.flowpaths_table)
        self.flowpaths_table.doubleClicked.connect(self._on_selected_flowpath_edit)
        header = self.flowpaths_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.flowpaths_table)
        self.flowpaths_tab = tab
        self.tabs.addTab(tab, "Flow Paths")

    def _refresh_flowpaths_table(self) -> None:
        selected = self._selected_flowpath_name()
        self.flowpaths_table.setSortingEnabled(False)
        self.flowpaths_table.setRowCount(0)
        for flowpath in self.get_flowpaths():
            row = self.flowpaths_table.rowCount()
            self.flowpaths_table.insertRow(row)
            values = [flowpath.name, flowpath.description or "—", ", ".join(flowpath.segments) or "—", str(len(flowpath.segments))]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 2:
                    item.setToolTip("\n".join(flowpath.segments))
                if column == 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.flowpaths_table.setItem(row, column, item)
        self.flowpaths_table.setSortingEnabled(True)
        self._restore_row_selection(self.flowpaths_table, selected)

    def _on_selected_flowpath_edit(self) -> None:
        flowpath = self._get_selected_flowpath()
        if flowpath is not None:
            self._on_flowpath_edit(flowpath)
        else:
            QMessageBox.information(self, "Select a Flow Path", "Select a flow path first.")

    def _on_selected_flowpath_remove(self) -> None:
        flowpath = self._get_selected_flowpath()
        if flowpath is None:
            QMessageBox.information(self, "Select a Flow Path", "Select a flow path first.")
            return
        if QMessageBox.question(self, "Remove Flow Path", f"Remove '{flowpath.name}' from this project?") is QMessageBox.StandardButton.Yes:
            self._on_flowpath_remove(flowpath.name)

    # Model/flow-path operations ---------------------------------------
    def on_add_model(self) -> None:
        self._open_model_dialog(None)

    def on_configure_model(self) -> None:
        model = self._get_selected_model(show_message=True)
        if model is not None:
            self._open_model_dialog(model)

    def _open_model_dialog(self, model: ConfiguredModel | None) -> None:
        dialog = ModelConfigWizard(self._plc, model, self, store=self.store)
        if dialog.exec():
            self.store.upsert_model(dialog.pv)
            self._reload_models()

    def _get_selected_model(self, *, show_message: bool = False) -> ConfiguredModel | None:
        name = self._selected_model_name()
        model = next((item for item in self.models if name and item.name.casefold() == name.casefold()), None)
        if model is None and show_message:
            QMessageBox.information(self, "Select a Model", "Select a process-variable row first.")
        return model

    def on_configure_flow_paths(self) -> None:
        self._refresh_flowpaths_table()
        self.tabs.setCurrentWidget(self.flowpaths_tab)

    def _on_flowpath_new(self) -> None:
        from gui.dlg_flowpath_cfg import FlowPathConfigWizard
        dialog = FlowPathConfigWizard(self._plc, parent=self, store=self.store)
        if dialog.exec():
            self._refresh_flowpaths_table()
            self._update_window_title()

    def _on_flowpath_edit(self, flowpath: FlowPath) -> None:
        from gui.dlg_flowpath_cfg import FlowPathConfigWizard
        dialog = FlowPathConfigWizard(self._plc, parent=self, flowpath=flowpath, store=self.store)
        if dialog.exec():
            self._refresh_flowpaths_table()
            self._update_window_title()

    def _on_flowpath_remove(self, name: str) -> None:
        if self.store.remove_flow_path(name):
            self._refresh_flowpaths_table()
            self._update_window_title()

    # CSV ---------------------------------------------------------------
    def on_export_models_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Models to CSV", "models.csv", "CSV Files (*.csv)")
        if path:
            try:
                export_models_csv(self.get_configured_models(), path, include_example_when_empty=True)
            except Exception as exc:
                QMessageBox.critical(self, "Export Models Failed", str(exc))

    def on_import_models_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Models from CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        try:
            existing = {model.name.casefold(): model for model in self.get_configured_models()}
            for model in import_models_csv(path):
                existing[model.name.casefold()] = model
            self.set_configured_models(list(existing.values()))
        except Exception as exc:
            QMessageBox.critical(self, "Import Models Failed", str(exc))

    def on_export_flowpaths_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Flow Paths to CSV", "flowpaths.csv", "CSV Files (*.csv)")
        if path:
            try:
                export_flowpaths_csv(self.get_flowpaths(), path, include_example_when_empty=True)
            except Exception as exc:
                QMessageBox.critical(self, "Export Flow Paths Failed", str(exc))

    def on_import_flowpaths_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Flow Paths from CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        try:
            existing = {item.name.casefold(): item for item in self.get_flowpaths()}
            for item in import_flowpaths_csv(path, flowpath_ctor=None):
                flowpath = item if isinstance(item, FlowPath) else FlowPath.from_dict(item)
                if flowpath.name:
                    existing[flowpath.name.casefold()] = flowpath
            self.set_flowpaths(list(existing.values()))
        except Exception as exc:
            QMessageBox.critical(self, "Import Flow Paths Failed", str(exc))

    # Simulation --------------------------------------------------------
    def on_start(self) -> None:
        report = self.runtime.build()
        if not report.is_valid:
            QMessageBox.warning(self, "Simulation Validation", report.format_for_dialog())
            return
        self.runtime.start()

    def on_stop(self) -> None:
        self.runtime.stop()

    def on_reset(self) -> None:
        report = self.runtime.reset()
        if not report.is_valid:
            QMessageBox.warning(self, "Simulation Validation", report.format_for_dialog())

    def on_validate(self) -> None:
        report = self.runtime.validate()
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Information if report.is_valid else QMessageBox.Icon.Warning)
        dialog.setWindowTitle("Simulation Validation")
        dialog.setText(report.format_for_dialog())
        dialog.exec()

    def on_read_from_plc(self) -> None:
        if not self.runtime.is_plc_connected:
            QMessageBox.information(self, "PLC Offline", "No PLC is connected. Offline project editing and simulation remain available.")
            return
        QMessageBox.information(self, "PLC Discovery", "PLC discovery can supply PlantPAx modules through SimulationManager.synchronize_discovery().")

    # Refresh/helpers ---------------------------------------------------
    def get_configured_models(self) -> list[ConfiguredModel]:
        return list(self.models)

    def set_configured_models(self, models: list[ConfiguredModel]) -> None:
        self.store.set_models(models)
        self._reload_models()

    def get_flowpaths(self) -> list[FlowPath]:
        return self.store.get_flow_paths()

    def set_flowpaths(self, items: list[FlowPath]) -> None:
        self.store.set_flow_paths(items)
        self._refresh_flowpaths_table()
        self._update_window_title()

    def _reload_models(self) -> None:
        self.models = self.store.get_models()
        self.runtime.build()
        self._refresh_pv_table()
        self._update_window_title()

    def _refresh_all(self) -> None:
        self.models = self.store.get_models()
        self._refresh_pv_table()
        self._refresh_flowpaths_table()
        self._refresh_values(self.runtime.current_values())
        self._refresh_connection_status()
        self._update_window_title()

    def _refresh_values(self, values: dict[str, float]) -> None:
        self._last_values = dict(values)
        for row in range(self.process_table.rowCount()):
            name_item = self.process_table.item(row, 0)
            value_item = self.process_table.item(row, 4)
            if name_item is not None and value_item is not None:
                value_item.setText(self._format_value(values.get(name_item.text())))

    @staticmethod
    def _configure_table(table: QTableWidget) -> None:
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.verticalHeader().setVisible(False)

    def _selected_model_name(self) -> str | None:
        row = self.process_table.currentRow()
        item = self.process_table.item(row, 0) if row >= 0 else None
        return item.text() if item else None

    def _selected_flowpath_name(self) -> str | None:
        row = self.flowpaths_table.currentRow()
        item = self.flowpaths_table.item(row, 0) if row >= 0 else None
        return item.text() if item else None

    def _get_selected_flowpath(self) -> FlowPath | None:
        name = self._selected_flowpath_name()
        return next((item for item in self.get_flowpaths() if name and item.name.casefold() == name.casefold()), None)

    @staticmethod
    def _restore_row_selection(table: QTableWidget, name: str | None) -> None:
        if not name:
            return
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item and item.text() == name:
                table.selectRow(row)
                return

    def _model_status(self, model: ConfiguredModel) -> str:
        if self.runtime.validation_report.by_model().get(model.name):
            return "Error"
        if model.type in {"", "None"}:
            return "Unconfigured"
        return "Ready"

    @staticmethod
    def _format_value(value: float | None) -> str:
        return "—" if value is None else f"{value:.3f}"

    def _update_window_title(self) -> None:
        dirty = " *" if self.store.is_dirty else ""
        self.setWindowTitle(f"{self.store.display_name}{dirty} — pySIMIO")
        self.project_status.setText(f"Project: {self.store.path if self.store.path else 'Not yet saved'}")

    def _refresh_connection_status(self) -> None:
        self.plc_status.setText("PLC: Connected" if self.runtime.is_plc_connected else "PLC: Offline")
        self.scan_action.setEnabled(self.runtime.is_plc_connected)

    def _on_runtime_state_changed(self, state: RuntimeState) -> None:
        self.runtime_status.setText(f"Simulation: {state.value}")
        running = state is RuntimeState.RUNNING
        self.act_start.setEnabled(not running)
        self.act_stop.setEnabled(running)

    def _on_runtime_fault(self, message: str) -> None:
        QMessageBox.critical(self, "Simulation Fault", message)

    def _recent_projects(self) -> list[str]:
        value = self._settings.value("recent_projects", [])
        if isinstance(value, str):
            value = [value]
        return [str(item) for item in value if Path(str(item)).exists()]

    def _remember_project(self, path: Path | None) -> None:
        if path is None:
            return
        normalized = str(path.resolve())
        recent = [item for item in self._recent_projects() if item != normalized]
        recent.insert(0, normalized)
        self._settings.setValue("recent_projects", recent[:MAX_RECENT_PROJECTS])
        self._settings.setValue("last_project_directory", str(path.parent))

    def _last_project_directory(self) -> str:
        return str(self._settings.value("last_project_directory", str(Path.home())))

    def _rebuild_recent_menu(self) -> None:
        self.recent_menu.clear()
        recent = self._recent_projects()
        if not recent:
            action = self.recent_menu.addAction("No Recent Projects")
            action.setEnabled(False)
            return
        for path in recent:
            action = self.recent_menu.addAction(Path(path).name)
            action.setToolTip(path)
            action.triggered.connect(lambda checked=False, project_path=path: self._open_recent(project_path))

    def _open_recent(self, path: str) -> None:
        if self._confirm_discard_changes():
            self._open_project_path(path)

    def closeEvent(self, event) -> None:
        if not self._confirm_discard_changes():
            event.ignore()
            return
        self.runtime.close()
        event.accept()
