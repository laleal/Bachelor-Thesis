import json
from azure.iot.device import IoTHubDeviceClient, Message

class DataSender:
    def __init__(self, connection_string):
        self.client = IoTHubDeviceClient.create_from_connection_string(connection_string)
        self.client.connect()
        print("Connected to IoT Hub.")

    def send_data(self, data):
        # convert to json
        message_json = json.dumps(data)
        message = Message(message_json)
        self.client.send_message(message)
        print("Data sent:", message_json)

    def disconnect(self):
        self.client.disconnect()
