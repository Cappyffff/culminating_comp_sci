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
        self.permanent_effects = []

        self.night_action_submitted = False
        self.detection_immunity = False
        self.roleblock_immune = False
        self.control_immune = False
        self.charges     = -1
        self.vote_weight = 1

        #FOR NE (best roles I love pirate so much maybe not exe tho icl)
        self.has_won         = False
        self.left_town       = False
        self.exe_target      = None   
        self.ll_targets      = []     
        self.plunder_disabled = False 

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
            "permanent_effects": self.permanent_effects,
        }


class GameState:
    def __init__(self):
        self.players = {}
        self.phase = "lobby"
        self.phase_number = 0
        self.role_registry = {}
        self.locked = False
        self.day_number   = 0
        self.trials_used  = 0
        self.on_trial     = None  
        self.votes        = {}    
        self.verdicts     = {}    
        self.sub_phase = ""
        self.lobby_id = None
        self.night_actions   = {} 
        self.pending_feedback = {} 
        self.sub_phase = ""
        self.lobby_id  = None
        self.pending_retrains = {}
        self.max_trials    = 3
        self.jester_haunts = {} 

    def get_living_players(self):
        return [p for p in self.players.values() if p.alive]

    def get_player_by_sid(self, sid):
        for p in self.players.values():
            if p.sid == sid:
                return p
        return None

    def to_public_dict(self):
        return {
            "phase":      self.phase,
            "sub_phase":  self.sub_phase,
            "day_number": self.day_number,
            "players":    [p.to_dict() for p in self.players.values()],
        }
    
    def get_role_data(self, role_name):
        for data in self.role_registry.values():
            if data["name"] == role_name:
                return data
        return {}