import uuid

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .services.course_store import (
    get_course, get_roadmap, list_courses, list_roadmaps,
    mark_roadmap_gamified, record_answer, record_boss_answer, save_course, save_roadmap,
)
from .services.ai import gamify_roadmap, generate_roadmap
from .services.copilot import course_copilot, home_copilot, roadmap_copilot


def learner_key(request):
    if "learner_key" not in request.session:
        request.session["learner_key"] = uuid.uuid4().hex
    return request.session["learner_key"]


def home(request):
    owner = learner_key(request)
    courses = list_courses(owner)
    return render(request, "learning/home.html", {
        "courses": courses, "roadmaps": list_roadmaps(owner),
        "copilot": home_copilot(courses),
    })


@require_POST
def create_roadmap(request):
    prompt = request.POST.get("prompt", "").strip()[:2000]
    if len(prompt) < 8:
        messages.error(request, "Describe what you want to learn and what you want to be able to do.")
        return redirect("home")
    try:
        roadmap = generate_roadmap(prompt)
    except Exception as exc:
        messages.error(request, f"The roadmap could not be generated. Details: {exc}")
        return redirect("home")
    roadmap_id = uuid.uuid4().hex
    save_roadmap(roadmap_id, learner_key(request), prompt, roadmap)
    return redirect("roadmap_review", roadmap_id=roadmap_id)


def roadmap_review(request, roadmap_id):
    document = get_roadmap(roadmap_id, learner_key(request))
    if not document:
        raise Http404("Roadmap not found for this browser session.")
    if document.get("status") == "gamified" and document.get("course_id"):
        return redirect("course_map", course_id=document["course_id"])
    roadmap = document["roadmap"]
    concepts = {item["id"]: item["name"] for item in roadmap["core_concepts"]}
    for step in roadmap["steps"]:
        step["mapped_concepts"] = [concepts[item] for item in step["concept_ids"]]
    return render(request, "learning/roadmap.html", {
        "document": document, "roadmap": roadmap, "copilot": roadmap_copilot(roadmap),
    })


@require_POST
def gamify(request, roadmap_id):
    owner = learner_key(request)
    document = get_roadmap(roadmap_id, owner)
    if not document:
        raise Http404("Roadmap not found for this browser session.")
    if document.get("status") == "gamified" and document.get("course_id"):
        return redirect("course_map", course_id=document["course_id"])
    try:
        course = gamify_roadmap(document["roadmap"])
    except Exception as exc:
        messages.error(request, f"Could not turn this roadmap into missions yet. Details: {exc}")
        return redirect("roadmap_review", roadmap_id=roadmap_id)
    course["id"] = uuid.uuid4().hex
    course["roadmap_id"] = roadmap_id
    save_course(course, owner)
    mark_roadmap_gamified(roadmap_id, owner, course["id"])
    return redirect("course_map", course_id=course["id"])


def owned_course(request, course_id):
    course = get_course(course_id, learner_key(request))
    if not course:
        raise Http404("Course not found for this browser session.")
    return course


def course_map(request, course_id):
    course = owned_course(request, course_id)
    progress = course.get("progress", {})
    mastered = set(progress.get("mastered", []))
    xp = len(mastered) * 20 + (50 if progress.get("complete") else 0)
    first_open = next((skill for skill in course["skills"] if skill["id"] not in mastered), None)
    return render(request, "learning/course_map.html", {
        "course": course, "mastered": mastered, "xp": xp,
        "complete": progress.get("complete", False), "first_open": first_open,
        "copilot": course_copilot(learner_key(request), course, "map"),
    })


def lesson(request, course_id, skill_id):
    course = owned_course(request, course_id)
    skills = course["skills"]
    index = next((i for i, item in enumerate(skills) if item["id"] == skill_id), None)
    if index is None:
        raise Http404("Mission not found.")
    mastered = set(course.get("progress", {}).get("mastered", []))
    if any(item["id"] not in mastered for item in skills[:index]):
        messages.info(request, "Complete the earlier missions to unlock this core skill.")
        return redirect("course_map", course_id=course_id)
    attempts = course.get("progress", {}).get("attempts", {}).get(skill_id, 0)
    owner = learner_key(request)
    return render(request, "learning/lesson.html", {
        "course": course, "skill": skills[index], "index": index, "total": len(skills),
        "attempts": attempts, "mastered": skill_id in mastered,
        "copilot": course_copilot(owner, course, "lesson", skill=skills[index], attempts=attempts),
    })


@require_POST
def submit_answer(request, course_id, skill_id):
    course = owned_course(request, course_id)
    if course is None:
        return redirect("home")
    skill = next((item for item in course["skills"] if item["id"] == skill_id), None)
    if not skill:
        raise Http404("Mission not found.")
    mastered = set(course.get("progress", {}).get("mastered", []))
    index = next(i for i, item in enumerate(course["skills"]) if item["id"] == skill_id)
    if any(item["id"] not in mastered for item in course["skills"][:index]):
        return redirect("course_map", course_id=course_id)
    answer = request.POST.get("answer", "")[:500]
    correct = answer == skill["answer"]
    updated = record_answer(course_id, learner_key(request), skill_id, answer, correct)
    if not updated:
        raise Http404("Course not found.")
    if correct:
        new_mastered = set(updated["progress"].get("mastered", []))
        next_skill = next((item for item in course["skills"][index + 1:] if item["id"] not in new_mastered), None)
        if next_skill:
            messages.success(request, "Mission mastered! +20 XP. The next skill is unlocked.")
            return redirect("lesson", course_id=course_id, skill_id=next_skill["id"])
        messages.success(request, "All core skills mastered! Your boss challenge is unlocked.")
        return redirect("boss", course_id=course_id)
    messages.error(request, "Not quite. Try the hint, then take another shot.")
    return redirect("lesson", course_id=course_id, skill_id=skill_id)


def boss(request, course_id):
    course = owned_course(request, course_id)
    mastered = set(course.get("progress", {}).get("mastered", []))
    if len(mastered) < len(course["skills"]):
        messages.info(request, "Master every required skill before the boss challenge.")
        return redirect("course_map", course_id=course_id)
    return render(request, "learning/boss.html", {
        "course": course, "boss": course["boss"],
        "complete": course.get("progress", {}).get("complete", False),
        "copilot": course_copilot(learner_key(request), course, "boss"),
    })


@require_POST
def submit_boss(request, course_id):
    course = owned_course(request, course_id)
    mastered = set(course.get("progress", {}).get("mastered", []))
    if len(mastered) < len(course["skills"]):
        return redirect("course_map", course_id=course_id)
    answer = request.POST.get("answer", "")[:500]
    correct = answer == course["boss"]["answer"]
    record_boss_answer(course_id, learner_key(request), answer, correct)
    if correct:
        messages.success(request, "Boss cleared! You demonstrated the full learning goal. +50 bonus XP.")
        return redirect("course_map", course_id=course_id)
    messages.error(request, "The boss is still standing. Check the hint and try again.")
    return redirect("boss", course_id=course_id)
