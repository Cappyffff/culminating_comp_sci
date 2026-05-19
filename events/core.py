from flask import request
from flask_socketio import emit

def register(socketio, lobby_service, debug_service, console):

    @socketio.on('connect')
    def handle_connect(auth=None):
        console.print(
            f"[CONNECT] Client connected: {request.sid}"
        )

        debug_service.log(
            "connect",
            f"Client connected: {request.sid}"
        )

        emit(
            'connection_ack',
            {
                'sid': request.sid,
                'message': 'Connected to server'
            },
            to=request.sid
        )

        socketio.emit(
            "lobby_list",
            lobby_service.list_lobbies(),
            to=request.sid
        )

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