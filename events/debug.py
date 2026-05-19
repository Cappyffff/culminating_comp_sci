from flask import request
from flask_socketio import emit


def register(socketio, debug_service):

    @socketio.on("debug_ping")
    def handle_ping(data):
        debug_service.log(
            "ping",
            f"Ping from {request.sid}"
        )

        emit(
            "pong_test",
            {"test": "HELLO FROM SERVER"},
            broadcast=True
        )

        debug_service.log(
            "pong",
            "Pong broadcasted"
        )