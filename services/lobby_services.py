import uuid


class LobbyService:
    def __init__(self):
        self.lobbies = {}

    def create_lobby(self, sid, name):
        lobby_id = str(uuid.uuid4())

        self.lobbies[lobby_id] = {
            "host": name,
            "players": [{"sid": sid, "name": name}]
        }

        return lobby_id

    def join_lobby(self, lobby_id, sid, name):
        if lobby_id not in self.lobbies:
            return False

        lobby = self.lobbies[lobby_id]

        if not any(p["sid"] == sid for p in lobby["players"]):
            lobby["players"].append({"sid": sid, "name": name})

        return True

    def remove_player(self, sid):
        empty = []

        for lid, lobby in self.lobbies.items():
            lobby["players"] = [p for p in lobby["players"] if p["sid"] != sid]
            if not lobby["players"]:
                empty.append(lid)

        for lid in empty:
            del self.lobbies[lid]

    def list_lobbies(self):
        return [
            {
                "id": lid,
                "host": lobby["host"],
                "players": len(lobby["players"]),
                "player_names": [p["name"] for p in lobby["players"]],
            }
            for lid, lobby in self.lobbies.items()
        ]