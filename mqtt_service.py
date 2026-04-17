#mqtt_service.py

import logging
import paho.mqtt.client as mqtt
from config import BROKER, PORT, TRIGGER_TOPIC

logging.basicConfig(level=logging.INFO)

class MQTTService:
    def __init__(self, callback):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = callback

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("Connected to MQTT broker.")
            client.subscribe(TRIGGER_TOPIC)

    def start(self):
        self.client.connect(BROKER, PORT, 60)
        self.client.loop_forever()