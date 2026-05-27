import random
from game.rolelists import resolve_rolelist


def assign_roles(players, role_registry, list_config=None):
    player_count = len(players)
    if player_count < 2:
        raise ValueError(f"assign_roles requires at least 2 players, got {player_count}.")

    if list_config is not None:
        role_list = resolve_rolelist(list_config, player_count, role_registry)
        return {
            player["player_number"]: role_list[i]
            for i, player in enumerate(players)
        }

    town_roles  = [r for r in role_registry.values() if r["faction"] == "town"]
    coven_roles = [r for r in role_registry.values() if r["faction"] == "coven"]

    max_coven   = min(4, player_count - 1)
    coven_count = random.randint(1, max_coven)
    town_count  = player_count - coven_count

    coven_pool = coven_roles.copy()
    random.shuffle(coven_pool)
    selected_coven = coven_pool[:coven_count]

    all_town = town_roles.copy()
    random.shuffle(all_town)

    town_pool = []
    used_unique_names = set()
    for role in all_town:
        if len(town_pool) >= town_count:
            break
        if role.get("unique"):
            if role["name"] in used_unique_names:
                continue
            used_unique_names.add(role["name"])
        town_pool.append(role)

    remaining = town_count - len(town_pool)
    if remaining > 0:
        repeatable_town = [r for r in town_roles if not r.get("unique")]
        if not repeatable_town:
            raise ValueError("Not enough repeatable Town roles to fill the remaining slots.")
        random.shuffle(repeatable_town)
        for i in range(remaining):
            town_pool.append(repeatable_town[i % len(repeatable_town)])

    random.shuffle(town_pool)

    all_roles = selected_coven + town_pool
    random.shuffle(all_roles)

    return {
        player["player_number"]: all_roles[i]
        for i, player in enumerate(players)
    }