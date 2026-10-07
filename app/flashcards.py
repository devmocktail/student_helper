"""SM-2 spaced-repetition scheduling (the classic SuperMemo-2 algorithm).

A card tracks:
  interval  - days until it is next due
  reps      - number of consecutive successful reviews
  ef        - "ease factor" (how easy the card is), >= 1.3
  lapses    - number of times it was forgotten

`review(card, quality)` returns the updated scheduling fields. `quality` is a
grade from 0 (total blank) to 5 (perfect). The UI maps buttons to grades:
  Again=1, Hard=3, Good=4, Easy=5
"""

import time

DAY_SECONDS = 86400

# UI button label -> SM-2 quality grade
GRADES = {"Again": 1, "Hard": 3, "Good": 4, "Easy": 5}


def review(card, quality):
    """Return updated {interval, reps, ef, due, lapses} for a reviewed card."""
    ef = float(card["ef"])
    reps = int(card["reps"])
    interval = float(card["interval"])
    lapses = int(card["lapses"])

    if quality < 3:
        # Forgotten: reset the streak, see it again tomorrow.
        reps = 0
        interval = 1
        lapses += 1
    else:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = round(interval * ef)
        reps += 1
        # Adjust ease factor based on how well it was recalled.
        ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        if ef < 1.3:
            ef = 1.3

    due = time.time() + interval * DAY_SECONDS
    return {
        "interval": interval,
        "reps": reps,
        "ef": round(ef, 3),
        "due": due,
        "lapses": lapses,
    }
