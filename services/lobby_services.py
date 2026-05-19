import uuid


class LobbyService:
    def __init__(self):
        self.lobbies = {}

    def create_lobby(self, sid, name, lobby_name=None, username=None):        
        for lobby in self.lobbies.values():
            if lobby["host_sid"] == sid:
                return None

        lobby_id = str(uuid.uuid4())
        self.lobbies[lobby_id] = {
            "host_sid": sid,
            "host": name,
            "lobby_name": lobby_name or f"{name}'s game",
            "locked": False,
            "players": [{"sid": sid, "name": name, "username": username, "player_number": 1}],
            "next_number": 2,
            "free_numbers": []
        }
        return lobby_id
    
    def get_lobby(self, lobby_id):
        return self.lobbies.get(lobby_id)

    def join_lobby(self, lobby_id, sid, name, username=None):
        if lobby_id not in self.lobbies:
            return False

        lobby = self.lobbies[lobby_id]

        if lobby["locked"]:
            return False

        if any(p["sid"] == sid for p in lobby["players"]):
            return True

        if lobby["free_numbers"]:
            player_number = lobby["free_numbers"].pop(0)
        else:
            player_number = lobby["next_number"]
            lobby["next_number"] += 1

        lobby["players"].append({
            "sid": sid,
            "name": name,
            "username": username,
            "player_number": player_number
        })

        return True

    def lock_lobby(self, lobby_id, sid):
        if lobby_id not in self.lobbies:
            return False

        lobby = self.lobbies[lobby_id]

        if lobby["host_sid"] != sid:
            return False

        lobby["locked"] = True
        return True

    def unlock_lobby(self, lobby_id, sid):
        if lobby_id not in self.lobbies:
            return False
        lobby = self.lobbies[lobby_id]
        if lobby["host_sid"] != sid:
            return False
        lobby["locked"] = False
        return True

    def remove_player(self, sid):
        empty = []

        for lid, lobby in self.lobbies.items():
            new_players = [p for p in lobby["players"] if p["sid"] != sid]

            for p in lobby["players"]:
                if p["sid"] == sid:
                    lobby["free_numbers"].append(p["player_number"])

            lobby["players"] = new_players

            if lobby.get("host_sid") == sid and lobby["players"]:
                new_host = lobby["players"][0]
                lobby["host_sid"] = new_host["sid"]
                lobby["host"] = new_host["name"]

            if not lobby["players"]:
                empty.append(lid)

        for lid in empty:
            del self.lobbies[lid]

    def list_lobbies(self):
        return [
            {
                "id": lid,
                "host": lobby["host"],
                "lobby_name": lobby["lobby_name"],
                "locked": lobby["locked"],
                "players": len(lobby["players"]),
                "player_list": lobby["players"]
            }
            for lid, lobby in self.lobbies.items()
        ]
    