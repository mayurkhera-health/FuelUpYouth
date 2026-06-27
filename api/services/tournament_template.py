"""
Tournament Template — dynamic multi-game day layout (Purvi spec).

Pure card-ordering for tournament days. Grams are NOT computed here — they are
overlaid downstream by window_distribution / fuel_gauge. Everyday Meal anchors
the day: BEFORE the first window if first game >= 11:00, else AFTER (Wind-Down).
Between games: Recharge at gap >= 45 min, Rebuild at gap >= 90 min.
"""

_BASE_MEAL_COLOR = "#7A9E6E"


def _add_min(t: str, m: int) -> str:
    h, mn = map(int, t.split(":"))
    total = h * 60 + mn + m
    return f"{total // 60:02d}:{total % 60:02d}"


def _diff_min(t1: str, t2: str) -> int:
    def mins(t):
        h, m = map(int, t.split(":"))
        return h * 60 + m
    return mins(t2) - mins(t1)


def get_tournament_template(game_schedule: list, wt_kg: float) -> list:
    """game_schedule = [{'start_time':'HH:MM','duration_min':int}, ...] sorted by time."""
    cards = []
    first_game_hour = int(game_schedule[0]["start_time"].split(":")[0])
    everyday_pos = "before" if first_game_hour >= 11 else "after"

    if everyday_pos == "before":
        cards.append({
            "key": "everyday_meal", "card": "everyday_meal", "label": "Tournament Base Meal",
            "title": "Tournament Base Meal",
            "body": ("Start your tournament day with a solid meal before anything else. "
                     "This is the base your fuel windows build on. "
                     "2 fists of grains · 1 palm of protein · vegetables."),
            "subtitle": "TOURNAMENT DAY FUEL", "color": _BASE_MEAL_COLOR,
            "is_event": False, "is_tappable": True,
            "sort_time": game_schedule[0]["start_time"], "time_display": "",
            "game_num": None, "duration_min": None,
        })

    for i, game in enumerate(game_schedule):
        n = i + 1
        st = game["start_time"]
        dur = game["duration_min"]
        cards.append({"key": f"fuel_before_g{n}", "card": "fuel_before",
                      "label": f"Fuel Before — Game {n}", "game_num": n,
                      "is_event": False, "is_tappable": True,
                      "sort_time": _add_min(st, -180), "time_display": "",
                      "duration_min": None})
        cards.append({"key": f"top_up_g{n}", "card": "top_up",
                      "label": f"Top-Up — Game {n}", "game_num": n,
                      "is_event": False, "is_tappable": True,
                      "sort_time": _add_min(st, -45), "time_display": "",
                      "duration_min": None})
        cards.append({"key": f"event_g{n}", "card": "event",
                      "label": f"Game {n}", "game_num": n,
                      "is_event": True, "is_tappable": False,
                      "sort_time": st, "time_display": "", "duration_min": dur})
        if dur > 75:
            cards.append({"key": f"keep_going_g{n}", "card": "keep_going",
                          "label": f"Keep Going — Game {n}", "game_num": n,
                          "is_event": False, "is_tappable": True,
                          "sort_time": _add_min(st, dur // 2), "time_display": "",
                          "duration_min": dur})

        if n < len(game_schedule):
            this_end = _add_min(st, dur)
            next_start = game_schedule[i + 1]["start_time"]
            gap = _diff_min(this_end, next_start)
            if gap >= 45:
                cards.append({"key": f"recharge_g{n}_g{n+1}", "card": "recharge",
                              "label": f"Recharge — Between Games {n} & {n+1}",
                              "body": (f"You have {gap} minutes. Refuel NOW. "
                                       f"Fast carbs + protein within 30 minutes."),
                              "game_num": n, "is_event": False, "is_tappable": True,
                              "sort_time": this_end, "time_display": "", "duration_min": None})
            if gap >= 90:
                cards.append({"key": f"rebuild_g{n}_g{n+1}", "card": "rebuild",
                              "label": f"Rebuild — Pre-Game {n+1} Meal",
                              "body": ("More time between games — get a proper recovery meal in. "
                                       "Protein + carbs + healthy fat. Your body needs this."),
                              "game_num": n, "is_event": False, "is_tappable": True,
                              "sort_time": _add_min(this_end, 30), "time_display": "",
                              "duration_min": None})

    last = game_schedule[-1]
    final_end = _add_min(last["start_time"], last["duration_min"])
    cards.append({"key": "recharge_final", "card": "recharge", "label": "Recharge — After Final Game",
                  "is_event": False, "is_tappable": True,
                  "sort_time": final_end, "time_display": "", "game_num": None, "duration_min": None})
    cards.append({"key": "rebuild_final", "card": "rebuild", "label": "Rebuild — Tournament Recovery Meal",
                  "is_event": False, "is_tappable": True,
                  "sort_time": _add_min(final_end, 60), "time_display": "", "game_num": None, "duration_min": None})

    if everyday_pos == "after":
        cards.append({
            "key": "everyday_meal", "card": "everyday_meal", "label": "Wind-Down Meal",
            "title": "Wind-Down Meal",
            "body": ("Tournament done. This meal rounds out your day. "
                     "Protein · carbs · healthy fat."),
            "subtitle": "EVERYDAY FUEL", "color": _BASE_MEAL_COLOR,
            "is_event": False, "is_tappable": True,
            "sort_time": _add_min(final_end, 120), "time_display": "",
            "game_num": None, "duration_min": None,
        })

    return cards
