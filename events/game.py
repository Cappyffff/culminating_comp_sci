import random
from flask import request
from flask_socketio import emit
from game.actions import resolve_night, DAY_ABILITY_ROLES, DUAL_TARGET_ROLES, GUESS_ROLES
from game.win_conditions import check_win_conditions
from game.phase import DURATIONS
from game.actions import resolve_night, DAY_ABILITY_ROLES, DUAL_TARGET_ROLES, GUESS_ROLES, MULTI_GUESS_ROLES

def register(socketio, game_state, debug_service):

    def emit_phase(room, phase, sub_phase="", duration=0):
        game_state.phase     = phase
        game_state.sub_phase = sub_phase
        socketio.emit("phase_change", {
            "phase":     phase,
            "sub_phase": sub_phase,
            "duration":  duration,
        }, to=room)
        socketio.emit("game_state_update", game_state.to_public_dict(), to=room)

    def tick(room, seconds):
        for i in range(seconds, 0, -1):
            socketio.emit("phase_tick", {"seconds": i}, to=room)
            socketio.sleep(1)

    def kill_player(player_number, room):
        player = game_state.players.get(player_number)
        if not player or not player.alive:
            return
        player.alive = False
        stoned = "stoned" in player.permanent_effects
        debug_service.log("game", f"Player #{player_number} ({player.role}) died")
        socketio.emit("death_announcement", {
            "player_number": player.player_number,
            "nickname":      player.nickname,
            "role":          None if stoned else player.role,
            "stoned":        stoned,
        }, to=room)
        socketio.emit("game_state_update", game_state.to_public_dict(), to=room)

        for p in game_state.players.values():
            if p.role == "Executioner" and p.alive and p.exe_target == player_number:
                p.exe_target = None
                jester_data  = game_state.get_role_data("Jester")
                if jester_data:
                    p.role             = jester_data["name"]
                    p.alignment        = jester_data.get("faction", "neutral")
                    p.base_attack      = jester_data.get("attack", 0)
                    p.base_defense     = jester_data.get("defense", 1)
                    p.current_attack   = jester_data.get("attack", 0)
                    p.current_defense  = jester_data.get("defense", 1)
                    p.roleblock_immune = jester_data.get("roleblock_immune", False)
                    p.control_immune   = jester_data.get("control_immune", False)
                    p.charges          = jester_data.get("charges", -1)
                socketio.emit("role_changed", {
                    "role":                "Jester",
                    "category":           "Neutral Evil",
                    "ability_description": "Get yourself lynched. After being lynched, haunt a guilty voter.",
                    "message":            "Your target has died. You are now a Jester.",
                }, to=p.sid)

        check_pirate_wins(room)

    def check_majority(living_players):
        threshold = len(living_players) // 2 + 1
        tally = {}
        for voter_pnum, target_pnum in game_state.votes.items():
            voter  = game_state.players.get(voter_pnum)
            weight = voter.vote_weight if voter else 1
            tally[target_pnum] = tally.get(target_pnum, 0) + weight
        for pnum, count in tally.items():
            if count >= threshold:
                return pnum
        return None

    def is_guilty():
        guilty   = sum(1 for v in game_state.verdicts.values() if v == "guilty")
        innocent = sum(1 for v in game_state.verdicts.values() if v == "innocent")
        return guilty > innocent

    def apply_pending_retrains(lobby_id):
        for pnum, entry in list(game_state.pending_retrains.items()):
            player   = game_state.players.get(pnum)
            new_data = entry["data"]
            if player and player.alive:
                player.role             = new_data["name"]
                player.base_attack      = new_data["attack"]
                player.base_defense     = new_data["defense"]
                player.current_attack   = new_data["attack"]
                player.current_defense  = new_data["defense"]
                player.roleblock_immune = new_data["roleblock_immune"]
                player.control_immune   = new_data["control_immune"]
                player.charges          = new_data["charges"]
                player.vote_weight      = 1
                socketio.emit("role_changed", {
                    "role":                new_data["name"],
                    "category":           new_data["category"],
                    "ability_description": new_data["ability_description"],
                    "attack":             new_data["attack"],
                    "defense":            new_data["defense"],
                    "charges":            new_data["charges"],
                }, to=player.sid)
        game_state.pending_retrains = {}

    def run_game_loop(lobby_id):
        game_state.lobby_id = lobby_id
        for p in game_state.players.values():
            if p.role == "Executioner":
                candidates = [
                    tp for tp in game_state.players.values()
                    if tp.alignment == "town" and tp.player_number != p.player_number
                ]
                if candidates:
                    target_p      = random.choice(candidates)
                    p.exe_target  = target_p.player_number
                    socketio.emit("exe_target_info", {
                        "target_number":   target_p.player_number,
                        "target_nickname": target_p.nickname,
                        "target_role":     target_p.role,
                    }, to=p.sid)

        for p in game_state.players.values():
            if p.role == "Pirate":
                others      = [tp for tp in game_state.players.values() if tp.player_number != p.player_number]
                landlubbers = random.sample(others, min(3, len(others)))
                p.ll_targets = [tp.player_number for tp in landlubbers]
                socketio.emit("pirate_landlubbers", {
                    "roles": [tp.role for tp in landlubbers],
                }, to=p.sid)
        debug_service.log("game", f"Game loop started for {lobby_id}")

        # ── Day 1 ─────────────────────────────────────────────────────────────
        game_state.day_number = 1
        emit_phase(lobby_id, "Day 1", "", DURATIONS["day1"])
        tick(lobby_id, DURATIONS["day1"])

        winner = check_win_conditions(game_state)
        if winner:
            socketio.emit("game_over", {"winner": winner}, to=lobby_id)
            return

        day = 2
        while True:

            # ── Night ─────────────────────────────────────────────────────────
            night_label = f"Night {day - 1}"
            game_state.night_actions = {}
            for p in game_state.players.values():
                p.night_action_submitted = False

            emit_phase(lobby_id, night_label, "", DURATIONS["night"])
            tick(lobby_id, DURATIONS["night"])

            deaths, feedback, retrainings = resolve_night(game_state)

            # Notify retrain targets — they accept/decline before day start
            for target_pnum, entry in retrainings.items():
                player = game_state.players.get(target_pnum)
                if player and player.alive:
                    game_state.pending_retrains[target_pnum] = entry
                    socketio.emit("retrain_offer", {
                        "new_role":            entry["data"]["name"],
                        "category":           entry["data"]["category"],
                        "ability_description": entry["data"]["ability_description"],
                    }, to=player.sid)

            # Night-end silence
            emit_phase(lobby_id, night_label, "silence", DURATIONS["night_end"])

            for pnum in deaths:
                kill_player(pnum, lobby_id)

            winner = check_win_conditions(game_state)
            if winner:
                socketio.emit("game_over", {"winner": winner}, to=lobby_id)
                return

            for pnum, msgs in feedback.items():
                player = game_state.players.get(pnum)
                if player and msgs:
                    socketio.emit("night_feedback", {"messages": msgs}, to=player.sid)

            tick(lobby_id, DURATIONS["night_end"])

            # ── Day ───────────────────────────────────────────────────────────
            day_label = f"Day {day}"
            game_state.day_number  = day
            game_state.trials_used = 0

            for p in list(game_state.players.values()):
                if p.has_won and p.alive and not p.left_town and p.alignment == "neutral":
                    if p.role in ("Pirate", "Doomsayer"):
                        ne_depart(p, lobby_id)

            for p in game_state.players.values():
                if p.alive and "doomed_pending" in p.permanent_effects:
                    p.permanent_effects.remove("doomed_pending")
                    p.permanent_effects.append("doomed")
                    socketio.emit("doom_announcement", {
                        "player_number": p.player_number,
                        "nickname":      p.nickname,
                    }, to=lobby_id)

            if game_state.day_number == 3:
                for p in game_state.players.values():
                    if p.alignment == "neutral" and not p.has_won:
                        p.current_defense = 0
                        p.base_defense    = 0

            apply_pending_retrains(lobby_id)
            emit_phase(lobby_id, day_label, "discussion", DURATIONS["discussion"])

            tick(lobby_id, DURATIONS["discussion"])

            # ── Voting loop ───────────────────────────────────────────────────
            voting_remaining = DURATIONS["voting"]

            while game_state.trials_used < game_state.max_trials and voting_remaining > 0:
                game_state.votes = {}
                emit_phase(lobby_id, day_label, "voting", voting_remaining)

                living = game_state.get_living_players()
                accused = None

                for i in range(voting_remaining, 0, -1):
                    socketio.emit("phase_tick", {"seconds": i}, to=lobby_id)
                    socketio.sleep(1)
                    hit = check_majority(living)
                    if hit:
                        accused = hit
                        voting_remaining = i - 1
                        break

                if not accused:
                    break

                game_state.trials_used += 1
                game_state.on_trial = accused
                socketio.emit("trial_start", {"accused": accused}, to=lobby_id)
                debug_service.log("game", f"Trial #{game_state.trials_used} — accused #{accused}")

                emit_phase(lobby_id, day_label, "defense", DURATIONS["defense"])
                tick(lobby_id, DURATIONS["defense"])

                game_state.verdicts = {}
                emit_phase(lobby_id, day_label, "verdict", DURATIONS["verdict"])
                tick(lobby_id, DURATIONS["verdict"])

                guilty = is_guilty()
                socketio.emit("verdict_reveal", {
                    "accused":  accused,
                    "verdicts": game_state.verdicts,
                    "guilty":   guilty,
                }, to=lobby_id)

                emit_phase(lobby_id, day_label, "silence", DURATIONS["silence"])
                tick(lobby_id, DURATIONS["silence"])

                if guilty:
                    accused_player = game_state.players.get(accused)

                    for p in list(game_state.players.values()):
                        if p.role == "Executioner" and p.alive and p.exe_target == accused:
                            p.has_won         = True
                            p.current_defense = 3
                            game_state.max_trials = max(1, game_state.max_trials - 1)
                            ne_depart(p, lobby_id)

                    if accused_player and accused_player.role == "Jester":
                        accused_player.has_won         = True
                        accused_player.current_defense = 3
                        guilty_voters = [
                            pnum for pnum, v in game_state.verdicts.items() if v == "guilty"
                        ]
                        game_state.jester_haunts[accused] = {
                            "target":   None,
                            "eligible": guilty_voters,
                        }
                        socketio.emit("jester_haunt_later", {
                            "message": "You were lynched! You will choose your haunt tonight.",
                        }, to=accused_player.sid)
                        ne_depart(accused_player, lobby_id)
                        game_state.on_trial = None
                        winner = check_win_conditions(game_state)
                        if winner:
                            socketio.emit("game_over", {"winner": winner}, to=lobby_id)
                            return
                        break

                    emit_phase(lobby_id, day_label, "last_words", DURATIONS["last_words"])
                    tick(lobby_id, DURATIONS["last_words"])
                    game_state.on_trial = None
                    kill_player(accused, lobby_id)
                    check_pirate_wins(lobby_id)

                    winner = check_win_conditions(game_state)
                    if winner:
                        socketio.emit("game_over", {"winner": winner}, to=lobby_id)
                        return
                    break

            day += 1

    def ne_depart(player, room):
        player.alive     = False
        player.left_town = True
        socketio.emit("ne_departure", {
            "player_number": player.player_number,
            "nickname":      player.nickname,
            "role":          player.role,
        }, to=room)
        socketio.emit("game_state_update", game_state.to_public_dict(), to=room)

    def check_pirate_wins(room):
        for p in game_state.players.values():
            if p.role == "Pirate" and p.alive and not p.has_won and p.ll_targets:
                if all(
                    not game_state.players.get(ll) or not game_state.players[ll].alive
                    for ll in p.ll_targets
                ):
                    p.has_won = True
                    p.current_defense = 3
                    socketio.emit("ne_win_pending", {
                        "role":    "Pirate",
                        "message": "All your landlubbers have died. You win!",
                    }, to=p.sid)

    @socketio.on("cast_vote")
    def handle_cast_vote(data):
        player = game_state.get_player_by_sid(request.sid)
        if not player or not player.alive:
            return
        if game_state.sub_phase != "voting":
            emit("action_error", {"message": "Not in voting phase."}, to=request.sid)
            return
        target = data.get("target")
        if target is None:
            game_state.votes.pop(player.player_number, None)
        else:
            tp = game_state.players.get(target)
            if not tp or not tp.alive:
                emit("action_error", {"message": "Invalid target."}, to=request.sid)
                return
            if target == player.player_number:
                emit("action_error", {"message": "You cannot vote for yourself."}, to=request.sid)
                return
            game_state.votes[player.player_number] = target

        tally = {}
        for voter_pnum, t in game_state.votes.items():
            voter  = game_state.players.get(voter_pnum)
            weight = voter.vote_weight if voter else 1
            tally[t] = tally.get(t, 0) + weight

        living = game_state.get_living_players()
        socketio.emit("votes_updated", {
            "votes":     game_state.votes,
            "tally":     tally,
            "threshold": len(living) // 2 + 1,
        }, to=game_state.lobby_id)

    @socketio.on("cast_verdict")
    def handle_cast_verdict(data):
        player = game_state.get_player_by_sid(request.sid)
        if not player or not player.alive:
            return
        if game_state.sub_phase != "verdict":
            emit("action_error", {"message": "Not in verdict phase."}, to=request.sid)
            return
        if player.player_number == game_state.on_trial:
            emit("action_error", {"message": "The accused cannot vote."}, to=request.sid)
            return
        verdict = data.get("verdict")
        if verdict not in ("guilty", "innocent", "abstain"):
            return
        game_state.verdicts[player.player_number] = verdict
        socketio.emit("verdicts_updated", {
            "verdicts": game_state.verdicts,
        }, to=game_state.lobby_id)

    @socketio.on("submit_night_action")
    def handle_submit_night_action(data):
        player = game_state.get_player_by_sid(request.sid)
        if not player or not player.alive:
            return
        if "Night" not in game_state.phase or game_state.sub_phase != "":
            emit("action_error", {"message": "Not in action submission phase."}, to=request.sid)
            return
        if player.role in DAY_ABILITY_ROLES:
            return
        if player.left_town:
            return

        target   = data.get("target")
        target2  = data.get("target2")
        guess    = data.get("guess")
        new_role = data.get("new_role")
        guesses     = data.get("guesses")
        action_type = data.get("action_type")

        if target is not None:
            tp = game_state.players.get(target)
            if not tp or not tp.alive:
                emit("action_error", {"message": "Invalid target."}, to=request.sid)
                return

        if player.role in DUAL_TARGET_ROLES and target2 is not None:
            t2p = game_state.players.get(target2)
            if not t2p or not t2p.alive:
                emit("action_error", {"message": "Invalid second target."}, to=request.sid)
                return

        game_state.night_actions[player.player_number] = {
            "target":      target,
            "target2":     target2      if player.role in DUAL_TARGET_ROLES  else None,
            "guess":       guess        if player.role in GUESS_ROLES         else None,
            "new_role":    new_role     if player.role == "Archmage"          else None,
            "guesses":     guesses      if player.role == "Doomsayer"         else None,
            "action_type": action_type  if player.role == "Pirate"            else None,
        }

        player.night_action_submitted = True
        emit("action_confirmed", {"target": target, "target2": target2}, to=request.sid)

        for jester_pnum, haunt_data in game_state.jester_haunts.items():
            jester = game_state.players.get(jester_pnum)
            if jester:
                socketio.emit("jester_haunt_prompt", {
                    "guilty_voters": haunt_data.get("eligible", []),
                }, to=jester.sid)

    @socketio.on("respond_to_retrain")
    def handle_respond_to_retrain(data):
        player = game_state.get_player_by_sid(request.sid)
        if not player:
            return
        accept = data.get("accept", False)
        if not accept:
            entry = game_state.pending_retrains.pop(player.player_number, None)
            if entry:
                archmage_pnum = entry.get("archmage")
                archmage = game_state.players.get(archmage_pnum)
                if archmage:
                    socketio.emit("retrain_declined", {
                        "target": player.player_number,
                    }, to=archmage.sid)
        # If accept=True, do nothing — apply_pending_retrains handles it at day start

    @socketio.on("use_day_ability")
    def handle_day_ability(data):
        player = game_state.get_player_by_sid(request.sid)
        if not player or not player.alive:
            return
        if player.role not in DAY_ABILITY_ROLES:
            emit("action_error", {"message": "No day ability."}, to=request.sid)
            return
        blocked = {"voting", "verdict", "silence", "defense", "last_words"}
        if game_state.sub_phase in blocked or "Night" in game_state.phase:
            emit("action_error", {"message": "Cannot use ability right now."}, to=request.sid)
            return
        if player.charges == 0:
            emit("action_error", {"message": "No charges remaining."}, to=request.sid)
            return

        target   = data.get("target")
        lobby_id = game_state.lobby_id

        if player.role == "Deputy":
            tp = game_state.players.get(target)
            if not tp or not tp.alive:
                emit("action_error", {"message": "Invalid target."}, to=request.sid)
                return
            player.charges -= 1
            killed = 1 > tp.current_defense
            if killed:
                kill_player(target, lobby_id)
            socketio.emit("day_ability_used", {
                "role": "Deputy", "shooter": player.player_number,
                "target": target, "killed": killed,
            }, to=lobby_id)
            if killed:
                winner = check_win_conditions(game_state)
                if winner:
                    socketio.emit("game_over", {"winner": winner}, to=lobby_id)

        elif player.role == "Conjurer":
            tp = game_state.players.get(target)
            if not tp or not tp.alive:
                emit("action_error", {"message": "Invalid target."}, to=request.sid)
                return
            player.charges -= 1
            killed = 2 > tp.current_defense
            if killed:
                kill_player(target, lobby_id)
            socketio.emit("day_ability_used", {
                "role": "Conjurer", "target": target, "killed": killed,
            }, to=lobby_id)
            if killed:
                winner = check_win_conditions(game_state)
                if winner:
                    socketio.emit("game_over", {"winner": winner}, to=lobby_id)

        elif player.role == "Mayor":
            player.charges    -= 1
            player.vote_weight = 3
            socketio.emit("day_ability_used", {
                "role": "Mayor",
                "player_number": player.player_number,
                "nickname":      player.nickname,
            }, to=lobby_id)

        elif player.role == "Prosecutor":
            if game_state.sub_phase != "voting":
                emit("action_error", {"message": "Can only prosecute during voting."}, to=request.sid)
                return
            tp = game_state.players.get(target)
            if not tp or not tp.alive:
                emit("action_error", {"message": "Invalid target."}, to=request.sid)
                return
            player.charges -= 1
            game_state.votes[player.player_number] = target
            socketio.emit("day_ability_used", {
                "role": "Prosecutor", "target": target,
            }, to=lobby_id)

    @socketio.on("submit_haunt")
    def handle_submit_haunt(data):
        player = game_state.get_player_by_sid(request.sid)
        if not player or player.role != "Jester" or not player.has_won:
            return
        if "Night" not in game_state.phase:
            emit("action_error", {"message": "Haunt can only be submitted at night."}, to=request.sid)
            return
        pnum       = player.player_number
        haunt_data = game_state.jester_haunts.get(pnum)
        if haunt_data is None:
            return
        target = data.get("target")
        if target not in haunt_data.get("eligible", []):
            emit("action_error", {"message": "Invalid haunt target."}, to=request.sid)
            return
        haunt_data["target"] = target
        emit("haunt_confirmed", {"target": target}, to=request.sid)

    return run_game_loop