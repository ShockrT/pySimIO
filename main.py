# v1.0
# The program reads a list of AnalogInputs from the AnalogInputs.csv file into a dictionary
# and performs the following operations for each:
# 1) Reads the metadata into a dictionary
# 2) Reads the tag values from the P_ANALOG_INPUT block (i.e. PVEUMin/Max, .Val values
# 3) Reads the metadata of the Control Variable
# 4) Reads the appropriate tag values from the CV (i.e. CVEUMin/Max, .Val*)
# 5) Converts the PV and CV values to a percent of its range
# 6) Creates a simulated output PV value based on the simulation model's "compute_value" function using
#    data from Steps #1-5
# 7) Saves data from previous steps to "metadata.csv"
import sys

from PyQt6.QtWidgets import QApplication

#from pycomm3 import LogixDriver
from core.opcinterface import OPCUAInterface
from core.simulator import PLCSimulator
from gui.mainwindow import MainWindow
import pandas
from core.data import PLCData

PLC_PATH = "DS3::[CAUSTIC]"
ANALOG_INPUT_FILE = "assets/AnalogInputs.csv"
opc_server_url = "opc.tcp://azrnadwapp1dd94:4990/FactoryTalkLinxGateway1"  # Change this to match your PLC's OPC UA server
#CAUSTIC_PLC_PATH = "172.30.71.16/2"
TAG_LIST_FILE = "assets/CAUSTIC_31Jan2025_Tags.CSV"

plc_data = PLCData()
# Extract PlantPAx Modules from csv
try:
    tag_list = pandas.read_csv(TAG_LIST_FILE).to_dict(orient="records")
except FileNotFoundError:
    print("File Not Found")
else:
    plc_data.get_plant_pax_modules(tag_list)

opc_interface = OPCUAInterface(opc_server_url)
#opc_interface.connect()
plc_sim = PLCSimulator(opc_interface)

app = QApplication(sys.argv)

# Create and show your main window
window = MainWindow(opc_interface, plc_sim, plc_data)
window.show()

sys.exit(app.exec())

#gui = GUI(opc_interface, plc_sim, plc_data)
#gui.run()

#plc_sim.simulate(data.pvList)


#opc_interface.disconnect()
