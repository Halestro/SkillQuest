"""SQLite persistence for roadmaps, generated courses, and learner progress."""

from learning.models import Attempt, CourseCompletion, SkillState, StoredCourse, StoredRoadmap


def _roadmap_document(item):
    return {
        "id": item.roadmap_id,
        "learner_key": item.learner_key,
        "prompt": item.prompt,
        "roadmap": item.body,
        "status": item.status,
        "course_id": item.course_id,
        "created_at": item.created_at,
    }


def save_roadmap(roadmap_id, owner, prompt, roadmap):
    StoredRoadmap.objects.update_or_create(
        roadmap_id=roadmap_id,
        defaults={"learner_key": owner, "prompt": prompt, "body": roadmap, "status": "roadmap", "course_id": ""},
    )


def get_roadmap(roadmap_id, owner):
    item = StoredRoadmap.objects.filter(roadmap_id=roadmap_id, learner_key=owner).first()
    return _roadmap_document(item) if item else None


def list_roadmaps(owner, limit=6):
    return [_roadmap_document(item) for item in StoredRoadmap.objects.filter(
        learner_key=owner, status="roadmap"
    ).order_by("-created_at")[:limit]]


def mark_roadmap_gamified(roadmap_id, owner, course_id):
    StoredRoadmap.objects.filter(roadmap_id=roadmap_id, learner_key=owner).update(
        status="gamified", course_id=course_id
    )


def save_course(course, owner):
    StoredCourse.objects.update_or_create(
        course_id=course["id"], defaults={"learner_key": owner, "body": course}
    )


def _course_document(item):
    states = SkillState.objects.filter(learner_key=item.learner_key, course_id=item.course_id)
    mastered = [state.skill_id for state in states if state.mastered]
    attempts = {state.skill_id: state.attempts for state in states}
    complete = CourseCompletion.objects.filter(learner_key=item.learner_key, course_id=item.course_id).exists()
    course = dict(item.body)
    course["id"] = item.course_id
    course["progress"] = {"mastered": mastered, "attempts": attempts, "complete": complete}
    return course


def get_course(course_id, owner):
    item = StoredCourse.objects.filter(course_id=course_id, learner_key=owner).first()
    return _course_document(item) if item else None


def list_courses(owner, limit=6):
    return [_course_document(item) for item in StoredCourse.objects.filter(
        learner_key=owner
    ).order_by("-created_at")[:limit]]


def record_answer(course_id, owner, skill_id, answer, correct):
    state, _ = SkillState.objects.get_or_create(
        learner_key=owner, course_id=course_id, skill_id=skill_id
    )
    state.attempts += 1
    if correct:
        state.mastered = True
    state.save(update_fields=["attempts", "mastered", "updated_at"])
    Attempt.objects.create(
        learner_key=owner, course_id=course_id, skill_id=skill_id,
        answer=answer, correct=correct,
    )
    return get_course(course_id, owner)


def record_boss_answer(course_id, owner, answer, correct):
    Attempt.objects.create(
        learner_key=owner, course_id=course_id, skill_id="boss",
        answer=answer, correct=correct,
    )
    if correct:
        CourseCompletion.objects.get_or_create(learner_key=owner, course_id=course_id)
    return get_course(course_id, owner)
