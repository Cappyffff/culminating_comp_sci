TOWN_BLOCKED = {"voting", "verdict", "silence"}

def can_chat(player, game_state, chat_type="town"):
    if not player.alive:
        return False, "Dead players cannot chat."

    phase    = game_state.phase
    sub      = game_state.sub_phase
    is_night = "Night" in phase

    if chat_type == "coven":
        if player.alignment != "coven":
            return False, "You are not in the coven."
        if not is_night:
            return False, "Coven can only chat at night."
        if sub == "silence":
            return False, "You cannot speak right now."
        return True, ""
    if is_night:
        return False, "You cannot chat at night."

    if sub in TOWN_BLOCKED:
        return False, "You cannot speak right now."

    if sub == "defense":
        if game_state.on_trial == player.player_number:
            return True, ""
        return False, "Only the accused may speak during defense."

    if sub == "last_words":
        if game_state.on_trial == player.player_number:
            return True, ""
        return False, "Only the accused may speak during last words."

    return True, ""