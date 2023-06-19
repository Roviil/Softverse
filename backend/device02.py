import logging
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta
from dataclasses import dataclass

stream_handler = logging.StreamHandler()
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(level=logging.INFO)
_LOGGER.addHandler(stream_handler)

DEVICE_CODE="device02"

MQTT_BROKER_URL = "127.0.0.1"
MQTT_BROKER_PORT = 1883
MQTT_CLIENT_ID = DEVICE_CODE
MQTT_USERNAME = "smarttec"
MQTT_USERPASSWD = "smarttec"
MQTT_TOPIC = f"cmd/{DEVICE_CODE}/remote/#"
MQTT_QOS = 0

@dataclass
class DEVICE:
    code:str
    mode:int
    status:int
    light:int
    speed:float
    temperature:float
    humidity:int
    timer_unfold:str
    timer_fold:str
    device_time:str

device = DEVICE(
    DEVICE_CODE, 0, 0, 0,
    7.2, 13.3, 50,
    "0900", "1700", "1300")

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

def publish_status():
    topic = "event/status"
    device.device_time = datetime.now().strftime('%H%M')
    message = f"#{'|'.join([str(value) for value in device.__dict__.values()])}#"
    #print(message)
    client.publish(topic, message)

def on_message(client, userdata, msg):
    topic = msg.topic.split("/")[-1]
    payload = str(msg.payload.decode("utf-8"))
    message = None
    if payload:
        message = payload.replace("#", "").split("|")[0]

    if topic == "status":
        publish_status()
        
    elif topic == "folding" and message:
        if message == "0":
            device.status = 0
        elif message == "1":
            device.status = 1
        else:
            pass
        publish_status()
        
    elif topic == "mode" and message:
        if message == "0":
            device.mode = 0
        elif message == "1":
            device.mode = 1
        else:
            pass
        publish_status()
        
    elif topic == "light" and message:
        if message == "0":
            device.light = 0
        elif message == "1":
            device.light = 1
        else:
            pass
        publish_status()
        
    else:
        pass

    _LOGGER.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]({topic}){payload}")


client = mqtt.Client(MQTT_CLIENT_ID)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_subscribe = on_subscribe
client.on_message = on_message

client.username_pw_set(MQTT_USERNAME, MQTT_USERPASSWD)
client.reconnect_delay_set(min_delay=1, max_delay=10)
client.connect(MQTT_BROKER_URL, MQTT_BROKER_PORT, keepalive=30)

client.loop_forever()
