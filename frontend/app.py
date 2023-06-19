import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect, HTTPException, Cookie, status, Depends, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates 
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_mqtt.fastmqtt import FastMQTT
from fastapi_mqtt.config import MQTTConfig
from db_control import *
from bson.json_util import loads
import asyncio
import logging
import pandas as pd
import json
from typing import Union, Any
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(level=logging.INFO)
file_handler = logging.FileHandler("logs/frontend-mqtt.log")
_LOGGER.addHandler(file_handler)

middleware = [
    Middleware(SessionMiddleware, secret_key='super-secret')
]
app = FastAPI(openapi_url="", middleware=middleware)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
mqtt_config = MQTTConfig()
mqtt_config.username = "smarttec"
mqtt_config.password = "smarttec"
fast_mqtt = FastMQTT(config=mqtt_config)
fast_mqtt.init_app(app)

MQTT_QOS = 1
#update_devices_list(session, ['device01', 'device02'])

def flash(request: Request, message: Any, category: str = "primary") -> None:
   if "_messages" not in request.session:
       request.session["_messages"] = []
       request.session["_messages"].append({"message": message, "category": category})

def get_flashed_messages(request: Request):
   return request.session.pop("_messages") if "_messages" in request.session else []

@app.get("/main", response_class=HTMLResponse)
async def main(request: Request, token: Union[str, None] = Cookie(default=None)):
    messages = get_flashed_messages(request)
    session = get_session(token)
    if not session:
        response = RedirectResponse('/', status_code=303)
        response.delete_cookie("token")
        return response

    user = User.objects(username=session.user.username).get()
    user_team = user.team # 로그인 유저의 소속을 가져옴

    if user.username == "smarttec":
        device_object_list = get_all_devices_object_list()
        return templates.TemplateResponse("adminpage.html", {"request": request, "device_object_list": device_object_list, "messages": messages})
    else:
        device_object_list = get_devices_object_list(user)
        return templates.TemplateResponse("main.html", {"request": request, "device_object_list": device_object_list, "user_team": user_team, "messages": messages})



@app.get("/adminpage") #관리자 메인 페이지 이동
async def adminpage(request: Request, token: Union[str, None] = Cookie(default=None)):
    messages = get_flashed_messages(request)

    session = get_session(token)
    user = User.objects(username=session.user.username).get()
    if user.username != "smarttec":
        device_object_list = get_devices_object_list(user) #전체 디바이스 가져오기
        return templates.TemplateResponse("main.html", {"request": request, "device_object_list": device_object_list, "messages": messages})

    return templates.TemplateResponse("adminpage.html", {"request": request, "messages": messages})

@app.post("/reset") #관리자 비밀번호 최기화
async def reset(request: Request, user_id: str = Form(...)):
    # 폼 데이터에서 username과 password 가져오기
    user = User.objects(username=user_id).first()#초기화 하는 유저 정보 가져오기
    password = 1234
    # 사용자 이름과 비밀번호를 해시화하여 저장합니다.
    hashed_password = get_password_hash(str(password))
    user.password = hashed_password
    user.save()
    flash(request, message="비밀번호가 성공적으로 변경되었습니다.", category="success")
    response = RedirectResponse("/usercontrol", status_code=status.HTTP_302_FOUND)
    return response
@app.get("/usercontrol") #유저 관리 페이지 이동
async def adminpage(request: Request, token: Union[str, None] = Cookie(default=None)):
    messages = get_flashed_messages(request)
    session = get_session(token)
    user = User.objects(username=session.user.username).get()

    if user.username == "smarttec":
        get_all_user = get_user() #전체 유저 정보 조회
        return templates.TemplateResponse("dashboard/usercontrol.html", {"request": request, "get_all_user": get_all_user, "messages": messages})
    else:# 관리자가 아닌 경우 강제로 메인 페이지로 이동
        device_object_list = get_devices_object_list(user)
        return templates.TemplateResponse("main.html", {"request": request, "device_object_list": device_object_list, "messages": messages})

@app.get("/devicemodify") #디아비으 수정 및 추가 페이지 이동
async def adminpage(request: Request, token: Union[str, None] = Cookie(default=None)):
    messages = get_flashed_messages(request)
    session = get_session(token)
    user = User.objects(username=session.user.username).get()
    device_object_list = get_all_devices_object_list() # 전체 디바이스 정보 조회

    if user.username == "smarttec":
        return templates.TemplateResponse("dashboard/devicemodify.html", {"request": request, "device_object_list": device_object_list, "messages": messages})
    else:
        device_object_list = get_devices_object_list(user)
        return templates.TemplateResponse("main.html", {"request": request, "device_object_list": device_object_list, "messages": messages})

