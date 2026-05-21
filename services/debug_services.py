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

    def get_game_data(self, game_state):
        if not game_state.players:
            return None

        players = []
        for p in game_state.players.values():
            players.append({
                "player_number": p.player_number,
                "sid": p.sid,
                "nickname": p.nickname,
                "role": p.role,
                "alignment": p.alignment,
                "alive": p.alive,
                "current_attack": p.current_attack,
                "current_defense": p.current_defense,
                "status_effects": p.status_effects,
            })

        return {
            "phase": game_state.phase,
            "phase_number": game_state.phase_number,
            "players": players,
        }