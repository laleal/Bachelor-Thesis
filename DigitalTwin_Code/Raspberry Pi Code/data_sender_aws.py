import json
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

class DataSender:
    def __init__(self, endpoint, root_ca, private_key, certificate,
                 client_id="myClient", topic="my/topic"):
        self.topic = topic
        self.client = AWSIoTMQTTClient(client_id)
        self.client.configureEndpoint(endpoint, 8883)
        self.client.configureCredentials(root_ca, private_key, certificate)

        #  some settings
        self.client.configureOfflinePublishQueueing(-1)
        self.client.configureDrainingFrequency(2)
        self.client.configureConnectDisconnectTimeout(10)
        self.client.configureMQTTOperationTimeout(5)
        self.client.connect()
        
        print(f"Connected to AWS")

    def publish(self, data, qos=1):
        msg = json.dumps(data)
        self.client.publish(self.topic, msg, qos)
        print(f"Published {msg}")

    def disconnect(self):
        self.client.disconnect()
        print("Disconnected from AWS.")
