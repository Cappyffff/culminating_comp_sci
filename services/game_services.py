import random


def assign_roles(players, role_registry):
    player_count = len(players)
    if player_count < 2:
        raise ValueError(f"assign_roles requires at least 2 players, got {player_count}.")

    town_roles  = [r for r in role_registry.values() if r["faction"] == "town"]
    coven_roles = [r for r in role_registry.values() if r["faction"] == "coven"]

    max_coven   = min(4, player_count - 1)
    coven_count = random.randint(1, max_coven)
    town_count  = player_count - coven_count

    coven_pool = coven_roles.copy()
    random.shuffle(coven_pool)
    selected_coven = coven_pool[:coven_count]

    unique_town     = [r for r in town_roles if r.get("unique")]
    repeatable_town = [r for r in town_roles if not r.get("unique")]

    random.shuffle(unique_town)
    random.shuffle(repeatable_town)

    town_pool = unique_town[:town_count]

    remaining = town_count - len(town_pool)
    if remaining > 0:
        if not repeatable_town:
            raise ValueError("Not enough repeatable Town roles to fill the remaining slots.")
        for i in range(remaining):
            town_pool.append(repeatable_town[i % len(repeatable_town)])

    random.shuffle(town_pool)

    all_roles = selected_coven + town_pool
    random.shuffle(all_roles)

    return {
        player["player_number"]: all_roles[i]
        for i, player in enumerate(players)
    }