@app.post("/deviceupdate") #디바이스 정보 수정(풍속, 펴는 시간, 접는 시간)
async def update_device(request: Request, device_code: str = Form(...), speed: str = Form(...), timer_unfold: str = Form(...), timer_fold: str = Form(...)):
    device = Device.objects(device_code = device_code).first()
    device.speed = float(speed)
    device.timer_unfold = timer_unfold
    device.timer_fold = timer_fold
    device.save()
    flash(request, message="정보가 수정되었습니다", category="success")
    response = RedirectResponse("/devicemodify", status_code=status.HTTP_302_FOUND)
    return response

@app.get('/', response_class=HTMLResponse)
async def root(request: Request, token: Union[str, None] = Cookie(default=None), msg: str = None):
    #return "서버 작업 중"
    messages = get_flashed_messages(request)
        
    if token:
        session = get_session(token)
        if session:
            response = RedirectResponse('/main', status_code=status.HTTP_302_FOUND)
            return response

    return templates.TemplateResponse("login.html", {"request": request, "messages": messages})

@app.post('/login')
async def login_post(request: Request, token: Union[str, None] = Cookie(default=None), data: OAuth2PasswordRequestForm = Depends()):

    if token:
        session = get_session(token)
        if session:
            response = RedirectResponse('/main', status_code=status.HTTP_302_FOUND)
            return response

            
    user = User.objects(username=data.username).first()
    #hashed_password = get_password_hash(data.password)

    if user and verify_password(data.password, user.password):
        # Valid credentials, create session
        session_token = create_session(user)
        #response.set_cookie(key="token", value=session_token, httponly=True, secure=True)
        
        response = RedirectResponse('/main', status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="token", value=session_token, httponly=True)
        return response
    else:
        # Invalid credentials
        flash(request, message="로그인에 실패하였습니다.", category="danger")
        response = RedirectResponse('/', status_code=status.HTTP_302_FOUND)
        return response
        raise HTTPException(status_code=401, detail='Invalid username or password')

@app.get("/singup") #회원가입 페이지 이동
async def singup(request: Request, token: Union[str, None] = Cookie(default=None), msg: str = None):
    messages = get_flashed_messages(request)

    if token:
        session = get_session(token)
        if session:
            response = RedirectResponse('/main', status_code=status.HTTP_302_FOUND)
            return response

    return templates.TemplateResponse("singup.html", {"request": request, "messages": messages})
@app.post("/singups") #회원가입 정보 DB로 전송
async def signup(request: Request, username: str = Form(...), password: str = Form(...), team: str = Form(...)):

    # 사용자 이름과 비밀번호를 해시화하여 저장합니다.
    hashed_password = get_password_hash(password)
    user = User(username=username, password=hashed_password, team=team)
    user.save()

    flash(request, message="회원가입이 완료되었습니다. 로그인하세요.", category="success")
    response = RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    return response

@app.post("/update/password") #비밀번호 업데이트
async def update_password(request: Request, token: Union[str, None] = Cookie(default=None), currentPassword: str = Form(...), newPassword: str = Form(...), confirmPassword: str =Form(...)):
    session = get_session(token)

    if not session:
        # 세션이 없는 경우 로그인되지 않은 상태
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    # 사용자 객체 가져오기
    user = User.objects(username=session.user.username).first()
    if not user:
        # 사용자를 찾을 수 없는 경우
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    #비밀번호 일치 여부 확인
    current_password_list = {"currentPassword" : currentPassword}
    new_password_list = {"newPassword" : newPassword}
    confirm_password_list = {"confirmPassword" : confirmPassword}
    current_password = list(current_password_list.values())[0]
    new_password = list(new_password_list.values())[0]
    confirm_password = list(confirm_password_list.values())[0]
    if not verify_password(current_password, user.password):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 일치하지 않습니다.")
    if confirm_password != new_password:
        raise HTTPException(status_code=400, detail="비밀번호가 일치하지 않습니다.")

    # 새로운 비밀번호로 업데이트
    hashed_password = get_password_hash(new_password)
    user.password = hashed_password
    user.save()

    flash(request, message="비밀번호가 성공적으로 변경되었습니다.", category="success")

    response = RedirectResponse("/main", status_code=status.HTTP_302_FOUND)
    return response

