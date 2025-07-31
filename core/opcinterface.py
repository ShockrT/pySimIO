from opcua import Client, ua

GLOBAL_DATA_TYPE = ua.VariantType.Float  # Change this to the desired data type
PLC_PATH = "DS3::[CAUSTIC]"
AI_TAG_MEMBER = ".Set_VirtualPV"

class OPCUAInterface:
    def __init__(self, opc_server_url):
        self.client = Client(opc_server_url)

    def connect(self):
        try:
            self.client.connect()
            print("Connected to OPC UA Server")
        except Exception as e:
            print("Connection failed:", e)

    def disconnect(self):
        self.client.disconnect()
        print("Disconnected from OPC UA Server")

    def browse_structure(self, tag):
        try:
            node = self.client.get_node(f"ns=2;s={tag}")
            children = node.get_children()
            for child in children:
                print(f"Child: {child.get_browse_name().to_string()}")
        except Exception as e:
            print(f"Error browsing structure for {tag}: {e}")

    def read_tag(self, tag):
        try:
            node = self.client.get_node(f"ns=2;s={tag}")
            return node.get_value()
        except Exception as e:
            print(f"Error reading {tag}: {e}")
            return None

    def write_tag(self, tag, value):
        full_tag = PLC_PATH + tag + AI_TAG_MEMBER
        try:
            node = self.client.get_node(f"ns=2;s={full_tag}")
            node.set_value(ua.Variant(value, ua.VariantType.Float))
            print(f"{full_tag} set to {value}")
        except Exception as e:
            print(f"Error writing {full_tag}: {e}")
