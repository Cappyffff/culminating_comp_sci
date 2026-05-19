from collections import deque
from datetime import datetime

class DebugService:
    def __init__(self):
        self.logs = deque(maxlen=200)

    def log(self, event_type: str, message: str, data=None):
        self.logs.appendleft({
            "time": datetime.now().strftime("%H:%M:%S"),
            "type": event_type,
            "message": message,
            "data": data or {}
        })

    def get_logs(self):
        return list(self.logs)

    def get_lobby_data(self, lobby_service):
        lobbies = []

        for lobby_id, lobby in lobby_service.lobbies.items():
            players = []

            for idx, player in enumerate(lobby["players"]):
                players.append({
                    "player_number": player["player_number"],
                    "name": player["name"],
                    "username": player.get("username", player["name"]),
                    "sid": player["sid"],
                    "role": None
                })

            lobbies.append({
                "id": lobby_id,
                "locked": lobby["locked"],
                "role_list": lobby.get("role_list", []),
                "players": players
            })

        return lobbies