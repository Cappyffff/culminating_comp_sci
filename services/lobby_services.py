import uuid


class LobbyService:
    def __init__(self):
        self.lobbies = {}

    def create_lobby(self, sid, name, lobby_name=None, username=None):
        for lobby in self.lobbies.values():
            if lobby["host_sid"] == sid:
                return None

        self.lobbies[lobby_id] = {
            "host_sid":     sid,
            "host":         name,
            "lobby_name":   lobby_name or f"{name}'s game",
            "locked":       False,
            "players":      [...],
            "next_number":  2,
            "free_numbers": [],
            "selected_list":  None,
            "custom_list":    None,
            "list_votes":     {},
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
            "sid":           sid,
            "name":          name,
            "username":      username,
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

    def set_role_list(self, lobby_id, sid, list_key):
        if lobby_id not in self.lobbies:
            return False
        lobby = self.lobbies[lobby_id]
        if lobby["host_sid"] != sid:
            return False
        lobby["selected_list"] = list_key
        lobby["custom_list"]   = None
        return True

    def set_custom_list(self, lobby_id, sid, config):
        if lobby_id not in self.lobbies:
            return False
        lobby = self.lobbies[lobby_id]
        if lobby["host_sid"] != sid:
            return False
        lobby["custom_list"]   = config
        lobby["selected_list"] = None
        return True

    def rename_lobby(self, lobby_id, sid, new_name):
        if lobby_id not in self.lobbies:
            return False
        lobby = self.lobbies[lobby_id]
        if lobby["host_sid"] != sid:
            return False
        new_name = new_name.strip()
        if not new_name:
            return False
        lobby["lobby_name"] = new_name
        return True

    def kick_player(self, lobby_id, host_sid, target_number):
        if lobby_id not in self.lobbies:
            return None
        lobby = self.lobbies[lobby_id]
        if lobby["host_sid"] != host_sid:
            return None

        target = next(
            (p for p in lobby["players"] if p["player_number"] == target_number),
            None
        )
        if target is None:
            return None

        lobby["players"] = [p for p in lobby["players"] if p["player_number"] != target_number]
        lobby["free_numbers"].append(target_number)
        return target["sid"]

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
                lobby["host"]     = new_host["name"]
            if not lobby["players"]:
                empty.append(lid)
        for lid in empty:
            del self.lobbies[lid]

    def list_lobbies(self):
        return [
            {
                "id":            lid,
                "host":          lobby["host"],
                "lobby_name":    lobby["lobby_name"],
                "locked":        lobby["locked"],
                "players":       len(lobby["players"]),
                "player_list":   lobby["players"],
                "selected_list": lobby["selected_list"],
                "has_custom":    lobby["custom_list"] is not None,
            }
            for lid, lobby in self.lobbies.items()
        ]

    def vote_role_list(self, lobby_id, sid, list_key):
        if lobby_id not in self.lobbies:
            return False
        lobby = self.lobbies[lobby_id]
        if list_key is None:
            lobby["list_votes"].pop(sid, None)
        else:
            lobby["list_votes"][sid] = list_key
        return True

    def get_vote_tally(self, lobby_id):
        lobby = self.lobbies.get(lobby_id)
        if not lobby:
            return {}
        tally = {}
        for key in lobby.get("list_votes", {}).values():
            tally[key] = tally.get(key, 0) + 1
        return tally

    def get_vote_winner(self, lobby_id):
        import random
        lobby = self.lobbies.get(lobby_id)
        if not lobby:
            return None
        votes = lobby.get("list_votes", {})
        if not votes:
            return lobby.get("selected_list")
        tally = {}
        for key in votes.values():
            tally[key] = tally.get(key, 0) + 1
        top = max(tally.values())
        winners = [k for k, v in tally.items() if v == top]
        return random.choice(winners)