class Player:
    def __init__(self, player_number, sid, nickname=None):
        self.player_number = player_number
        self.sid = sid
        self.nickname = nickname or f"Player {player_number}"

        self.role = None
        self.alignment = None

        self.alive = True

        self.base_attack = 0
        self.base_defense = 0
        self.current_attack = 0
        self.current_defense = 0

        self.status_effects = []
        self.permanant_effects = []

        self.night_action_submitted = False
        self.detection_immunity = False
        self.roleblock_immune = False
        self.control_immune = False

    def to_dict(self):
        return {
            "player_number": self.player_number,
            "nickname": self.nickname,
            "alive": self.alive,
        }

    def to_private_dict(self):
        return {
            "player_number": self.player_number,
            "nickname": self.nickname,
            "role": self.role,
            "alignment": self.alignment,
            "alive": self.alive,
            "current_attack": self.current_attack,
            "current_defense": self.current_defense,
            "status_effects": self.status_effects,
            "permanant_effects": self.permanant_effects,
        }


class GameState:
    def __init__(self):
        self.players = {}
        self.phase = "lobby"
        self.phase_number = 0
        self.role_registry = {}
        self.locked = False

    def get_living_players(self):
        return [p for p in self.players.values() if p.alive]

    def get_player_by_sid(self, sid):
        for p in self.players.values():
            if p.sid == sid:
                return p
        return None

    def to_public_dict(self):
        return {
            "phase": self.phase,
            "phase_number": self.phase_number,
            "players": [p.to_dict() for p in self.players.values()],
        }