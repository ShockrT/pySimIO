# Intended for use with PlantPAx Library of Process Objects v5.x

PLANT_PAX_MODULES = ["P_ANALOG_INPUT", "P_ANALOG_OUTPUT", "P_DISCRETE_INPUT", "P_DISCRETE_OUTPUT",
                     "P_VALVE_DISCRETE", "P_VARIABLE_SPEED_DRIVE", "P_MOTOR_DISCRETE", "P_PID", "P_D4SD"]
ANALOG_INPUT_TYPES = ["P_ANALOG_INPUT"]
CV_MODULE_TYPES = ["P_VARIABLE_SPEED_DRIVE", "P_PID", "P_ANALOG_OUTPUT"]
PUMP_TYPES = ["P_VARIABLE_SPEED_DRIVE"]
VALVE_TYPES = ["P_VALVE_DISCRETE", "P_D4SD"]
CONTROL_VALVE_TYPES = ["P_ANALOG_OUTPUT"]
MODEL_TYPES = ["None", "Flow", "Pressure", "Temperature", "Level"]
COLUMN_HEADINGS = ["Analog Input", "Active", "Model Type", "Value", "Model"]
COLUMN_WIDTHS = [150, 60, 120, 80, 120]
opc_server_url = "opc.tcp://azrnadwapp1dd94:4990/FactoryTalkLinxGateway1"
