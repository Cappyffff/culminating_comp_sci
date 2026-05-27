def check_win_conditions(game_state):
    living = [p for p in game_state.players.values() if p.alive]
    if not living:
        return "nobody"

    town  = [p for p in living if p.alignment == "town"]
    coven = [p for p in living if p.alignment == "coven"]

    non_coven = [p for p in living if p.alignment != "coven"]
    if non_coven and all("hexed" in p.permanent_effects for p in non_coven):
        return "coven"

    if len(coven) == 0:
        return "town"

    if len(coven) >= len(town):
        return "coven"

    return None