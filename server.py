from gevent import monkey
monkey.patch_all()
# NOTHING GOES ABOVE THESE TWO LINES

import socket
import os

from dotenv import load_dotenv
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO
from rich.console import Console
from rich.panel import Panel
from services.lobby_services import LobbyService
from services.debug_services import DebugService
from game.rolelists import load_rolelist_registry
from game.state import GameState, Player
from game.roles import load_role_registry
from config import Config
from network import LANDiscovery
from events import debug as debug_events
from events import lobby as lobby_events
from events import core as core_events
from events import game as game_events
from events import chat as chat_events

lobby_service = LobbyService()
game_state = GameState()
game_state.role_registry = load_role_registry()
discovery = None
debug_service = DebugService()
rolelist_registry = load_rolelist_registry("data/rolelists.toml")

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
local_ip = s.getsockname()[0]
s.close()

app = Flask(__name__)
app.config.from_object(Config)

console = Console()
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins='*')

run_game_loop = game_events.register(socketio, game_state, debug_service)

chat_events.register(socketio, game_state, debug_service)
debug_events.register(socketio, debug_service)
lobby_events.register(socketio, lobby_service, debug_service, game_state, rolelist_registry, run_game_loop)
core_events.register(socketio, lobby_service, debug_service, console, game_state)

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/lobby")
def lobby():
    return render_template("lobby.html")

@app.route("/game")
def game():
    return render_template("game.html")

@app.route("/debug")
def debug():
    key = request.args.get("key")
    authenticated = key == app.config["SECRET_KEY"]

    return render_template(
        "debug.html",
        secret_key=key if authenticated else None,
        authenticated=authenticated
    )

@app.route("/api/debug")
def api_debug():
    key = request.args.get("key")

    if key != app.config["SECRET_KEY"]:
        return jsonify({"error": "Unauthorized"}), 401

    return jsonify({
        "logs": debug_service.get_logs(),
        "lobbies": debug_service.get_lobby_data(lobby_service),
        "game": debug_service.get_game_data(game_state),
        "audit": getattr(debug_service, "get_audit", lambda: [])()
    })

@app.route("/api/debug/reveal-role")
def reveal_role():
    key = request.args.get("key")
    sid = request.args.get("sid")

    if key != app.config["SECRET_KEY"]:
        return jsonify({"error": "Unauthorized"}), 401

    player = game_state.get_player_by_sid(sid)
    if player and player.role:
        return jsonify({"role": player.role})

    for lobby in lobby_service.lobbies.values():
        for p in lobby["players"]:
            if p["sid"] == sid:
                return jsonify({"role": p.get("role") or "No role yet"})

    return jsonify({"error": "Not found"}), 404

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
        discovery = LANDiscovery("cappyffff", 5001)
        discovery.start()
        socketio.run(app, host='0.0.0.0', port=5001, debug=True, use_reloader=False)

    except KeyboardInterrupt:
        console.print(Panel(
            f"Server Shutting Down: Keyboard Interrupt",
            title="ERROR",
            style="#FFA500"
            
        ))

    finally:
        if discovery:
            discovery.stop()
        if not KeyboardInterrupt:
            console.print(Panel(
                "Server Shutting Down",
                title="ERROR",
                style="#FFA500"
        ))