@app.post("/update/team") #소속정보 업데이트
async def update_team(request: Request, token: Union[str, None] = Cookie(default=None), newTeam: str = Form(...) ):
    session = get_session(token)

    if not session:
        # 세션이 없는 경우 로그인되지 않은 상태
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    # 사용자 객체 가져오기
    user = User.objects(username=session.user.username).first()
    if not user:
        # 사용자를 찾을 수 없는 경우
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    # 새로운 소속정보로 업데이트
    user.team = newTeam
    user.save()

    flash(request, message="소속정보가 성공적으로 변경되었습니다.", category="success")
    response = RedirectResponse("/main", status_code=status.HTTP_302_FOUND)
    return response

@app.post("/user/delete") #유저 정보 삭제
async def update_password(request: Request, user_id: str = Form(...)):
    #유저 정보 가져오기
    user = User.objects(username=user_id).first()
    #유저 삭제
    user.delete()
    flash(request, message="계정이 삭제되었습니다!", category="success")
    response = RedirectResponse("/usercontrol", status_code=status.HTTP_302_FOUND)
    return response

@app.get("/settingpage") #디바이스 할당 페이지 이동
async def singup(request: Request):
    messages = get_flashed_messages(request)
    #디바이스 정보 및 디바이스에 할당 된 유저, 전체 유저 조회
    device_object_list = get_all_devices_object_list()
    user_list = get_user_devices_object_list()
    get_all_user = get_user() 
    return templates.TemplateResponse("dashboard/index.html", {"request": request, "device_object_list": device_object_list, "user_list": user_list, "get_all_user": get_all_user, "messages": messages})

@app.post("/settingpage/mapping") #디바이스 할당
async def singup(deviceCode1: str = Form(...), selected_users: str = Form(...)):
    user = User.objects(username=selected_users).get() #유저 정보 조회
    device = DeviceInfo.objects.get(device_code=deviceCode1)  # 기존 device 조회
    device.user.append(selected_users)# device에 유저 추가
    device.save()
    user.devices.append(device.id) #user에 디바이스 추가
    user.save()
    response = RedirectResponse("/settingpage", status_code=status.HTTP_302_FOUND)
    return response

@app.post("/settingpage/unassign") # 디바이스 할당 해제
async def unassign(request: Request, deviceCode2: str = Form(...), selected_users: str = Form(...)):
    if selected_users == "할당된 유저가 없습니다.":
        flash(request, message="할당된 유저가 없습니다.", category="danger")
        response = RedirectResponse("/settingpage", status_code=status.HTTP_302_FOUND)
        return response
    user = User.objects(username=selected_users).get()
    device = DeviceInfo.objects.get(device_code=deviceCode2)  # 기존 device 조회
    device.user.remove(selected_users)  # device에서 유저 삭제
    device.save()
    user.devices.remove(device)  # user에서 디바이스 삭제
    user.save()
    response = RedirectResponse("/settingpage", status_code=status.HTTP_302_FOUND)
    return response

@app.post("/upload") #엑셀파일 업로드시 디바이스 정보 DB로 전송
async def upload(request: Request, file: UploadFile = File(...)):
    try:
        contents = await file.read()

        # 엑셀 파일 읽기
        df = pd.read_excel(contents)


        # 필요한 열만 선택
        json_data = df.to_json(orient='records')
        data = json.loads(json_data)


        # 데이터베이스에 저장
        device_code = data[0]["device_code"]
        device_name = data[0]["device_name"]
        device = DeviceInfo(device_code = device_code, device_name = device_name)
        device_insert = Device(device_code = device_code, mode = 1, status = 0, light = 0, speed = 1.0, temperature = 1.5, humidity = 1, timer_unfold = "13:00", timer_fold = "19:00", device_time ="13:00")
        device_insert.save()
        device.save()


        flash(request, message="디바이스 정보가 성공적으로 업로드 되었습니다.", category="success")
        response = RedirectResponse("/devicemodify", status_code=status.HTTP_302_FOUND)
        return response
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "디바이스 정보 업로드에 실패했습니다."})

