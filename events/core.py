from flask import request
from flask_socketio import emit, join_room

def register(socketio, lobby_service, debug_service, console, game_state):

    @socketio.on('connect')
    def handle_connect(auth=None):
        console.print(f"[CONNECT] Client connected: {request.sid}")
        debug_service.log("connect", f"Client connected: {request.sid}")

        emit('connection_ack', {'sid': request.sid, 'message': 'Connected to server'}, to=request.sid)
        socketio.emit("lobby_list", lobby_service.list_lobbies(), to=request.sid)

        if game_state.phase not in ("lobby", ""):
            emit("game_state_update", game_state.to_public_dict(), to=request.sid)
            emit("phase_change", {
                "phase":     game_state.phase,
                "sub_phase": game_state.sub_phase,
                "duration":  0,
            }, to=request.sid)

    @socketio.on('disconnect')
    def handle_disconnect(reason=None):
        console.print(
            f"[DISCONNECT] Client disconnected: {request.sid}"
        )

        debug_service.log(
            "disconnect",
            f"Client disconnected: {request.sid}"
        )

        lobby_service.remove_player(request.sid)

        socketio.emit(
            "lobby_list",
            lobby_service.list_lobbies()
        )

    @socketio.on("rejoin_game")
    def handle_rejoin_game(data):
        lobby_id      = data.get("lobby_id")
        player_number = data.get("player_number")
        if not lobby_id or game_state.lobby_id != lobby_id:
            return
        join_room(lobby_id)
        if player_number and player_number in game_state.players:
            game_state.players[player_number].sid = request.sid
            debug_service.log("game", f"Player #{player_number} rejoined with new SID {request.sid}")

    @socketio.on('ping_test')
    def handle_ping(data):
        console.print(
            f"[PING] SID: {request.sid} DATA: {data}"
        )

        debug_service.log(
            "ping",
            f"Ping from {request.sid}",
            data
        )

        emit(
            'pong_test',
            {'test': 'HELLO FROM SERVER'}
        )

        debug_service.log(
            "pong",
            "Pong sent"
        )