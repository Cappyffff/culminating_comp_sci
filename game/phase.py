DURATIONS = {
    "day1":       15,
    "discussion": 45,
    "voting":     30,
    "defense":    15,
    "verdict":    15,
    "silence":    5,
    "last_words": 5,
    "night":      40,
    "night_end":  5,
}

def majority_threshold(living_count):
    return (living_count // 2) + 1