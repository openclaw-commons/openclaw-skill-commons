#!/usr/bin/env python3
"""
Calculate skill leaderboard from vote files.
Scores use time-decay weighting: recent votes matter more.
Also produces a "trending_7d" list based on votes in the last 7 days.
"""

import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

LAMBDA = 0.05  # decay constant, half-life ~14 days
VOTES_DIR = Path("votes")
LEADERBOARD_FILE = Path("leaderboard.json")


def decay_factor(timestamp_str: str) -> float:
    """Calculate time-decay weight for a vote."""
    try:
        vote_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days_ago = (now - vote_time).total_seconds() / 86400
        return math.exp(-LAMBDA * days_ago)
    except Exception:
        return 0.5


def is_within_days(timestamp_str: str, days: int) -> bool:
    try:
        vote_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return vote_time >= cutoff
    except Exception:
        return False


def calculate_leaderboard():
    skill_data = defaultdict(lambda: {
        "score": 0.0,
        "score_7d": 0.0,
        "total_votes": 0,
        "votes_7d": 0,
        "positive_votes": 0,
        "negative_votes": 0,
        "unique_voters": set(),
        "last_voted": None,
    })

    if not VOTES_DIR.exists():
        print("No votes directory found, generating empty leaderboard.")
        skills = []
        trending = []
    else:
        for instance_dir in VOTES_DIR.iterdir():
            if not instance_dir.is_dir():
                continue
            instance_id = instance_dir.name

            for vote_file in instance_dir.glob("*.json"):
                skill_name = vote_file.stem
                try:
                    with open(vote_file) as f:
                        data = json.load(f)

                    for vote in data.get("votes", []):
                        value = vote.get("value", 0)
                        ts = vote.get("timestamp", "")

                        if value not in (1, -1):
                            continue

                        weight = decay_factor(ts)
                        skill_data[skill_name]["score"] += value * weight
                        skill_data[skill_name]["total_votes"] += 1
                        skill_data[skill_name]["unique_voters"].add(instance_id)

                        if value == 1:
                            skill_data[skill_name]["positive_votes"] += 1
                        else:
                            skill_data[skill_name]["negative_votes"] += 1

                        if is_within_days(ts, 7):
                            skill_data[skill_name]["score_7d"] += value
                            skill_data[skill_name]["votes_7d"] += 1

                        if ts:
                            last = skill_data[skill_name]["last_voted"]
                            if last is None or ts > last:
                                skill_data[skill_name]["last_voted"] = ts

                except Exception as e:
                    print(f"Warning: could not parse {vote_file}: {e}")

        def build_entry(name, d):
            return {
                "name": name,
                "score": round(d["score"], 4),
                "score_7d": round(d["score_7d"], 4),
                "total_votes": d["total_votes"],
                "votes_7d": d["votes_7d"],
                "positive_votes": d["positive_votes"],
                "negative_votes": d["negative_votes"],
                "unique_voters": len(d["unique_voters"]),
                "last_voted": d["last_voted"],
            }

        skills = sorted(
            [build_entry(n, d) for n, d in skill_data.items()],
            key=lambda x: x["score"], reverse=True
        )

        trending = sorted(
            [s for s in skills if s["votes_7d"] > 0],
            key=lambda x: x["score_7d"], reverse=True
        )[:10]

    leaderboard = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "version": "0.2",
        "note": "Auto-generated. Do not edit manually.",
        "skills": skills,
        "trending_7d": trending,
    }

    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(leaderboard, f, indent=2, ensure_ascii=False)

    print(f"Leaderboard updated: {len(skills)} skills, {len(trending)} trending in 7d.")


if __name__ == "__main__":
    calculate_leaderboard()
