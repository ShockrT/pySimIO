import json
from json import JSONDecodeError
from gui.dlg_flowpath_cfg import FlowPathConfigWizard
from core.constants import MODEL_TYPES
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QDialog, QScrollArea, QFormLayout, QPushButton, \
    QComboBox, QGroupBox, QHBoxLayout, QLineEdit


class ModelConfigWizard(QDialog):
    def __init__(self, plc, pv):
        super().__init__()
        self.plc = plc
        self.pv = pv
        self.setWindowTitle(f"Configure Model: {pv.name}")
        self.setMinimumSize(600, 600)
        main_layout = QVBoxLayout(self)
        # Scroll area wrapper
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        form_container = QWidget()
        form_layout = QFormLayout(form_container)
        self.save_btn = QPushButton("Save Model")
        self.save_btn.clicked.connect(self.save_model) # type: ignore
        # Model Select Combobox
        self.cmb = QComboBox()
        self.cmb.addItems(MODEL_TYPES)
        self.cmb.setCurrentText(pv.model_type or "None")
        self.cmb.currentTextChanged.connect(self.on_model_select) # type: ignore
        form_layout.addWidget(self.save_btn)
        form_layout.addWidget(QLabel("Model Type:"))
        form_layout.addWidget(self.cmb)
        self.container = QWidget()
        main_layout.addWidget(self.container)
        self.create_fp_btn_flow = QPushButton("Create New Flow Path")
        self.create_fp_btn_pressure = QPushButton("Create New Flow Path")
        self.create_fp_btn_temperature = QPushButton("Create New Flow Path")
        self.create_fp_btn_level = QPushButton("Create New Flow Path")

        # Flow Model Widgets
        self.flow_cv_rows = []
        self.fp_label = QLabel("Flow Path:")
        self.fp_combo = QComboBox()
        self.flow_group = QGroupBox("Control Variables for Flow")
        self.flow_layout = QVBoxLayout()
        self.flow_group.setLayout(self.flow_layout)
        self.add_flow_cv_btn = QPushButton("Add Control Variable")
        self.add_flow_cv_btn.clicked.connect(self._add_flow_cv_row) # type: ignore
        self.flow_layout.addWidget(self.add_flow_cv_btn)
        form_layout.addRow(self.flow_group)
        form_layout.addWidget(self.create_fp_btn_flow)
        form_layout.addRow(self.fp_label, self.fp_combo)

        # Pressure Model Widgets
        self.pressure_cv_rows = []
        self.pressure_group = QGroupBox("Control Variables for Pressure")
        self.pressure_layout = QVBoxLayout()
        self.pressure_group.setLayout(self.pressure_layout)
        self.pressure_group.hide()
        self.add_pressure_cv_btn = QPushButton("Add Control Variable")
        self.add_pressure_cv_btn.clicked.connect(self._add_pressure_cv_row) # type: ignore
        self.add_pressure_cv_btn.hide()
        self.pressure_layout.addWidget(self.add_pressure_cv_btn)
        self.press_inlet_path_label = QLabel("Inlet Flow Path:")
        self.press_inlet_path_combo = QComboBox()
        self.press_outlet_path_label = QLabel("Outlet Flow Path:")
        self.press_outlet_path_combo = QComboBox()
        form_layout.addRow(self.pressure_group)
        form_layout.addRow(QLabel(""), self.create_fp_btn_pressure)
        form_layout.addRow(self.press_inlet_path_label, self.press_inlet_path_combo)
        form_layout.addRow(self.press_outlet_path_label, self.press_outlet_path_combo)

        # Temperature Model Widgets
        self.heat_cv_rows = []
        self.cool_cv_rows = []
        self.heat_group = QGroupBox("Heat Control Variables")
        self.heat_layout = QVBoxLayout()
        self.heat_group.setLayout(self.heat_layout)
        self.add_heat_cv_btn = QPushButton("Add Heat CV")
        self.add_heat_cv_btn.clicked.connect(self._add_heat_cv_row) # type: ignore
        self.heat_layout.addWidget(self.add_heat_cv_btn)
        self.cool_group = QGroupBox("Cool Control Variables")
        self.cool_layout = QVBoxLayout()
        self.cool_group.setLayout(self.cool_layout)
        self.add_cool_cv_btn = QPushButton("Add Cool CV")
        self.add_cool_cv_btn.clicked.connect(self._add_cool_cv_row) # type: ignore
        self.cool_layout.addWidget(self.add_cool_cv_btn)
        self.heat_path_label = QLabel("Heating Flow Path:")
        self.heat_path_combo = QComboBox()
        self.cool_path_label = QLabel("Cooling Flow Path:")
        self.cool_path_combo = QComboBox()
        form_layout.addRow(self.heat_group)
        form_layout.addRow(self.cool_group)
        form_layout.addRow(QLabel(""), self.create_fp_btn_temperature)
        form_layout.addRow(self.heat_path_label, self.heat_path_combo)
        form_layout.addRow(self.cool_path_label, self.cool_path_combo)

        # Level Model Widgets
        self.inlet_rows = []
        self.outlet_rows = []
        self.inlet_group = QGroupBox("Inlet Flow Paths")
        self.inlet_layout = QVBoxLayout()
        self.inlet_group.setLayout(self.inlet_layout)
        self.outlet_group = QGroupBox("Outlet Flow Paths")
        self.outlet_layout = QVBoxLayout()
        self.outlet_group.setLayout(self.outlet_layout)
        self.add_inlet_btn = QPushButton("Add Inlet Flow Path")
        self.add_outlet_btn = QPushButton("Add Outlet Flow Path")
        self.add_inlet_btn.clicked.connect(self._add_inlet_row) # type: ignore
        self.add_outlet_btn.clicked.connect(self._add_outlet_row) # type: ignore
        self.inlet_layout.addWidget(self.add_inlet_btn)
        self.outlet_layout.addWidget(self.add_outlet_btn)
        form_layout.addRow(QLabel(""), self.create_fp_btn_level)
        form_layout.addRow(self.inlet_group)
        form_layout.addRow(self.outlet_group)

        # Set form_layout container as the scrollable widget
        scroll_area.setWidget(form_container)

        # Add scroll area to the dialog's main layout
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

        self.hide_dynamic_fields()
        self.update_model_view()
        self.load_model()

    def on_model_select(self, text):
        self.pv.model_type = text
        self.hide_dynamic_fields()
        self.update_model_view()

    def hide_dynamic_fields(self):
        self.flow_group.hide()
        self.add_flow_cv_btn.hide()
        self.fp_label.hide()
        self.fp_combo.hide()
        self.create_fp_btn_flow.hide()

        self.pressure_group.hide()
        self.add_pressure_cv_btn.hide()
        self.press_inlet_path_label.hide()
        self.press_inlet_path_combo.hide()
        self.press_outlet_path_label.hide()
        self.press_outlet_path_combo.hide()
        self.create_fp_btn_pressure.hide()

        self.heat_group.hide()
        self.add_heat_cv_btn.hide()
        self.cool_group.hide()
        self.add_cool_cv_btn.hide()
        self.heat_path_label.hide()
        self.heat_path_combo.hide()
        self.cool_path_label.hide()
        self.cool_path_combo.hide()
        self.create_fp_btn_temperature.hide()

        self.inlet_group.hide()
        self.outlet_group.hide()
        self.add_inlet_btn.hide()
        self.add_outlet_btn.hide()
        self.create_fp_btn_level.hide()

    def show_dynamic_fields(self):
        model_type = self.pv.model_type
        if model_type == "Flow":
            self.flow_group.show()
            self.add_flow_cv_btn.show()
            self.fp_label.show()
            self.create_fp_btn_flow.show()
            self.fp_combo.show()
        elif model_type == "Pressure":
            self.pressure_group.show()
            self.add_pressure_cv_btn.show()
            self.create_fp_btn_pressure.show()
            self.press_inlet_path_label.show()
            self.press_inlet_path_combo.show()
            self.press_outlet_path_label.show()
            self.press_outlet_path_combo.show()
        elif model_type == "Temperature":
            self.heat_group.show()
            self.cool_group.show()
            self.add_heat_cv_btn.show()
            self.add_cool_cv_btn.show()
            self.create_fp_btn_temperature.show()
            self.heat_path_label.show()
            self.heat_path_combo.show()
            self.cool_path_label.show()
            self.cool_path_combo.show()
        elif model_type == "Level":
            self.create_fp_btn_level.show()
            self.inlet_group.show()
            self.outlet_group.show()
            self.add_inlet_btn.show()
            self.add_outlet_btn.show()
        else:
            pass

    def update_model_view(self):
        if self.pv.model_type == "Flow":
            try:
                self.create_fp_btn_flow.clicked.disconnect() # type: ignore
            except TypeError:
                pass  # Wasn't connected yet — safe to ignore
            self.fp_combo.clear()
            self.create_fp_btn_flow.clicked.connect(self.create_new_flow_path)  # type: ignore
            self.fp_combo.addItems(self.get_flow_path_names())
            self.fp_combo.currentTextChanged.connect(self.on_flow_path_select) # type: ignore
            #self._add_flow_cv_row()
            self.show_dynamic_fields()
        elif self.pv.model_type == "Pressure":
            try:
                self.create_fp_btn_pressure.clicked.disconnect() # type: ignore
            except TypeError:
                pass  # Wasn't connected yet — safe to ignore
            self.create_fp_btn_pressure.clicked.connect(self.create_new_flow_path)  # type: ignore
            self.press_inlet_path_combo.clear()
            self.press_outlet_path_combo.clear()
            self.press_inlet_path_combo.addItems(self.get_flow_path_names())
            self.press_inlet_path_combo.currentTextChanged.connect(self.on_flow_path_select) # type: ignore
            self.press_outlet_path_combo.addItems(self.get_flow_path_names())
            self.press_outlet_path_combo.currentTextChanged.connect(self.on_flow_path_select) # type: ignore
            self.show_dynamic_fields()
        elif self.pv.model_type == "Temperature":
            try:
                self.create_fp_btn_temperature.clicked.disconnect() # type: ignore
            except TypeError:
                pass  # Wasn't connected yet — safe to ignore
            self.create_fp_btn_temperature.clicked.connect(self.create_new_flow_path)  # type: ignore
            self.heat_path_combo.clear()
            self.cool_path_combo.clear()
            self.heat_path_combo.addItems(self.get_flow_path_names())
            self.heat_path_combo.currentTextChanged.connect(self.on_flow_path_select) # type: ignore
            self.cool_path_combo.addItems(self.get_flow_path_names())
            self.cool_path_combo.currentTextChanged.connect(self.on_flow_path_select) # type: ignore
            self.show_dynamic_fields()
        elif self.pv.model_type == "Level":
            try:
                self.create_fp_btn_level.clicked.disconnect() # type: ignore
            except TypeError:
                pass  # Wasn't connected yet — safe to ignore
            self.create_fp_btn_level.clicked.connect(self.create_new_flow_path)  # type: ignore
            self._add_inlet_row()
            self._add_outlet_row()
            self.show_dynamic_fields()
        else:
            pass

    def _add_flow_cv_row(self, prefill=None):
        row_widget = QWidget()
        layout = QHBoxLayout()
        row_widget.setLayout(layout)

        control_combo = QComboBox()
        gain_input = QLineEdit()
        gain_input.setPlaceholderText("Gain")
        gain_input.setFixedWidth(60)

        remove_btn = QPushButton("×")
        remove_btn.setFixedWidth(24)
        remove_btn.clicked.connect(lambda: self._remove_flow_cv_row(row_widget)) # type: ignore

        # Populate combo with control variables
        for var in self.plc.cv_list:
            control_combo.addItem(var.name)

        layout.addWidget(control_combo)
        layout.addWidget(gain_input)
        layout.addWidget(remove_btn)

        self.flow_layout.insertWidget(self.flow_layout.count() - 1, row_widget)
        self.flow_cv_rows.append({
            "widget": row_widget,
            "control_combo": control_combo,
            "gain_input": gain_input
        })
        if prefill:
            control_combo.setCurrentText(prefill.get("control_variable", ""))
            gain_input.setText(str(prefill.get("gain", 0)))

    def _remove_flow_cv_row(self, widget):
        self.flow_cv_rows = [r for r in self.flow_cv_rows if r["widget"] != widget]
        widget.setParent(None)
        widget.deleteLater()

    def _add_pressure_cv_row(self, prefill=None):
        row_widget = QWidget()
        layout = QHBoxLayout()
        row_widget.setLayout(layout)

        control_combo = QComboBox()
        gain_input = QLineEdit()
        gain_input.setPlaceholderText("Gain")
        gain_input.setFixedWidth(60)

        remove_btn = QPushButton("×")
        remove_btn.setFixedWidth(24)
        remove_btn.clicked.connect(lambda: self._remove_pressure_cv_row(row_widget)) # type: ignore

        # Populate combo with available control variables
        for cv in self.plc.cv_list:
            control_combo.addItem(cv.name)

        layout.addWidget(control_combo)
        layout.addWidget(gain_input)
        layout.addWidget(remove_btn)

        self.pressure_layout.insertWidget(self.pressure_layout.count() - 1, row_widget)
        self.pressure_cv_rows.append({
            "widget": row_widget,
            "control_combo": control_combo,
            "gain_input": gain_input
        })
        if prefill:
            control_combo.setCurrentText(prefill.get("control_variable", ""))
            gain_input.setText(str(prefill.get("gain", 0)))

    def _remove_pressure_cv_row(self, widget):
        self.pressure_cv_rows = [r for r in self.pressure_cv_rows if r["widget"] != widget]
        widget.setParent(None)
        widget.deleteLater()

    def _add_heat_cv_row(self, prefill=None):
        self._add_cv_row(self.heat_layout, self.heat_cv_rows, self._remove_heat_cv_row, prefill)

    def _remove_heat_cv_row(self, widget):
        self._remove_cv_row(widget, self.heat_cv_rows)

    def _add_cool_cv_row(self, prefill=None):
        self._add_cv_row(self.cool_layout, self.cool_cv_rows, self._remove_cool_cv_row, prefill)

    def _remove_cool_cv_row(self, widget):
        self._remove_cv_row(widget, self.cool_cv_rows)

    def _add_cv_row(self, layout, row_list, remove_callback, prefill=None):
        row_widget = QWidget()
        row_layout = QHBoxLayout()
        row_widget.setLayout(row_layout)

        control_combo = QComboBox()
        gain_input = QLineEdit()
        gain_input.setPlaceholderText("Gain")
        gain_input.setFixedWidth(60)

        remove_btn = QPushButton("×")
        remove_btn.setFixedWidth(24)
        remove_btn.clicked.connect(lambda: remove_callback(row_widget)) # type: ignore

        for var in self.plc.cv_list:
            control_combo.addItem(var.name)

        row_layout.addWidget(control_combo)
        row_layout.addWidget(gain_input)
        row_layout.addWidget(remove_btn)

        layout.insertWidget(layout.count() - 1, row_widget)
        row_list.append({
            "widget": row_widget,
            "control_combo": control_combo,
            "gain_input": gain_input
        })

        if prefill:
            control_combo.setCurrentText(prefill.get("control_variable", ""))
            gain_input.setText(str(prefill.get("gain", 0)))

    def _remove_cv_row(self, widget, row_list):
        row_list[:] = [r for r in row_list if r["widget"] != widget]
        widget.setParent(None)
        widget.deleteLater()

    def _remove_row(self, widget, row_list):
        row_list[:] = [r for r in row_list if r["widget"] != widget]
        widget.setParent(None)
        widget.deleteLater()

    def _add_inlet_row(self, prefill=None):
        self._add_flow_path_row(self.inlet_layout, self.inlet_rows, prefill)
        self.adjustSize()

    def _add_outlet_row(self, prefill=None):
        self._add_flow_path_row(self.outlet_layout, self.outlet_rows, prefill)
        self.adjustSize()

    def _add_flow_path_row(self, parent_layout, row_list, prefill=None):
        row_widget = QWidget()
        layout = QHBoxLayout()
        row_widget.setLayout(layout)

        flow_combo = QComboBox()
        gain_input = QLineEdit()
        gain_input.setPlaceholderText("1.0")
        gain_input.setFixedWidth(60)

        control_combo = QComboBox()
        control_combo.setPlaceholderText("Control Variable")

        remove_btn = QPushButton("×")
        remove_btn.setFixedWidth(24)
        remove_btn.clicked.connect(lambda: self._remove_row(row_widget, row_list)) # type: ignore

        # Populate flow path & control variable combo boxes
        for fp in self.get_flow_path_names():
            flow_combo.addItem(fp)

        for cv in self.plc.cv_list:
            control_combo.addItem(cv.name)

        layout.addWidget(flow_combo)
        layout.addWidget(gain_input)
        layout.addWidget(control_combo)
        layout.addWidget(remove_btn)

        parent_layout.insertWidget(parent_layout.count() - 1, row_widget)  # Above add button
        row_list.append({
            "widget": row_widget,
            "flow_combo": flow_combo,
            "gain_input": gain_input,
            "control_combo": control_combo
        })
        if prefill:
            flow_combo.setCurrentText(prefill.get("flow_path", ""))
            gain_input.setText(str(prefill.get("gain", 0)))
            control_combo.setCurrentText(prefill.get("control_variable", ""))

    def on_flow_path_select(self, text):
        if hasattr(self.pv, "model") and self.pv.model:
            self.pv.model.flow_path.name = text

    def create_new_flow_path(self):
        dlg = FlowPathConfigWizard(self.plc)
        dlg.flow_path_saved.connect(self.on_new_flow_path_created)  # connect signal
        dlg.exec()

    # TODO #1) Add model save to file functionality
    def save_model(self):
        print("Saving...")
        try:
            with open("./assets/pv_models.json", "r") as f:
                data = json.load(f)
        except (FileNotFoundError, JSONDecodeError):
            data = {}

        model_type = self.cmb.currentText()
        self.pv.model_type = model_type
        config = {"model_type": model_type}

        if model_type == "Flow":
            config.update(self._collect_flow_model_config())
        elif model_type == "Pressure":
            config.update(self._collect_pressure_model_config())
        elif model_type == "Temperature":
            config.update(self._collect_temperature_model_config())
        elif model_type == "Level":
            config.update(self._collect_level_model_config())

        data[self.pv.name] = config

        with open("./assets/pv_models.json", "w") as f:
            json.dump(data, f, indent=4)

        self.accept()

    def _collect_flow_model_config(self):
        return {
            "flow_path": self.fp_combo.currentText(),
            "control_variables": self._extract_cv_config(self.flow_cv_rows)
        }

    def _collect_pressure_model_config(self):
        return {
            "inlet_flow_path": self.press_inlet_path_combo.currentText(),
            "outlet_flow_path": self.press_outlet_path_combo.currentText(),
            "control_variables": self._extract_cv_config(self.pressure_cv_rows)
        }

    def _collect_temperature_model_config(self):
        return {
            "heating_flow_path": self.heat_path_combo.currentText(),
            "cooling_flow_path": self.cool_path_combo.currentText(),
            "heat_control_variables": self._extract_cv_config(self.heat_cv_rows),
            "cool_control_variables": self._extract_cv_config(self.cool_cv_rows)
        }

    def _collect_level_model_config(self):
        return {
            "inlet_paths": self._extract_flow_path_config(self.inlet_rows),
            "outlet_paths": self._extract_flow_path_config(self.outlet_rows)
        }

    def _extract_cv_config(self, row_list):
        results = []
        for row in row_list:
            control_var = row["control_combo"].currentText()
            try:
                gain = float(row["gain_input"].text())
            except ValueError:
                gain = 1.0
            results.append({
                "control_variable": control_var,
                "gain": gain
            })
        return results

    def _extract_flow_path_config(self, row_list):
        results = []
        for row in row_list:
            flow_path = row["flow_combo"].currentText()
            try:
                gain = float(row["gain_input"].text())
            except ValueError:
                gain = 1.0
            control_var = row["control_combo"].currentText()
            results.append({
                "flow_path": flow_path,
                "gain": gain,
                "control_variable": control_var
            })
        return results

    def load_model(self):
        try:
            with open("./assets/pv_models.json", "r") as f:
                data = json.load(f)
        except (FileNotFoundError, JSONDecodeError):
            return  # Nothing to load

        config = data.get(self.pv.name)
        if not config:
            return

        model_type = config.get("model_type", "None")
        self.cmb.setCurrentText(model_type)
        self.pv.model_type = model_type  # Ensure internal state is updated
        self.hide_dynamic_fields()
        self.update_model_view()

        if model_type == "Flow":
            self.fp_combo.setCurrentText(config.get("flow_path", ""))
            for entry in config.get("control_variables", []):
                self._add_flow_cv_row(prefill=entry)

        elif model_type == "Pressure":
            self.press_inlet_path_combo.setCurrentText(config.get("inlet_flow_path", ""))
            self.press_outlet_path_combo.setCurrentText(config.get("outlet_flow_path", ""))
            for entry in config.get("control_variables", []):
                self._add_pressure_cv_row(prefill=entry)

        elif model_type == "Temperature":
            self.heat_path_combo.setCurrentText(config.get("heating_flow_path", ""))
            self.cool_path_combo.setCurrentText(config.get("cooling_flow_path", ""))
            for entry in config.get("heat_control_variables", []):
                self._add_cv_row(self.heat_layout, self.heat_cv_rows, self._remove_heat_cv_row, entry)
            for entry in config.get("cool_control_variables", []):
                self._add_cv_row(self.cool_layout, self.cool_cv_rows, self._remove_cool_cv_row, entry)

        elif model_type == "Level":
            for inlet in config.get("inlet_paths", []):
                self._add_flow_path_row(self.inlet_layout, self.inlet_rows, inlet)
            for outlet in config.get("outlet_paths", []):
                self._add_flow_path_row(self.outlet_layout, self.outlet_rows, outlet)

        self.show_dynamic_fields()

    def get_flow_path_names(self):
        fp_names = []
        try:
            with open("./assets/flowpaths.json", "r") as fp_file:
                # Reading existing data
                fp_data = json.load(fp_file)
                for key, value in fp_data.items():
                    fp_names.append(f"{key} - {value["description"]}")
        except (FileNotFoundError, JSONDecodeError):
            pass
        return fp_names

    def on_new_flow_path_created(self, new_flow_path_name):
        # Refresh combo box contents
        self.fp_combo.clear()
        self.fp_combo.addItems(self.get_flow_path_names())
        self.fp_combo.setCurrentText(new_flow_path_name)  # Optional: auto-select the newly added one
