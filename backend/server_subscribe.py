import logging
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta
from model import *

stream_handler = logging.StreamHandler()
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(level=logging.INFO)
_LOGGER.addHandler(stream_handler)

file_handler = logging.FileHandler("logs/backend.log")
_LOGGER.addHandler(file_handler)


MQTT_BROKER_URL = "127.0.0.1"
MQTT_BROKER_PORT = 1883
MQTT_CLIENT_ID = "Backend-Server"
MQTT_USERNAME = "smarttec"
MQTT_USERPASSWD = "smarttec"
MQTT_TOPIC = "event/status"
MQTT_QOS = 1

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        _LOGGER.info("Broker Server connected OK")
        client.subscribe(MQTT_TOPIC, MQTT_QOS)
    else:
        _LOGGER.info(f"Bad connection Returned code={rc}")

def on_disconnect(client, userdata, flags, rc=0):
    _LOGGER.info(f"{rc} Broker Server disconnected")

def on_subscribe(client, userdata, mid, granted_qos):
    pass
    #print("subscribed: " + str(mid) + " " + str(granted_qos))
    # 다중 Subscribe: subscribe([("topic1", 1), ("topic2", 1)])

def on_message(client, userdata, msg):
    #print(str(msg.payload.decode("utf-8")))
    payload = str(msg.payload.decode("utf-8"))
    if payload[0] == "#":
        message = payload.replace("#", "").split("|")
        if len(message) == 10:
            #print(message)
            try:
                device = Device(
                    device_code = message[0],
                    mode = int(message[1]),
                    status = int(message[2]),
                    light = int(message[3]),
                    speed = float(message[4]),
                    temperature = float(message[5]),
                    humidity = int(message[6]),
                    timer_unfold = f"{message[7][:2]}:{message[7][2:]}",
                    timer_fold = f"{message[8][:2]}:{message[8][2:]}",
                    device_time = f"{message[9][:2]}:{message[9][2:]}",
                    datetime = datetime.now()
                )
                device.save()
                # 기존: datetime = datetime.utcnow() + timedelta(hours=9)
                # 수정: datetime = datetime.now()
                #print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] => {message}")
                _LOGGER.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]{message}")
            except:
                pass


client = mqtt.Client(MQTT_CLIENT_ID)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_subscribe = on_subscribe
client.on_message = on_message

client.username_pw_set(MQTT_USERNAME, MQTT_USERPASSWD)
client.reconnect_delay_set(min_delay=1, max_delay=10)
client.connect(MQTT_BROKER_URL, MQTT_BROKER_PORT, keepalive=30)
#client.subscribe(MQTT_TOPIC, MQTT_QOS)
client.loop_forever()
