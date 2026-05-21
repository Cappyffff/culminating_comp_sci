import tomllib
import random

SLOT_PRIORITY = {
    "specific":      0,
    "pool":          1,
    "category":      2,
    "random_town":   3,
    "random_coven":  3,
    "common_town":   3,
    "common_coven":  3,
    "any":           4,
}

COMMON_COVEN_CATEGORIES = {"Coven Utility", "Coven Deception"}
COMMON_TOWN_EXCLUDED    = {"Town Power"}


def load_rolelist_registry(path="data/rolelists.toml"):
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data["lists"]


def resolve_rolelist(list_config, player_count, role_registry):

    max_coven        = min(4, player_count - 1)
    used_unique_keys = set()
    coven_filled     = 0
    resolved         = []

    def available(faction=None, category=None, exclude_categories=None, include_categories=None):
        pool = []
        for key, role in role_registry.items():
            if faction and role["faction"] != faction:
                continue
            if category and role["category"] != category:
                continue
            if exclude_categories and role["category"] in exclude_categories:
                continue
            if include_categories and role["category"] not in include_categories:
                continue
            if role.get("unique") and key in used_unique_keys:
                continue
            pool.append((key, role))
        return pool

    def mark(key, role):
        if role.get("unique"):
            used_unique_keys.add(key)

    def resolve_slot(slot):
        nonlocal coven_filled
        slot_type = slot["type"]

        if slot_type == "specific":
            key = slot["role"]
            if key not in role_registry:
                raise ValueError(f"Role key '{key}' not found in registry.")
            role = role_registry[key]
            if role.get("unique") and key in used_unique_keys:
                raise ValueError(
                    f"Role '{key}' is unique but appears more than once in the list."
                )
            if role["faction"] == "coven" and coven_filled >= max_coven:
                raise ValueError(
                    f"Role '{key}' would exceed the coven cap of {max_coven}."
                )
            mark(key, role)
            if role["faction"] == "coven":
                coven_filled += 1
            return role

        elif slot_type == "pool":
            roles      = slot.get("roles", [])
            candidates = []
            for key in roles:
                if key not in role_registry:
                    continue
                role = role_registry[key]
                if role.get("unique") and key in used_unique_keys:
                    continue
                if role["faction"] == "coven" and coven_filled >= max_coven:
                    continue
                candidates.append((key, role))
            if not candidates:
                raise ValueError(
                    f"Pool slot {roles} has no remaining eligible roles."
                )
            key, role = random.choice(candidates)
            mark(key, role)
            if role["faction"] == "coven":
                coven_filled += 1
            return role

        elif slot_type == "category":
            category = slot["category"]
            faction  = category.split()[0].lower()
            if faction == "coven" and coven_filled >= max_coven:
                raise ValueError(
                    f"Category slot '{category}' would exceed the coven cap of {max_coven}."
                )
            pool = available(faction=faction, category=category)
            if not pool:
                raise ValueError(f"No available roles left in category '{category}'.")
            key, role = random.choice(pool)
            mark(key, role)
            if role["faction"] == "coven":
                coven_filled += 1
            return role

        elif slot_type == "random_town":
            pool = available(faction="town")
            if not pool:
                raise ValueError("No available roles left for random_town slot.")
            key, role = random.choice(pool)
            mark(key, role)
            return role

        elif slot_type == "random_coven":
            if coven_filled >= max_coven:
                raise ValueError("random_coven slot would exceed the coven cap.")
            pool = available(faction="coven")
            if not pool:
                raise ValueError("No available roles left for random_coven slot.")
            key, role = random.choice(pool)
            mark(key, role)
            coven_filled += 1
            return role

        elif slot_type == "common_town":
            pool = available(faction="town", exclude_categories=COMMON_TOWN_EXCLUDED)
            if not pool:
                raise ValueError("No available roles left for common_town slot.")
            key, role = random.choice(pool)
            mark(key, role)
            return role

        elif slot_type == "common_coven":
            if coven_filled >= max_coven:
                raise ValueError("common_coven slot would exceed the coven cap.")
            pool = available(faction="coven", include_categories=COMMON_COVEN_CATEGORIES)
            if not pool:
                raise ValueError("No available roles left for common_coven slot.")
            key, role = random.choice(pool)
            mark(key, role)
            coven_filled += 1
            return role

        elif slot_type == "any":
            pool = available() if coven_filled < max_coven else available(faction="town")
            if not pool:
                raise ValueError("No available roles left for 'any' slot.")
            key, role = random.choice(pool)
            mark(key, role)
            if role["faction"] == "coven":
                coven_filled += 1
            return role

        else:
            raise ValueError(f"Unknown slot type '{slot_type}'.")

    all_slots = []
    for section in ("town", "coven", "any"):
        for slot in list_config.get(section, []):
            all_slots.append(slot)

    all_slots.sort(key=lambda s: SLOT_PRIORITY.get(s["type"], 99))
    for slot in all_slots:
        if len(resolved) >= player_count:
            break
        resolved.append(resolve_slot(slot))

    remaining = player_count - len(resolved)
    for _ in range(remaining):
        pool = available() if coven_filled < max_coven else available(faction="town")
        if not pool:
            raise ValueError("Not enough roles available to fill all player slots.")
        key, role = random.choice(pool)
        mark(key, role)
        if role["faction"] == "coven":
            coven_filled += 1
        resolved.append(role)

    random.shuffle(resolved)
    return resolved