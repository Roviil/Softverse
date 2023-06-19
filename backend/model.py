from passlib.context import CryptContext
from mongoengine import *
from datetime import datetime, timedelta

HOST = '127.0.0.1'
PORT = 27017
USER_NAME = 'smarttec'
USER_PASSWD = 'smarttec'
AUTH_DB = 'admin'

connect(db='smarttec', host=HOST, port=PORT, username=USER_NAME, password=USER_PASSWD, authentication_source=AUTH_DB)

class Device(Document):
    device_code = StringField(required=True, max_length=100)
    mode = IntField(required=True)
    status = IntField(required=True)
    light = IntField(required=True)
    speed = FloatField()
    temperature = FloatField()
    humidity = IntField()
    timer_unfold = StringField(required=True, max_length=5)
    timer_fold = StringField(required=True, max_length=5)
    device_time = StringField(required=True, max_length=5)
    datetime = DateTimeField(default=datetime.utcnow() + timedelta(hours=9))

class DeviceInfo(Document):
    device_code = StringField(required=True, max_length=100, unique=True)
    device_name = StringField(required=True, max_length=100)
    user = ListField()

class User(Document):
    username = StringField(required=True, unique=True)
    password = StringField(required=True)
    team = StringField(required=True)
    devices = ListField(ReferenceField(DeviceInfo))

class Session(Document):
    token = StringField(required=True, unique=True)
    user = ReferenceField(User, required=True)
    created_at = DateTimeField(required=True)



if __name__ == '__main__':
    """
    device_info = DeviceInfo(
        device_code = 'device01',
        device_name = '테스트디바이스'
    )
    device_info.save()    
    """
    exit()
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def get_password_hash(password: str) -> str:

        return pwd_context.hash(password)


    user = User(
        username = 'smarttec',
        password = get_password_hash('smarttec')

    )
    #user.save()