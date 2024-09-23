from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, Session
from passlib.context import CryptContext
from datetime import datetime
import json

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

DATABASE_URL = "sqlite:///./chat.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

connections = []
active_users = {}

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    messages = relationship("Message", back_populates="user")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    room = Column(String, index=True)
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="messages")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if user and pwd_context.verify(password, user.hashed_password):
        return user
    return None

def create_user(db: Session, username: str, password: str):
    hashed_password = pwd_context.hash(password)
    user = User(username=username, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.get("/")
async def index(request: Request):
    user = request.cookies.get("username")
    if user:
        return RedirectResponse(url="/rooms")
    return templates.TemplateResponse("login.html", {"request": request, "message": None})

@app.get("/register")
async def register_get(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "message": None})

@app.post("/register")
async def register_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "message": "Lietotājvārds jau eksistē."}
        )
    create_user(db, username, password)
    response = RedirectResponse(url="/rooms", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="username", value=username)
    return response

@app.post("/login")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "message": "Nepareizs lietotājvārds vai parole."}
        )
    response = RedirectResponse(url="/rooms", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="username", value=username)
    return response

@app.get("/rooms")
async def rooms(request: Request):
    username = request.cookies.get("username")
    if not username:
        return RedirectResponse(url="/")
    active_rooms = list(set(conn['room'] for conn in connections))
    return templates.TemplateResponse(
        "rooms.html",
        {"request": request, "username": username, "active_rooms": active_rooms}
    )

@app.get("/chat")
async def chat_get():
    return RedirectResponse(url="/rooms")

@app.post("/chat")
async def chat(request: Request, room: str = Form(...)):
    username = request.cookies.get("username")
    if not username:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(
        "chat.html",
        {"request": request, "room": room, "username": username}
    )

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie(key="username")
    return response

@app.websocket("/ws/{room}/{username}")
async def websocket_endpoint(
    websocket: WebSocket,
    room: str,
    username: str,
    db: Session = Depends(get_db)
):
    await websocket.accept()
    connections.append({"websocket": websocket, "username": username, "room": room})
    messages = db.query(Message).filter(Message.room == room).order_by(Message.timestamp).all()
    history = [
        {
            "timestamp": msg.timestamp.strftime('%H:%M:%S'),
            "username": msg.user.username if msg.user else None,
            "content": msg.content,
            "is_system": msg.user is None
        }
        for msg in messages
    ]
    await websocket.send_text(json.dumps({
        "event": "history",
        "messages": history
    }))
    timestamp = datetime.now().strftime('%H:%M:%S')
    connect_message = {
        "timestamp": timestamp,
        "username": None,
        "content": f"{username} pievienojās čatam",
        "is_system": True
    }
    new_message = Message(room=room, content=connect_message["content"], user_id=None)
    db.add(new_message)
    db.commit()
    await broadcast_message(json.dumps({"event": "message", "message": connect_message}), room)
    await send_user_list(room)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            if message_data["event"] == "message":
                message = message_data["message"]
                timestamp = datetime.now().strftime('%H:%M:%S')
                full_message = {
                    "timestamp": timestamp,
                    "username": username,
                    "content": message,
                    "is_system": False
                }
                user = db.query(User).filter(User.username == username).first()
                new_message = Message(room=room, content=message, user_id=user.id)
                db.add(new_message)
                db.commit()
                await broadcast_message(json.dumps({"event": "message", "message": full_message}), room)
            elif message_data["event"] == "typing":
                is_typing = message_data["typing"]
                typing_message = json.dumps({
                    "event": "typing",
                    "username": username,
                    "typing": is_typing
                })
                for conn in connections:
                    if conn["websocket"] != websocket and conn["room"] == room:
                        await conn["websocket"].send_text(typing_message)
    except WebSocketDisconnect:
        connections.remove(next(conn for conn in connections if conn["websocket"] == websocket))
        timestamp = datetime.now().strftime('%H:%M:%S')
        disconnect_message = {
            "timestamp": timestamp,
            "username": None,
            "content": f"{username} atstāja čatu",
            "is_system": True
        }
        new_message = Message(room=room, content=disconnect_message["content"], user_id=None)
        db.add(new_message)
        db.commit()
        await broadcast_message(json.dumps({"event": "message", "message": disconnect_message}), room)
        await send_user_list(room)
    except Exception as e:
        print(f"Kļūda: {e}")
        await websocket.close()

async def broadcast_message(message, room):
    for conn in connections:
        if conn["room"] == room:
            try:
                await conn["websocket"].send_text(message)
            except:
                pass

async def send_user_list(room):
    user_list = [conn['username'] for conn in connections if conn['room'] == room]
    message = json.dumps({"event": "user_list", "users": user_list})
    for conn in connections:
        if conn["room"] == room:
            await conn["websocket"].send_text(message)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
