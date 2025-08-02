from functools import partial
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QTabWidget, QWidget, QVBoxLayout, QLabel, QDialog, QMainWindow, QHBoxLayout, QScrollArea, \
    QCheckBox, QPushButton
from gui.dlg_model_cfg import ModelConfigWizard
from core.constants import COLUMN_HEADINGS, COLUMN_WIDTHS

class MainWindow(QMainWindow):
    def __init__(self, opc_interface, plc_simulator, plc):
        super().__init__()
        # Create the OPC interface and simulator instances
        self.opc_interface = opc_interface
        self.plc_simulator = plc_simulator

        self.plc = plc
        self.pv_list = plc.pv_list
        self.setWindowTitle("pySIMIO")
        self.resize(800, 600)

        # Create the menu bar with all top-level menus
        self._create_menu_bar()

        # Create the tabbed layout and place widgets into their respective tabs
        self._create_tabs()

    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction(QAction("Open", self))
        file_menu.addAction(QAction("Save", self))
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close) # type: ignore
        file_menu.addAction(exit_action)

        # Edit Menu
        edit_menu = menu_bar.addMenu("Edit")
        edit_menu.addAction(QAction("Undo", self))
        edit_menu.addAction(QAction("Redo", self))

        # Connections Menu
        connections_menu = menu_bar.addMenu("Connections")
        connect_action = QAction("Connect", self)
        connect_action.triggered.connect(self.show_plc_connection_dialog) # type: ignore
        connections_menu.addAction(connect_action)
        #connections_menu.addAction(QAction("Refresh", self))

        # Help Menu
        help_menu = menu_bar.addMenu("Help")
        help_menu.addAction(QAction("About", self))

    def _create_tabs(self):
        # Create the tab widget that holds all tab pages
        self.tab_widget = QTabWidget()

        # Add three tabs: Process Variables, Flow Paths, Equipment
        self.tab_widget.addTab(self._build_process_variables_tab(), "Process Variables")
        self.tab_widget.addTab(self._build_flow_paths_tab(), "Flow Paths")
        self.tab_widget.addTab(self._build_equipment_tab(), "Equipment")

        # Set the QTabWidget as the central widget of the main window
        self.setCentralWidget(self.tab_widget)

    def _build_process_variables_tab(self):
        # Create the main container widget for the tab
        tab = QWidget()
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Create the header for the tab
        header = QHBoxLayout()
        for heading, width in zip(COLUMN_HEADINGS, COLUMN_WIDTHS):
            lbl = QLabel(heading)
            lbl.setFixedWidth(width)
            lbl.setStyleSheet("font-weight: bold;")
            header.addWidget(lbl)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        table_layout = QVBoxLayout(container)

        # Populate table with list of Process Variables
        for pv in self.pv_list:
            row = QHBoxLayout()
            name = QLabel(pv.name)
            name.setFixedWidth(COLUMN_WIDTHS[0])
            chk = QCheckBox()
            chk.setChecked(pv.active if hasattr(pv, "active") else False)
            chk.stateChanged.connect(lambda _, pv=pv: pv.toggle_active()) # type: ignore
            chk.setFixedWidth(COLUMN_WIDTHS[1])

            dtype = QLabel(pv.model or "")
            dtype.setFixedWidth(COLUMN_WIDTHS[2])

            value = QLabel(f"{pv.value}")
            value.setFixedWidth(COLUMN_WIDTHS[3])

            btn = QPushButton("Configure Model")
            btn.clicked.connect(partial(self.open_model_config, pv)) # type: ignore
            btn.setFixedWidth(COLUMN_WIDTHS[4])

            for widget in (name, chk, dtype, value, btn):
                row.addWidget(widget)
            table_layout.addLayout(row)

        tab.setLayout(layout)
        return tab

    def _build_flow_paths_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Flow Paths UI goes here."))
        tab.setLayout(layout)
        return tab

    def _build_equipment_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Equipment UI goes here."))
        tab.setLayout(layout)
        return tab

    def open_model_config(self, pv):
        # Opens the model configuration wizard dialog
        dlg = ModelConfigWizard(self.plc, pv)
        dlg.exec()

    def show_plc_connection_dialog(self):
        from gui.dlg_plc_conn_cfg import PLCConnectionDialog  # if it's in a separate file

        dialog = PLCConnectionDialog(self)
        if dialog.exec() == QDialog.accepted:
            self.plc_connection = dialog.plc_connection
            print("PLC connected!")
            # Optionally: fetch tags or update UI
        else:
            print("PLC connection cancelled.")
