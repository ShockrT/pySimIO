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
import atexit

from opcinterface import OPCUAInterface
from simulator import PLCSimulator
from userinterface import GUI
import pandas
from data import Data

PLC_PATH = "DS3::[CAUSTIC]"
ANALOG_INPUT_FILE = "AnalogInputs.csv"
opc_server_url = "opc.tcp://azrnadwapp1dd94:4990/FactoryTalkLinxGateway1"  # Change this to match your PLC's OPC UA server

opc_interface = OPCUAInterface(opc_server_url)
opc_interface.connect()
plc_sim = PLCSimulator(opc_interface)
data = Data()
#gui = GUI(opc_interface, plc_sim)
#gui.run()

# Get list of Process Variables from csv
try:
    raw_data = pandas.read_csv(ANALOG_INPUT_FILE).to_dict(orient="records")
except FileNotFoundError:
    print("File Not Found")
else:
    # Data scrub function will create a list of PVs with the required information (CV Tag and relationship)
    data.data_scrub(input_data=raw_data)

plc_sim.simulate(data.pvList)

#output_df = pandas.DataFrame(vars(ProcessVariable) for pv in data.pvList) #Write tag data to output DataFrame
#output_df.to_csv("metadata.csv") #Write tag data to csv



opc_interface.disconnect()

atexit.register(opc_interface.disconnect)