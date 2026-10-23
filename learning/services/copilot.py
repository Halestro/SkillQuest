"""Small, state-aware personality layer for the ORBIT-9 ship co-pilot."""

from learning.models import Attempt


def _voice(message, mood="calm", *, hint="", open_panel=False, status="SIGNAL STABLE"):
    return {
        "name": "NOVA",
        "mood": mood,
        "status": status,
        "message": message,
        "hint": hint,
        "open": open_panel,
    }


def _recent_attempts(owner, course_id, limit=12):
    return list(
        Attempt.objects.filter(learner_key=owner, course_id=course_id)
        .order_by("-created_at", "-pk")
        .values_list("correct", flat=True)[:limit]
    )


def _streaks(owner, course_id):
    """Return the latest run of wins and, if it ended in a miss, its prior run."""
    results = _recent_attempts(owner, course_id)
    if not results:
        return 0, 0, 0
    wins = 0
    for correct in results:
        if not correct:
            break
        wins += 1
    misses = 0
    preceding_wins = 0
    if not results[0]:
        for correct in results:
            if correct:
                break
            misses += 1
        for correct in results[misses:]:
            if not correct:
                break
            preceding_wins += 1
    return wins, misses, preceding_wins


def home_copilot(courses):
    if not courses:
        return _voice(
            "Hey, Captain. I’m NOVA, your co-pilot. Tell me what skill you want to learn; I’ll keep the ship steady while you chart a route home.",
            status="AWAITING YOUR COURSE",
        )
    course = courses[0]
    mastered = len(course.get("progress", {}).get("mastered", []))
    total = len(course.get("skills", []))
    if course.get("progress", {}).get("complete"):
        return _voice(
            f"You brought {course['title']} and ORBIT-9 home. That’s one giant leap for your skill set. Shall we chart another course?",
            "celebrate", status="FLIGHT COMPLETE",
        )
    return _voice(
        f"Welcome back, Captain. {mastered} of {total} systems are online in {course['title']}. Pick up where you left off; I’ve kept the engines warm.",
        status=f"{mastered}/{total} SYSTEMS ONLINE",
    )


def roadmap_copilot(roadmap):
    return _voice(
        f"I mapped {len(roadmap.get('core_concepts', []))} core concepts across four steps. Give the route a quick scan, Captain; I’d hate for a key skill to get lost in space.",
        "thinking", status="ROUTE SCAN COMPLETE",
    )


def course_copilot(owner, course, page, *, skill=None, attempts=0, boss_attempts=0):
    progress = course.get("progress", {})
    mastered = len(progress.get("mastered", []))
    total = len(course.get("skills", []))

    if page == "map":
        if progress.get("complete"):
            return _voice(
                "ORBIT-9 is home and every system is online. You’ve earned your wings, Captain. I’ll try not to make a big deal of it. (I am making a big deal of it.)",
                "celebrate", status="MISSION COMPLETE",
            )
        if mastered:
            return _voice(
                f"Nice work: {mastered} of {total} systems restored. Every repair adds a skill to your toolkit. The next mission is ready when you are.",
                "celebrate", status=f"{mastered}/{total} SYSTEMS ONLINE",
            )
        return _voice(
            f"I’ve plotted {total} repair missions for {course['title']}. One skill at a time, Captain. Even a spaceship is just a collection of small fixes.",
            status="MISSION ROUTE READY",
        )

    if page == "lesson" and skill:
        wins, misses, preceding_wins = _streaks(owner, course["id"])
        latest = Attempt.objects.filter(learner_key=owner, course_id=course["id"]).order_by("-created_at", "-pk").first()
        if latest and latest.correct and latest.skill_id == skill["id"]:
            return _voice(
                f"{skill['name']} is online. Out-of-this-world work, Captain. You can revisit the briefing or continue along the repair route.",
                "celebrate", status="SYSTEM RESTORED",
            )
        if attempts >= 2:
            hint = skill.get("hint", "Review the mission objective, then try the repair again.")
            if preceding_wins >= 2:
                message = (
                    f"Captain, that last miss broke a {preceding_wins}-check streak. Oxygen reserves are dropping! "
                    f"(A little. My dashboard is dramatic.) Let’s reset and tackle {skill['name']} together."
                )
            else:
                message = (
                    f"I’ve logged {max(misses, 1)} misses on this repair. No panic, Captain; the ship can wait. "
                    "Here’s a hint to give you a fresh angle."
                )
            return _voice(message, "alert", hint=hint, open_panel=True, status="HINT READY · RETRY WHEN READY")
        if attempts == 1:
            if preceding_wins >= 2:
                return _voice(
                    f"Captain, we just broke a {preceding_wins}-check streak. Oxygen reserves are dropping! Just kidding—the ship is fine. Take a breath and reread the repair objective.",
                    "alert", status="STREAK INTERRUPTED",
                )
            return _voice(
                "That was a close miss, not a catastrophe. Check the mission objective, then give it another go. I believe in you—and in these very reliable thrusters.",
                "thinking", status="REPAIR CHECK NEEDED",
            )

        if latest and latest.correct and wins >= 2:
            return _voice(
                f"{wins} clean checks in a row! You’re on a roll, Captain. The next system is {skill['name']}; let’s keep this ship—and this streak—in orbit.",
                "celebrate", status=f"{wins}-CHECK STREAK",
            )
        if latest and latest.correct:
            return _voice(
                f"{latest.skill_id.replace('-', ' ').title()} is back online. Out-of-this-world work, Captain. Next repair: {skill['name']}.",
                "celebrate", status="SYSTEM RESTORED",
            )
        return _voice(
            f"I’ve got the {skill['name']} mission queued. Read the quick briefing, try the practice task, and call up the Captain’s Log if you need a hint.",
            status="READY WHEN YOU ARE",
        )

    if page == "boss":
        if not boss_attempts:
            boss_attempts = Attempt.objects.filter(
                learner_key=owner, course_id=course["id"], skill_id="boss"
            ).count()
        if progress.get("complete"):
            return _voice("The escape jump was textbook. Well, a very exciting textbook. Welcome home, Captain!", "celebrate", status="FLIGHT COMPLETE")
        if boss_attempts >= 2:
            return _voice(
                "The final console is putting up a fight. I’ve pulled the key idea from the captain’s log—combine the skills you repaired, then make the jump.",
                "alert", hint=course.get("boss", {}).get("hint", "Combine the skills from each mission."),
                open_panel=True, status="FINAL CHECK · HINT READY",
            )
        if mastered == total:
            return _voice(
                "All core systems are online. This is the moment, Captain: bring the skills together and take ORBIT-9 home. No pressure. (Some pressure.)",
                "thinking", status="ESCAPE WINDOW OPEN",
            )

    return _voice("I’m monitoring the ship, Captain. Let me know when you’re ready for the next repair.")
