import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))


from datetime import datetime, timedelta
from typing import Optional
from mongoengine import DoesNotExist

from backend.model import *

from secrets import token_urlsafe
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_user():
    user_list = []
    for user in User.objects:
        user_data = {
            'id': user.username,
            'team': user.team,
        }
        user_list.append(user_data)
    return user_list

def generate_token(length: int = 32) -> str:
    # Generate a random token with the specified length
    token = token_urlsafe(length)
    return token

def create_session(user: User) -> str:
    # Generate unique session token
    token = generate_token()
    # Save session to database
    session = Session(token=token, user=user, created_at=datetime.now())
    session.save()

    return token

def get_session(token: str) -> Session:
    try:
        # Retrieve session from database by token
        session = Session.objects(token=token).get()
        # Check if session has expired
        if session.created_at < datetime.now() - timedelta(days=30):
            # Session has expired, delete it
            session.delete()
            return None
        return session
    except DoesNotExist:
        # Session not found
        #raise HTTPException(status_code=404, detail='Session not found')
        return None

def delete_session_token(token: str) -> None:
    session = Session.objects(token=token)
    if session:
        session.get().delete()

def get_session_list_by_user_id(user_id: str) -> Optional[Session]:
    try:
        # Retrieve session from database by user ID
        _id = User.objects(username=user_id).get()
        session_list = Session.objects(user=_id)
        return session_list
    except DoesNotExist:
        # Session not found
        return None

def delete_session_list(session_list: list) -> None:
    for session in session_list:
        delete_session_token(session.token)

def update_devices_list(session: Session, devices_list: list) -> bool:
    user = User.objects(username=session.user.username)
    device_object_list = []
    for device_code in devices_list:
        device = DeviceInfo.objects(device_code=device_code)
        if device:
            device_object_list.append(device.get())

    if user:
        r = user.get().modify(
            devices = device_object_list
        )
        return r

    return False

def get_devices_object_list(user: User):
    device_object_list = list()

    for device in user['devices']:
        cursor = Device.objects(device_code=device.device_code).order_by('-datetime').limit(1).aggregate(*[{
            '$lookup': {
                'from': DeviceInfo._get_collection_name(),
                'localField': 'device_code',
                'foreignField': 'device_code',
                'as': 'device_info'
            }},{
            '$unwind': {
                'path': '$device_info'
            }}])
        cursor_list = list(cursor)
        if cursor_list:
            #device_object_list.append(dumps(cursor_list[0], ensure_ascii=False))
            cursor_list[0]['datetime'] = cursor_list[0]['datetime'].strftime("%Y-%m-%d %H:%M:%S")
            device_object_list.append(cursor_list[0])
    return device_object_list


def get_all_devices_object_list():
    device_object_list = list()
    for device in DeviceInfo.objects:
        cursor = Device.objects(device_code=device.device_code).order_by('-datetime').limit(1).aggregate(*[{
            '$lookup': {
                'from': DeviceInfo._get_collection_name(),
                'localField': 'device_code',
                'foreignField': 'device_code',
                'as': 'device_info'
            }},{
            '$unwind': {
                'path': '$device_info'
            }}])
        cursor_list = list(cursor)
        if cursor_list:
            #device_object_list.append(dumps(cursor_list[0], ensure_ascii=False))
            cursor_list[0]['datetime'] = cursor_list[0]['datetime'].strftime("%Y-%m-%d %H:%M:%S")
            device_object_list.append(cursor_list[0])
    return device_object_list

def get_user_devices_object_list():
    user_object_list = []

    # Retrieve all documents from the device_info table
    device_info_list = DeviceInfo.objects()

    for device_info in device_info_list:
        users = device_info.user
        if users:
            user_data = {
                'device_code': device_info.device_code,
                'users': users  # Update the key to 'users' to reflect the attribute name
            }
            user_object_list.append(user_data)
        else:
            user_data = {
                'device_code': device_info.device_code,
                'users': "할당된 유저가 없습니다."
            }
            user_object_list.append(user_data)
    return user_object_list

def get_devices_object_by_token(token: str):
    cursor = Session.objects(token=token).aggregate(*[{
        '$lookup': {
            'from': User._get_collection_name(),
            'localField': 'user',
            'foreignField': '_id',
            'as': 'devices'
        }},{
        '$unwind': {
            'path': '$devices'
        }},{
        '$project': {
            '_id': 0,
            'devices': {
                '$map': {
                    'input': '$devices.devices',
                    'as': 'devices_list',
                    'in': {
                        'device_id': '$$devices_list'
                    }
                }
            },
        }},{
        '$lookup': {
            'from': DeviceInfo._get_collection_name(),
            'localField': 'devices.device_id',
            'foreignField': '_id',
            'as': 'devices'
        }}
        ])
    cursor_list = list(cursor)
    if cursor_list:
        return cursor_list[0]['devices']

def get_devices_status_by_devices_objects(device_object_list:list):
    result = list()
    for device_object in device_object_list:
        device = Device.objects(device_code=device_object['device_code']).order_by('-datetime').first()
        if device:
            device_data = {
                'device_code': device['device_code'],
                'mode': device['mode'],
                'status': device['status'],
                'light': device['light'],
                'speed': device['speed'],
                'temperature': device['temperature'],
                'humidity': device['humidity'],
                'timer_unfold': device['timer_unfold'],
                'timer_fold': device['timer_fold'],
                'device_time': device['device_time'],
                'datetime': device['datetime'].strftime("%Y-%m-%d %H:%M:%S"),
            }
            result.append(device_data)
    return result


if __name__ == '__main__':
    session_list = get_session_list_by_user_id(user_id="smarttec")
    #delete_session_list(session_list)
