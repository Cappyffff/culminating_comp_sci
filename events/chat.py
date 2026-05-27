from flask import request
from flask_socketio import emit
from services.chat_services import can_chat


def register(socketio, game_state, debug_service):

    @socketio.on("send_message")
    def handle_send_message(data):
        player = game_state.get_player_by_sid(request.sid)
        if not player:
            return

        allowed, reason = can_chat(player, game_state, chat_type="town")
        if not allowed:
            emit("chat_error", {"message": reason}, to=request.sid)
            return

        msg = (data.get("message") or "").strip()
        if not msg:
            return

        socketio.emit("chat_message", {
            "player_number": player.player_number,
            "nickname":      player.nickname,
            "message":       msg,
        })

    @socketio.on("coven_chat")
    def handle_coven_chat(data):
        player = game_state.get_player_by_sid(request.sid)
        if not player:
            return

        allowed, reason = can_chat(player, game_state, chat_type="coven")
        if not allowed:
            emit("chat_error", {"message": reason}, to=request.sid)
            return

        msg = (data.get("message") or "").strip()
        if not msg:
            return

        coven_sids = [
            p.sid for p in game_state.players.values()
            if p.alignment == "coven"
        ]
        for sid in coven_sids:
            socketio.emit("coven_message", {
                "player_number": player.player_number,
                "message":       msg,
            }, to=sid)

        debug_service.log("chat", f"Coven msg from #{player.player_number}: {msg}")