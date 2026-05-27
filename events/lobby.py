from flask_socketio import emit, join_room, leave_room
from game.state import Player
from services.game_services import assign_roles
from flask import request


def register(socketio, lobby_service, debug_service, game_state, rolelist_registry, run_game_loop):

    def countdown(lobby_id):
        for i in range(10, -1, -1):
            socketio.emit("pregame_tick", {"seconds": i}, to=lobby_id)
            socketio.sleep(1)

        lobby = lobby_service.get_lobby(lobby_id)
        if not lobby:
            debug_service.log("game", f"countdown: lobby {lobby_id} missing at assignment time")
            return

        if lobby.get("custom_list") is not None:
            list_config = lobby["custom_list"]
        else:
            list_key    = lobby_service.get_vote_winner(lobby_id)
            list_config = rolelist_registry.get(list_key) if list_key else None

        try:
            assignments = assign_roles(lobby["players"], game_state.role_registry, list_config)
        except ValueError as e:
            debug_service.log("game", f"assign_roles failed for {lobby_id}: {e}")
            socketio.emit("game_error", {"message": str(e)}, to=lobby_id)
            return

        print(f"[DEBUG] Assignments: { {pnum: rd['name'] for pnum, rd in assignments.items()} }")
        print(f"[DEBUG] Player SIDs: { {p['player_number']: p['sid'] for p in lobby['players']} }")
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
            player.charges     = role_data["charges"]
            player.vote_weight = 1

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
            }, to=sid, namespace="/")

        game_state.phase        = "Day 1"
        game_state.phase_number = 1
        debug_service.log("game", f"Phase → Day 1, emitting game_start for {lobby_id}")

        coven_players = [p for p in game_state.players.values() if p.alignment == "coven"]
        coven_list    = [
            {"player_number": p.player_number, "nickname": p.nickname, "role": p.role}
            for p in coven_players
        ]

        for p in coven_players:
            socketio.emit("coven_reveal", {"coven": coven_list}, to=p.sid, namespace="/")
        socketio.start_background_task(run_game_loop, lobby_id)
        socketio.emit("pregame_end", {}, to=lobby_id)
        socketio.emit("game_start", {"lobby_id": lobby_id}, to=lobby_id)

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
        success  = lobby_service.lock_lobby(lobby_id, request.sid)

        debug_service.log("lobby", f"{request.sid} tried locking lobby {lobby_id}", {"success": success})

        if success:
            lobby   = lobby_service.get_lobby(lobby_id)
            players = lobby["players"] if lobby else []
            socketio.emit("lobby_list", lobby_service.list_lobbies())
            socketio.emit("pregame_start", {"players": players}, to=lobby_id)

    @socketio.on("unlock_lobby")
    def unlock_lobby(data):
        lobby_id = data.get("lobby_id")
        success  = lobby_service.unlock_lobby(lobby_id, request.sid)

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

    @socketio.on("request_rolelists")
    def request_rolelists():
        emit("rolelist_data", {
            key: {
                "name": val["name"],
                "description": val["description"]
            }
            for key, val in rolelist_registry.items()
        }, to=request.sid)

    @socketio.on("set_role_list")
    def set_role_list(data):
        lobby_id = data.get("lobby_id")
        list_key = data.get("list_key")

        if not lobby_id:
            return

        if list_key is not None and list_key not in rolelist_registry:
            emit("lobby_error", {"message": f"Unknown role list '{list_key}'."}, to=request.sid)
            return

        success = lobby_service.set_role_list(lobby_id, request.sid, list_key)

        if success:
            socketio.emit("role_list_updated", {
                "selected_list": list_key,
                "list_name":     rolelist_registry[list_key]["name"] if list_key else None,
                "is_custom":     False,
            }, to=lobby_id)
        else:
            emit("lobby_error", {"message": "Could not set role list."}, to=request.sid)

    @socketio.on("set_custom_role_list")
    def set_custom_role_list(data):
        lobby_id = data.get("lobby_id")
        config   = data.get("config") 

        if not lobby_id or not isinstance(config, dict):
            emit("lobby_error", {"message": "Invalid custom list payload."}, to=request.sid)
            return

        for section in ("town", "coven", "any"):
            slots = config.get(section, [])
            if not isinstance(slots, list):
                emit("lobby_error", {"message": f"Section '{section}' must be a list."}, to=request.sid)
                return
            for slot in slots:
                if "type" not in slot:
                    emit("lobby_error", {"message": "Every slot must have a 'type' field."}, to=request.sid)
                    return

        success = lobby_service.set_custom_list(lobby_id, request.sid, config)

        if success:
            total_slots = sum(
                len(config.get(s, [])) for s in ("town", "coven", "any")
            )
            socketio.emit("role_list_updated", {
                "selected_list": None,
                "list_name":     "Custom",
                "is_custom":     True,
                "slot_count":    total_slots,
                "config" : config,
            }, to=lobby_id)
        else:
            emit("lobby_error", {"message": "Could not set custom role list."}, to=request.sid)

    @socketio.on("rename_lobby")
    def rename_lobby(data):
        lobby_id = data.get("lobby_id")
        new_name = data.get("name", "").strip()

        if not lobby_id or not new_name:
            emit("lobby_error", {"message": "Name cannot be empty."}, to=request.sid)
            return

        success = lobby_service.rename_lobby(lobby_id, request.sid, new_name)

        if success:
            socketio.emit("lobby_renamed", {"name": new_name}, to=lobby_id)
            socketio.emit("lobby_list", lobby_service.list_lobbies())
        else:
            emit("lobby_error", {"message": "Could not rename lobby."}, to=request.sid)

    @socketio.on("kick_player")
    def kick_player(data):
        lobby_id      = data.get("lobby_id")
        target_number = data.get("player_number")

        if not lobby_id or target_number is None:
            return

        kicked_sid = lobby_service.kick_player(lobby_id, request.sid, target_number)

        if kicked_sid:
            lobby  = lobby_service.get_lobby(lobby_id)
            players = lobby["players"] if lobby else []
            emit("kicked", {"message": "You were removed from the lobby by the host."}, to=kicked_sid)
            leave_room(lobby_id, sid=kicked_sid)
            socketio.emit("player_list_update", {"players": players}, to=lobby_id)
            socketio.emit("lobby_list", lobby_service.list_lobbies())
            debug_service.log("lobby", f"Player #{target_number} kicked from {lobby_id} by host")
        else:
            emit("lobby_error", {"message": "Could not kick player."}, to=request.sid)

    @socketio.on("vote_role_list")
    def vote_role_list(data):
        lobby_id = data.get("lobby_id")
        list_key = data.get("list_key")

        if not lobby_id:
            return

        if list_key is not None and list_key not in rolelist_registry:
            emit("lobby_error", {"message": f"Unknown role list '{list_key}'."}, to=request.sid)
            return

        success = lobby_service.vote_role_list(lobby_id, request.sid, list_key)
        if success:
            tally = lobby_service.get_vote_tally(lobby_id)
            socketio.emit("vote_update", {"votes": tally}, to=lobby_id)