from gevent import monkey
monkey.patch_all()
# NOTHING GOES ABOVE THESE TWO LINES

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from rich.console import Console
from rich.panel import Panel
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'RLRY2JRG'

console = Console()
lobbies = {}
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins='*')

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/lobby")
def lobby():
    return render_template("lobby.html")

def emit_lobby_list():
    emit("lobby_list", [
        {
            "id": lid,
            "host": lobby["host"],
            "players": len(lobby["players"]),
            "player_names": [p["name"] for p in lobby["players"]]
        }
        for lid, lobby in lobbies.items()
    ], broadcast=True, namespace='/')

def emit_lobby_list_to_client(sid):
    emit("lobby_list", [
        {
            "id": lid,
            "host": lobby["host"],
            "players": len(lobby["players"]),
            "player_names": [p["name"] for p in lobby["players"]]
        }
        for lid, lobby in lobbies.items()
    ], to=sid, namespace='/')

@socketio.on('connect')
def handle_connect():
    console.print(Panel(
        f"Client connected: {request.sid}",
        title="CONNECT",
        style="green"
    ))
    emit('connection_ack', {'sid': request.sid, 'message': 'Connected to server'})
    emit_lobby_list_to_client(request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    console.print(Panel(
        f"Client disconnected: {request.sid}",
        title="DISCONNECT",
        style="red"
    ))

    for lid in list(lobbies.keys()):
        if request.sid in lobbies[lid]["players"]:
            lobbies[lid]["players"].remove(request.sid)
        if len(lobbies[lid]["players"]) == 0:
            del lobbies[lid]

    emit_lobby_list()

@socketio.on("create_lobby")
def create_lobby(data):
    lobby_id = str(uuid.uuid4())

    lobbies[lobby_id] = {
        "host": data.get("name", "Host"),
        "players": [{"sid": request.sid, "name": data.get("name", "Host")}]
    }

    emit_lobby_list()

@socketio.on("join_lobby")
def join_lobby(data):
    lobby_id = data["lobby_id"]
    username = data.get("name", "Guest")

    if lobby_id in lobbies:
        if not any(p['sid'] == request.sid for p in lobbies[lobby_id]["players"]):
            lobbies[lobby_id]["players"].append({"sid": request.sid, "name": username})

    emit_lobby_list()

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
    print("Server starting on http://0.0.0.0:5001")
    print(" * Serving Flask app 'server'")
    print(" * Debug mode: on")
    console.print("[bold #FA5787]WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.[/bold #FA5787]")
    print(" * Running on all addresses (0.0.0.0)")
    print(" * Running on http://127.0.0.1:5001")
    print(" * Running on http://10.5.10.114:5001")
    console.print("[bold #FFC000]Press CTRL+C to quit[/bold #FFC000]")
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, use_reloader=False)