@app.get("/download") #엑셀파일 업로드시 사용하는 양식의 예제 엑셀파일을 다운로드 가능
async def download():
    targetFile = "/home/smarttec/workspace/smarttec/frontend/example.xlsx"
    return FileResponse(path=targetFile, filename="example.xlsx", media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.get("/logout")
async def logout(request: Request, token: Union[str, None] = Cookie(default=None)):
    if token:
        delete_session_token(token)
    
    response = RedirectResponse('/', status_code=303)
    response.delete_cookie("token")
    return response

async def make_mqtt_publish_all_devices(devices_object_list, cmd, message):       
    for device in devices_object_list:
        if cmd == "folding":
            topic = f"cmd/{device['device_code']}/remote/folding"
        elif cmd == "mode":
            topic = f"cmd/{device['device_code']}/remote/mode"
        else:
            continue
        await mqtt_publish(topic, message)
        
async def make_mqtt_publish_device(device_code, cmd, message):       
    if cmd == "folding":
        topic = f"cmd/{device_code}/remote/folding"
    elif cmd == "mode":
        topic = f"cmd/{device_code}/remote/mode"
    elif cmd == "light":
        topic = f"cmd/{device_code}/remote/light"
    # 2023.05.01. Refresh 주석
    #elif cmd == "refresh":
    #    topic = f"cmd/{device_code}/remote/status"
    await mqtt_publish(topic, message)

async def mqtt_publish(topic: str, message: str):
    #print("##> ", topic, message)
    _LOGGER.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][{topic}]{message}")
    fast_mqtt.publish(topic, message, MQTT_QOS)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        await websocket.close()
        self.active_connections.remove(websocket)

    # websocket에 연결된 특정 소켓에게 메시지 전송
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    # websocket에 연결된 전체에게 메시지 전송
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

async def get_status_from_devices(websocket: WebSocket, devices_object_list:list, past_status: Union[list, None]):
    await asyncio.sleep(2)
    devices_status = get_devices_status_by_devices_objects(devices_object_list)
    if devices_status == past_status:
        return devices_status    
    else:
        await websocket.send_json(devices_status)
        return devices_status

async def recieve_message(websocket: WebSocket):
    data = await websocket.receive_text()
    json_data = loads(data)
    if json_data['cmd'] == "all_unfolding":
        # 일괄펴기 #1#
        devices_object_list = get_devices_object_by_token(websocket._cookies['token'])
        await make_mqtt_publish_all_devices(devices_object_list, cmd="folding", message="#1#")
    elif json_data['cmd'] == "all_folding":
        # 일괄접기 #0#
        devices_object_list = get_devices_object_by_token(websocket._cookies['token'])
        await make_mqtt_publish_all_devices(devices_object_list, cmd="folding", message="#0#")
    elif json_data['cmd'] == "all_auto":
        # 일괄자동 #1#
        devices_object_list = get_devices_object_by_token(websocket._cookies['token'])
        await make_mqtt_publish_all_devices(devices_object_list, cmd="mode", message="#1#")
    elif json_data['cmd'] == "all_manual":
        # 일괄수동 #0#
        devices_object_list = get_devices_object_by_token(websocket._cookies['token'])
        await make_mqtt_publish_all_devices(devices_object_list, cmd="mode", message="#0#")
    elif json_data['cmd'] == "folding" or json_data['cmd'] == "mode" or json_data['cmd'] == "light":
        # 단일 단말기 접기/펼침 or 자동/수동
        # folding : False - 접힘(0), True - 펼침(1)
        # mode : False - 수동(0), True - 자동(1)
        # light : False - 꺼짐(0), True - 켜짐(1)
        message = "#1#" if json_data['message'] else "#0#"
        await make_mqtt_publish_device(json_data['device_code'], cmd=json_data['cmd'], message=message)
    # 2023.05.01. Refresh 주석
    #elif json_data['cmd'] == "refresh":
    #    message = ""
    #    await make_mqtt_publish_device(json_data['device_code'], cmd=json_data['cmd'], message=message)
    

manager = ConnectionManager()

@app.websocket("/api/websocket")
async def websocket(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        devices_object_list = get_devices_object_by_token(websocket._cookies['token'])
    except:
        manager.disconnect(websocket)
        return

    past_status = None 
    try:
        while True:
            get_status_task = asyncio.create_task(get_status_from_devices(websocket, devices_object_list, past_status), name="get_status_task")
            recive_message_task = asyncio.create_task(recieve_message(websocket))

            done, pending = await asyncio.wait(
                {get_status_task, recive_message_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            for task in done:
                if task.get_name() == "get_status_task":
                    past_status = task.result()
                else:
                    task.result()

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        return
