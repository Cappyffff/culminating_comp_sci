import random

PRIORITY_CONTROL       = 0
PRIORITY_ROLEBLOCK     = 1
PRIORITY_PROTECTIVE    = 2
PRIORITY_INVESTIGATIVE = 3
PRIORITY_SUPPORT       = 4
PRIORITY_KILLING       = 5

ROLE_PRIORITY = {
    "Witch":         PRIORITY_CONTROL,
    "Tavern Keeper": PRIORITY_ROLEBLOCK,
    "Poisoner":      PRIORITY_ROLEBLOCK,
    "Cleric":        PRIORITY_PROTECTIVE,
    "Trapper":       PRIORITY_PROTECTIVE,
    "Socialite":     PRIORITY_PROTECTIVE,
    "Sheriff":       PRIORITY_INVESTIGATIVE,
    "Tracker":       PRIORITY_INVESTIGATIVE,
    "Psychic":       PRIORITY_INVESTIGATIVE,
    "Wilding":       PRIORITY_INVESTIGATIVE,
    "Medusa":        PRIORITY_SUPPORT,
    "Illusionist":   PRIORITY_SUPPORT,
    "Hex Master":    PRIORITY_SUPPORT,
    "Archmage":      PRIORITY_SUPPORT,
    "Vigilante":     PRIORITY_KILLING,
    "Ritualist":     PRIORITY_KILLING,
    "Pirate":        PRIORITY_KILLING,
    "Doomsayer":     PRIORITY_KILLING,
    
}

DAY_ABILITY_ROLES = {"Mayor", "Prosecutor", "Deputy", "Conjurer"}

DUAL_TARGET_ROLES = {"Witch"}

GUESS_ROLES = {"Ritualist"}
MULTI_GUESS_ROLES = {"Doomsayer"}


