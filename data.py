class ProcessVariable:
    def __init__(self):
        self.name = ""
        self.cvTag = ""
        self.EUMin = 0.0
        self.EUMax = 100.0
        self.Value = 0.0
        self.cvRelationship = "" # direct or inverse

    def print_properties(self):
        print(f"Name: {self.name}")
        print(f"EUMin: {self.EUMin}")
        print(f"EUMax: {self.EUMax}")
        print(f"Value: {self.Value}")
        print(f"cvName: {self.cvTag}")
        print(f"cvRelationship: {self.cvRelationship}")

class Data:
    def __init__(self):
        self.pvList = []

    # Take the data from the input csv and create a list of Tags
    def data_scrub(self, input_data):
        for item in input_data:
            if str(item["cvTag"]) != 'nan' and str(item["relationship"]) != 'nan':
                new_pv = ProcessVariable()
                new_pv.name = item["pvName"]
                new_pv.cvTag = item["cvTag"]
                new_pv.cvRelationship = item["relationship"]
                self.pvList.append(new_pv)

    def print_tags(self):
        for pv in self.pvList:
            print(pv.name)
