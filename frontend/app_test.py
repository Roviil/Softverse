"""

A small Test application to show how to use Flask-MQTT.

"""
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import logging
from datetime import datetime
import eventlet
import json
from flask import Flask, render_template, send_file
from flask_mqtt import Mqtt
from flask_socketio import SocketIO
from flask_bootstrap import Bootstrap
from flask_mongoengine import MongoEngine

from backend.model import *

eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET'] = 'secret_key'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['MQTT_BROKER_URL'] = '127.0.0.1'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_CLIENT_ID'] = 'flask-mqtt'
app.config['MQTT_CLEAN_SESSION'] = True
app.config['MQTT_USERNAME'] = 'smarttec'
app.config['MQTT_PASSWORD'] = 'smarttec'
app.config['MQTT_KEEPALIVE'] = 60
app.config['MQTT_TLS_ENABLED'] = False
#app.config['MQTT_LAST_WILL_TOPIC'] = 'home/lastwill'
#app.config['MQTT_LAST_WILL_MESSAGE'] = 'bye'
#app.config['MQTT_LAST_WILL_QOS'] = 1

# Parameters for SSL enabled
# app.config['MQTT_BROKER_PORT'] = 8883
# app.config['MQTT_TLS_ENABLED'] = True
# app.config['MQTT_TLS_INSECURE'] = True
# app.config['MQTT_TLS_CA_CERTS'] = 'ca.crt'

app.config['MONGODB_SETTINGS'] = {
    "db": "smarttec",
    "host": '127.0.0.1',
    "port": 27017,
    "username": "smarttec",
    "password": "smarttec",
    "authentication_source": "admin"
}

mqtt = Mqtt(app)
socketio = SocketIO(app)
bootstrap = Bootstrap(app)

db = MongoEngine(app)

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(level=logging.INFO)
file_handler = logging.FileHandler("logs/frontend_test-mqtt.log")
_LOGGER.addHandler(file_handler)


@app.route('/test')
def test():
    #devices = Device.objects()
    #print(devices)
    return render_template('test.html')

@app.route('/test/frontend_mqtt_log')
def frontend_mqtt_log():
    filename = './logs/frontend-mqtt.log'
    with open(filename, "r") as f:
        lines = f.readlines()
    contents = ""
    for line in lines:
        contents += line + "<br>"
    return contents

@app.route('/test/frontend_test_mqtt_log')
def frontend_test_mqtt_log():
    filename = './logs/frontend_test-mqtt.log'
    with open(filename, "r") as f:
        lines = f.readlines()
    contents = ""
    for line in lines:
        contents += line + "<br>"
    return contents
    
@app.route('/test/backend_log')
def backend_log():
    filename = '../backend/logs/backend.log'
    with open(filename, "r") as f:
        lines = f.readlines()
    contents = ""
    for line in lines:
        contents += line + "<br>"
    return contents    

@socketio.on('publish')
def handle_publish(json_str):
    print(json_str)
    data = json.loads(json_str)
    mqtt.publish(data['topic'], data['message'], data['qos'])
    _LOGGER.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][{data['topic']}]{data['message']}")


@socketio.on('subscribe')
def handle_subscribe(json_str):
    data = json.loads(json_str)
    mqtt.subscribe(data['topic'], data['qos'])


@socketio.on('unsubscribe_all')
def handle_unsubscribe_all():
    mqtt.unsubscribe_all()


@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    data = dict(
        topic=message.topic,
        payload=message.payload.decode(),
        qos=message.qos,
    )
    response_message = message.payload.decode().split("|")
    if len(response_message) == 8:
        response = f"\n => Device: {response_message[0]}"
        response += f"\n => Mode: {'수동' if response_message[1] == '1' else '자동'}"
        response += f"\n => Status: {'접힘' if response_message[2] == '1' else '펼침'}"
        response += f"\n => Speed: {response_message[3]}m/s"
        response += f"\n => Temperature: {response_message[4]}˚C"
        response += f"\n => Humidity: {response_message[5]}%"
        response += f"\n => Timer_unfold: {response_message[6][:2]}:{response_message[6][2:]}"
        response += f"\n => Timer_fold: {response_message[7][:2]}:{response_message[7][2:]}"
        data['payload'] += response
    socketio.emit('mqtt_message', data=data)


@mqtt.on_log()
def handle_logging(client, userdata, level, buf):
    #print(level, buf)
    pass


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, use_reloader=False, debug=True)
