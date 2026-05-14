import tomllib


def load_role_registry(path="data/roles.toml"):
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data["roles"]


def apply_role_to_player(player, role_name, registry):
    role = registry[role_name]
    player.role = role_name
    player.alignment = role["faction"]
    player.base_attack = role["attack"]
    player.base_defense = role["defense"]
    player.current_attack = role["attack"]
    player.current_defense = role["defense"]
    player.roleblock_immune = role["roleblock_immune"]
    player.control_immune = role["control_immune"]