def resolve_night(game_state):

    players = game_state.players
    actions = game_state.night_actions

    role_by_name = {v["name"]: v for v in game_state.role_registry.values()}

    def living(pnum):
        p = players.get(pnum)
        return p if (p and p.alive) else None

    def is_astral(pnum):
        p = players.get(pnum)
        data = role_by_name.get(p.role, {}) if p else {}
        return data.get("astral", False)

    feedback = {pnum: [] for pnum in players}
    retrainings = {}

    doomed_deaths = set()
    for pnum_d, p_d in players.items():
        if p_d.alive and "doomed" in p_d.permanent_effects:
            doomed_deaths.add(pnum_d)
            add_fb(pnum_d, "The Doomsayer's curse has claimed you.")

    jester_haunt_kills = set()
    for jester_pnum, haunt_data in list(game_state.jester_haunts.items()):
        target = haunt_data.get("target")
        if target is None:
            eligible = [
                p for p in haunt_data.get("eligible", [])
                if players.get(p) and players[p].alive
            ]
            target = random.choice(eligible) if eligible else None
        if target and players.get(target) and players[target].alive:
            jester_haunt_kills.add(target)
            add_fb(target, "The Jester's ghost has come for you.")
    game_state.jester_haunts = {}

    def add_fb(pnum, msg):
        if pnum in feedback:
            feedback[pnum].append(msg)

    def use_charge(player):
        if player.charges == -1:
            return True
        if player.charges <= 0:
            return False
        player.charges -= 1
        return True

    going_to = {}
    for pnum, action in actions.items():
        if not action or not living(pnum):
            continue
        target = action.get("target")
        if target is not None and living(target):
            going_to[pnum] = target

    for pnum, action in actions.items():
        p = living(pnum)
        if not p or p.role != "Witch" or not action:
            continue
        t1 = action.get("target")
        t2 = action.get("target2")
        if t1 is None or t2 is None:
            continue
        t1p = living(t1)
        t2p = living(t2)
        if not t1p or not t2p:
            continue
        if t1p.control_immune:
            add_fb(pnum, "Your target was immune to your control.")
            continue
        going_to[t1] = t2
        add_fb(pnum, f"You controlled #{t1} ({t1p.role}) to visit #{t2}.")
        add_fb(t1, "You were controlled last night.")

    roleblocked = set()
    for pnum, action in actions.items():
        p = living(pnum)
        if not p or ROLE_PRIORITY.get(p.role, 99) != PRIORITY_ROLEBLOCK or not action:
            continue
        target = action.get("target")
        if target is None:
            continue
        tp = living(target)
        if not tp:
            continue
        if tp.roleblock_immune:
            add_fb(pnum, "Your target was immune to your roleblock.")
            continue
        roleblocked.add(target)
        add_fb(pnum, f"You roleblocked #{target}.")
        add_fb(target, "You were roleblocked last night.")

    for pnum in roleblocked:
        going_to.pop(pnum, None)
    for pnum in list(going_to):
        if not living(going_to[pnum]):
            going_to.pop(pnum, None)

    visits = {}
    for visitor, target in going_to.items():
        if not is_astral(visitor):
            visits.setdefault(target, []).append(visitor)

    illusioned = set()
    for pnum, action in actions.items():
        p = living(pnum)
        if not p or p.role != "Illusionist" or not action or pnum in roleblocked:
            continue
        target = action.get("target")
        if target is not None and living(target):
            illusioned.add(target)

    defenses = {} 
    trapped  = {}

    for pnum, action in actions.items():
        p = living(pnum)
        if not p or ROLE_PRIORITY.get(p.role, 99) != PRIORITY_PROTECTIVE or not action:
            continue
        if pnum in roleblocked:
            add_fb(pnum, "You were roleblocked and could not use your ability.")
            continue
        target = action.get("target")
        if target is None:
            continue
        tp = living(target)
        if not tp:
            continue

        if p.role == "Cleric":
            defenses[target] = max(defenses.get(target, 0), 2)   # powerful defense
            add_fb(pnum, f"You placed a barrier on #{target}.")
            add_fb(target, "You were protected by a Cleric's barrier last night.")

        elif p.role == "Trapper":
            defenses[target] = max(defenses.get(target, 0), 2)
            trapped[target] = pnum
            add_fb(pnum, f"You set a trap at #{target}'s house.")

        elif p.role == "Socialite":
            for visitor in visits.get(target, []):
                vp = living(visitor)
                if not vp or vp.roleblock_immune:
                    continue
                roleblocked.add(visitor)
                add_fb(visitor, "You were turned away and could not use your ability.")
            add_fb(pnum, f"You hosted a party at #{target}'s house.")

    for pnum, action in actions.items():
        p = living(pnum)
        if not p or ROLE_PRIORITY.get(p.role, 99) != PRIORITY_INVESTIGATIVE or not action:
            continue
        if pnum in roleblocked:
            add_fb(pnum, "You were roleblocked and could not use your ability.")
            continue
        target = action.get("target")
        if target is None:
            continue
        tp = living(target)
        if not tp:
            continue

        if p.role == "Sheriff":
            if target in illusioned:
                result = "innocent"
            elif tp.alignment == "coven" and not tp.detection_immunity:
                result = "suspicious"
            else:
                result = "innocent"
            add_fb(pnum, f"#{target} appears to be {result}.")

        elif p.role == "Tracker":
            dest = going_to.get(target)
            if dest:
                add_fb(pnum, f"#{target} visited #{dest} last night.")
            else:
                add_fb(pnum, f"#{target} did not visit anyone last night.")

        elif p.role == "Psychic":
            others = [n for n in players if n != pnum and living(n)]
            if len(others) >= 3:
                evil = [n for n in others if players[n].alignment == "coven"]
                if evil:
                    pick = random.choice(evil)
                    rest = random.sample([n for n in others if n != pick], 2)
                    vision = [pick] + rest
                else:
                    vision = random.sample(others, 3)
                random.shuffle(vision)
                nums = ", ".join(f"#{n}" for n in vision)
                add_fb(pnum, f"You had a vision. One of these players is suspicious: {nums}")
            else:
                add_fb(pnum, "There were not enough players for a vision.")

        elif p.role == "Wilding":
            dest = going_to.get(target)
            vlist = [v for v in visits.get(target, []) if v != pnum]
            if dest:
                add_fb(pnum, f"#{target} visited #{dest} last night.")
            else:
                add_fb(pnum, f"#{target} stayed home last night.")
            if vlist:
                add_fb(pnum, f"#{target} was visited by: {', '.join(f'#{v}' for v in vlist)}.")
            else:
                add_fb(pnum, f"Nobody visited #{target} last night.")

    for pnum, action in actions.items():
        p = living(pnum)
        if not p or ROLE_PRIORITY.get(p.role, 99) != PRIORITY_SUPPORT or not action:
            continue
        if pnum in roleblocked:
            add_fb(pnum, "You were roleblocked and could not use your ability.")
            continue
        target = action.get("target")

        if p.role == "Medusa":
            if target is None:
                continue
            tp = living(target)
            if not tp:
                continue
            if not use_charge(p):
                add_fb(pnum, "You have no charges remaining.")
                continue
            if "stoned" not in tp.permanent_effects:
                tp.permanent_effects.append("stoned")
            add_fb(pnum, f"You stoned #{target}.")

        elif p.role == "Illusionist":
            if target is not None and living(target):
                add_fb(pnum, f"#{target} will appear innocent to investigators tonight.")

        elif p.role == "Archmage":
            target   = action.get("target")
            new_role = action.get("new_role")
            if target is None or not new_role:
                continue
            tp = living(target)
            if not tp or tp.alignment != "coven":
                add_fb(pnum, "You can only retrain coven members.")
                continue
            new_data = role_by_name.get(new_role, {})
            if not new_data or new_data.get("faction") != "coven":
                add_fb(pnum, "Invalid role.")
                continue
            BLOCKED_FOR_OTHERS = {"Coven Killing", "Coven Power"}
            if target != pnum and new_data.get("category") in BLOCKED_FOR_OTHERS:
                add_fb(pnum, "You cannot retrain others into Coven Killing or Coven Power roles.")
                continue
            retrainings[target] = {"data": new_data, "archmage": pnum}
            add_fb(pnum, f"You are attempting to retrain #{target} into {new_role}.")
            add_fb(target, f"The Archmage wants to retrain you into {new_role}. You can accept or decline.")

        elif p.role == "Hex Master":
            if target is None:
                continue
            tp = living(target)
            if not tp:
                continue
            if "hexed" not in tp.permanent_effects:
                tp.permanent_effects.append("hexed")
            add_fb(pnum, f"You hexed #{target}.")
            # TODO: check win condition — if all non-coven players are hexed

    pending_attacks = [] 

    for pnum, action in actions.items():
        p = living(pnum)
        if not p or ROLE_PRIORITY.get(p.role, 99) != PRIORITY_KILLING or not action:
            continue
        if pnum in roleblocked:
            add_fb(pnum, "You were roleblocked and could not use your ability.")
            continue
        target = going_to.get(pnum)  
        if target is None:
            continue

        if p.role == "Vigilante":
            if not use_charge(p):
                add_fb(pnum, "You have no charges remaining.")
                continue
            pending_attacks.append((pnum, target, 1))

        elif p.role == "Ritualist":
            if not use_charge(p):
                add_fb(pnum, "You have no charges remaining.")
                continue
            guess = action.get("guess", "")
            tp = living(target)
            if tp and guess == tp.role:
                pending_attacks.append((pnum, target, 3))
                add_fb(pnum, "Your ritual succeeded. You attacked your target.")
            else:
                add_fb(pnum, "Your ritual failed — your guess was wrong.")

        elif p.role == "Pirate":
            action_type = action.get("action_type", "scour")
            if action_type == "scour":
                is_ll = target in p.ll_targets
                add_fb(pnum, f"#{target} {'IS' if is_ll else 'is NOT'} one of your landlubbers.")
                continue  # scour never kills
            elif action_type == "plunder":
                if p.plunder_disabled:
                    add_fb(pnum, "Your plunder ability has been permanently revoked.")
                    continue
                if not use_charge(p):
                    add_fb(pnum, "You have no plunder charges remaining.")
                    continue
                if target not in p.ll_targets:
                    p.plunder_disabled = True
                    add_fb(pnum, "That was not one of your landlubbers! Your plunder has been permanently revoked.")
                pending_attacks.append((pnum, target, 1))

        elif p.role == "Doomsayer":
            guesses = action.get("guesses", [])
            if len(guesses) < 3:
                add_fb(pnum, "You did not submit 3 guesses. The doom was not triggered.")
                continue
            seen = set()
            doomed_targets = []
            all_correct = True
            for g in guesses[:3]:
                gt = g.get("target")
                gr = g.get("role")
                gp = living(gt)
                if not gp or gt in seen:
                    all_correct = False
                    break
                seen.add(gt)
                if gp.role == gr:
                    doomed_targets.append(gt)
                else:
                    all_correct = False
                    break
            if all_correct and len(doomed_targets) == 3:
                p.has_won = True
                p.current_defense = 3
                for dt in doomed_targets:
                    dtp = players.get(dt)
                    if dtp and "doomed_pending" not in dtp.permanent_effects:
                        dtp.permanent_effects.append("doomed_pending")
                add_fb(pnum, "All three of your prophecies rang true. Doom has been cast!")
            else:
                add_fb(pnum, "Not all 3 guesses were correct. The doom was not triggered.")

    for attacker, target, atk_level in list(pending_attacks):
        if target in trapped and not is_astral(attacker):
            trapper_pnum = trapped[target]
            pending_attacks.append((trapper_pnum, attacker, 2))
            ap = players.get(attacker)
            add_fb(trapper_pnum, f"#{attacker} ({ap.role if ap else '?'}) walked into your trap!")
            add_fb(target, "Your trap protected you from an attacker!")

    for target_pnum, trapper_pnum in trapped.items():
        for visitor in visits.get(target_pnum, []):
            vp = players.get(visitor)
            if vp:
                add_fb(trapper_pnum, f"#{visitor} ({vp.role}) visited your trap.")

    deaths = set()
    for attacker, target, atk_level in pending_attacks:
        tp = living(target)
        if not tp:
            continue
        effective_def = defenses.get(target, tp.current_defense)
        if atk_level > effective_def:
            deaths.add(target)
            add_fb(attacker, f"You successfully killed #{target}.")
            add_fb(target, "You were attacked last night!")
        else:
            add_fb(attacker, "Your target was too strong to kill.")
            if target not in deaths:
                add_fb(target, "Someone tried to attack you, but you were protected!")

    all_deaths = deaths | doomed_deaths | jester_haunt_kills
    for pnum_p, p_p in players.items():
        if p_p.role == "Pirate" and p_p.alive and not p_p.has_won and p_p.ll_targets:
            if all(
                not players.get(ll) or not players[ll].alive or ll in all_deaths
                for ll in p_p.ll_targets
            ):
                p_p.has_won = True
                p_p.current_defense = 3
                add_fb(pnum_p, "All your landlubbers have perished. Your work here is done.")

    deaths = all_deaths
    return deaths, feedback, retrainings