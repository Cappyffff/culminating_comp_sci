from flask_socketio import emit, join_room, leave_room
from game.state import Player
from services.game_services import assign_roles
from flask import request


def register(socketio, lobby_service, debug_service, game_state):

    def countdown(lobby_id):
        for i in range(10, -1, -1):
            socketio.emit("pregame_tick", {"seconds": i}, to=lobby_id)
            socketio.sleep(1)

        lobby = lobby_service.get_lobby(lobby_id)
        if not lobby:
            debug_service.log("game", f"countdown: lobby {lobby_id} missing at assignment time")
            return

        assignments = assign_roles(lobby["players"], game_state.role_registry)
        debug_service.log("game", f"Roles assigned for {lobby_id}",
                        {pnum: rd["name"] for pnum, rd in assignments.items()})

        for player_data in lobby["players"]:
            pnum      = player_data["player_number"]
            sid       = player_data["sid"]
            role_data = assignments[pnum]

            player = Player(pnum, sid, player_data["name"])
            player.role             = role_data["name"]
            player.alignment        = role_data["faction"]
            player.base_attack      = role_data["attack"]
            player.base_defense     = role_data["defense"]
            player.current_attack   = role_data["attack"]
            player.current_defense  = role_data["defense"]
            player.roleblock_immune = role_data["roleblock_immune"]
            player.control_immune   = role_data["control_immune"]
            game_state.players[pnum] = player

            socketio.emit("role_assigned", {
                "player_number":       pnum,
                "nickname":            player.nickname,
                "role":                role_data["name"],
                "alignment":           player.alignment,
                "faction":             role_data["faction"],
                "category":            role_data["category"],
                "attack":              player.current_attack,
                "defense":             player.current_defense,
                "ability_type":        role_data["ability_type"],
                "ability_description": role_data["ability_description"],
                "charges":             role_data["charges"],
                "unique":              role_data["unique"],
                "astral":              role_data["astral"],
                "roleblock_immune":    role_data["roleblock_immune"],
                "control_immune":      role_data["control_immune"],
            }, to=sid)

        game_state.phase        = "Day 1"
        game_state.phase_number = 1
        debug_service.log("game", f"Phase → Day 1, emitting game_start for {lobby_id}")

        socketio.emit("pregame_end", {}, to=lobby_id)
        socketio.emit("game_start",  {}, to=lobby_id)

    @socketio.on("create_lobby")
    def create_lobby(data):
        lobby_id = lobby_service.create_lobby(
            request.sid,
            data.get("name", "Host"),
            data.get("lobby_name"),
            data.get("username")
        )

        if lobby_id is None:
            emit("lobby_error", {"message": "You already have an open lobby."}, to=request.sid)
            return

        join_room(lobby_id)
        debug_service.log("lobby", f"Lobby created by {request.sid}", {"lobby_id": lobby_id})
        socketio.emit("lobby_list", lobby_service.list_lobbies())
        emit("lobby_created", {"lobby_id": lobby_id}, to=request.sid)

    @socketio.on("join_lobby")
    def join_lobby(data):
        lobby_service.join_lobby(data["lobby_id"], request.sid, data.get("name", "Guest"), data.get("username"))
        join_room(data["lobby_id"])

        debug_service.log("lobby", f"{request.sid} joined lobby {data['lobby_id']}")
        socketio.emit("lobby_list", lobby_service.list_lobbies())
        emit("lobby_joined", {"lobby_id": data["lobby_id"]}, to=request.sid)

    @socketio.on("leave_lobby")
    def leave_lobby(data):
        lobby_id = None
        for lid, lobby in lobby_service.lobbies.items():
            if any(p["sid"] == request.sid for p in lobby["players"]):
                lobby_id = lid
                break

        lobby_service.remove_player(request.sid)

        if lobby_id:
            leave_room(lobby_id)

        debug_service.log("lobby", f"{request.sid} left their lobby")
        socketio.emit("lobby_list", lobby_service.list_lobbies())
        emit("lobby_left", {}, to=request.sid)

    @socketio.on("request_lobbies")
    def request_lobbies():
        debug_service.log("lobby", f"{request.sid} requested lobby list")
        socketio.emit("lobby_list", lobby_service.list_lobbies(), to=request.sid)

    @socketio.on("lock_lobby")
    def lock_lobby(data):
        lobby_id = data["lobby_id"]
        success = lobby_service.lock_lobby(lobby_id, request.sid)

        debug_service.log("lobby", f"{request.sid} tried locking lobby {lobby_id}", {"success": success})

        if success:
            lobby = lobby_service.get_lobby(lobby_id)
            players = lobby["players"] if lobby else []
            socketio.emit("lobby_list", lobby_service.list_lobbies())
            socketio.emit("pregame_start", {"players": players}, to=lobby_id)

    @socketio.on("unlock_lobby")
    def unlock_lobby(data):
        lobby_id = data.get("lobby_id")
        success = lobby_service.unlock_lobby(lobby_id, request.sid)

        if success:
            socketio.emit("lobby_list", lobby_service.list_lobbies())
            socketio.emit("lobby_unlocked", {}, to=lobby_id)

    @socketio.on("start_game")
    def start_game(data):
        lobby_id = data.get("lobby_id")
        if not lobby_id:
            return

        lobby = lobby_service.get_lobby(lobby_id)
        if not lobby or lobby["host_sid"] != request.sid:
            return

        socketio.start_background_task(countdown, lobby_id)

    @socketio.on("submit_nickname")
    def submit_nickname(data):
        lobby_id = data.get("lobby_id")
        nickname = data.get("nickname", "").strip()

        if not nickname or not lobby_id:
            return

        lobby = lobby_service.get_lobby(lobby_id)
        if not lobby:
            return

        for p in lobby["players"]:
            if p["sid"] == request.sid:
                p["name"] = nickname
                break

        socketio.emit("player_list_update", {"players": lobby["players"]}, to=lobby_id)