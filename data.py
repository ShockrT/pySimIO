PLANT_PAX_MODULES = ["P_ANALOG_INPUT", "P_ANALOG_OUTPUT", "P_DISCRETE_INPUT", "P_DISCRETE_OUTPUT",
                     "P_VALVE_DISCRETE", "P_VARIABLE_SPEED_DRIVE", "P_MOTOR_DISCRETE", "P_PID", "P_D4SD"]
PV_MODULE_TYPES = ["P_ANALOG_INPUT"]
CV_MODULE_TYPES = ["P_VARIABLE_SPEED_DRIVE", "P_PID", "P_ANALOG_OUTPUT"]
MODEL_TYPES = ["flow", "pressure", "temperature", "level"]
class ProcessVariable:
    def __init__(self):
        self.name = ""
        self.active = False
        self.cvTag = ""
        self.EUMin = 0.0
        self.EUMax = 100.0
        self.value = 0.0
        self.cvRelationship = "" # direct or inverse
        self.simRate = 0.1
        self.model_configured = False
        self.model_type = ""
        self.model = None

    def toggle_active(self):
        self.active = not self.active
        print(f"Active status toggled for: {self.name}")

    def print_properties(self):
        print(f"Name: {self.name}")
        print(f"EUMin: {self.EUMin}")
        print(f"EUMax: {self.EUMax}")
        print(f"Value: {self.value}")
        print(f"cvName: {self.cvTag}")
        print(f"cvRelationship: {self.cvRelationship}")

    # def check_model(self, device_type: str) -> bool:
    #     if device_type in self.DEVICE_TYPES:
    #         match device_type:
    #             case "flow":
    #                 pass

class ControlVariable:
    def __init__(self):
        self.name = ""
        self.EUMin = 0.0
        self.EUMax = 100.0
        self.value = 0.0

class PLCData:
    def __init__(self):
        self.pax_modules_list = [] # All PlantPAx modules found in tag export
        self.pv_list = [] # List of PV Names (strings)
        self.cv_list = [] # List of CV Names (strings)
        self.valve_list = []
        # module_dict is a dictionary whose keys are the PlantPAx module types
        # and whose values are lists of PlantPAx modules (represented as dictionaries) with that data type
        self.module_dict = {}

    def print_tags(self):
        for pv in self.pv_list:
            print(pv.name)

    def get_plant_pax_modules(self, input_data):
        # Get list of all controller-scoped PlantPAx module tags from the input data
        all_pax_tags_list = [item for item in input_data
                           if item["DATATYPE"] in PLANT_PAX_MODULES and str(item["SCOPE"]) == "nan"]
        # Create new dictionary for each PlantPAx module tag
        for tag in all_pax_tags_list:
            new_module = {"Name": str(tag["NAME"]),
                          "Description": str(tag["DESCRIPTION"]),
                          "Data Type": str(tag["DATATYPE"])}
            # Add the new module to the PlantPAx module dictionary
            try:
                self.module_dict[new_module["Data Type"]].append(new_module)
            except KeyError:
                self.module_dict[new_module["Data Type"]] = [new_module]
            # Create new Process Variable object and add to list of Process Variables
            if new_module["Data Type"] in PV_MODULE_TYPES:
                new_pv = ProcessVariable()
                new_pv.name = new_module["Name"]
                self.pv_list.append(new_pv)
            # Populate a list of possible control variables based on data type
            if new_module["Data Type"] in CV_MODULE_TYPES:
                self.cv_list.append(new_module["Name"])






class FlowPath:
    def __init__(self):
        # Each node is a valve in the path
        self.nodes = [FlowPathNode]

class FlowPathNode:
    def __init__(self):
        self.node = {
            "name": str,
            "is_open": bool
        }