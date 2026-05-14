from gevent import monkey
monkey.patch_all()
# NOTHING GOES ABOVE THESE TWO LINES

import socket

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from rich.console import Console
from rich.panel import Panel
from services.lobby_services import LobbyService

lobby_service = LobbyService()
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
local_ip = s.getsockname()[0]
s.close()
app = Flask(__name__)
app.config['SECRET_KEY'] = 'RLRY2JRG'

console = Console()
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins='*')

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/lobby")
def lobby():
    return render_template("lobby.html")

@socketio.on('connect')
def handle_connect(auth=None):
    console.print(Panel(
        f"Client connected: {request.sid}",
        title="CONNECT",
        style="green"
    ))
    emit('connection_ack', {'sid': request.sid, 'message': 'Connected to server'})
    socketio.emit(
        "lobby_list",
        lobby_service.list_lobbies(),
        to=request.sid
    )
@socketio.on('disconnect')
def handle_disconnect(reason=None):   
    console.print(Panel(
        f"Client disconnected: {request.sid}",
        title="DISCONNECT",
        style="red"
    ))

    lobby_service.remove_player(request.sid)

    socketio.emit(
    "lobby_list",
    lobby_service.list_lobbies()
)

@socketio.on("create_lobby")
def create_lobby(data):
    lobby_service.create_lobby(
        request.sid,
        data.get("name", "Host")
    )

    socketio.emit(
    "lobby_list",
    lobby_service.list_lobbies()
)

@socketio.on("join_lobby")
def join_lobby(data):
    lobby_service.join_lobby(
        data["lobby_id"],
        request.sid,
        data.get("name", "Guest")
    )

    socketio.emit(
    "lobby_list",
    lobby_service.list_lobbies()
)

@socketio.on('ping_test')
def handle_ping(data):
    console.print(Panel(
        f"SID: {request.sid}\nDATA: {data}",
        title="PING",
        style="yellow"
    ))
    emit('pong_test', {'test': 'HELLO FROM SERVER'}, broadcast=True)
    print("Pong Sent")

if __name__ == '__main__':
    console.clear()

    try:
        print("Server starting on http://0.0.0.0:5001")
        print(" * Serving Flask app 'server'")
        print(" * Debug mode: on")
        console.print("[bold #FA5787]WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.[/bold #FA5787]")
        print(" * Running on all addresses (0.0.0.0)")
        print(" * Running on http://127.0.0.1:5001")
        print(f" * Running on http://{local_ip}:5001")
        console.print("[bold #FFC000]Press CTRL+C to quit[/bold #FFC000]")
        socketio.run(app, host='0.0.0.0', port=5001, debug=True, use_reloader=False)


    except KeyboardInterrupt:
        console.print(Panel(
            f"Server Shutting Down: Keyboard Interrupt",
            title="ERROR",
            style="#FFA500"
        ))