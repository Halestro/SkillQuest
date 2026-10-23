from django.db import models


class Attempt(models.Model):
    learner_key = models.CharField(max_length=64, db_index=True)
    course_id = models.CharField(max_length=64, db_index=True)
    skill_id = models.CharField(max_length=64)
    answer = models.TextField(blank=True)
    correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class SkillState(models.Model):
    learner_key = models.CharField(max_length=64, db_index=True)
    course_id = models.CharField(max_length=64, db_index=True)
    skill_id = models.CharField(max_length=64)
    attempts = models.PositiveIntegerField(default=0)
    mastered = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["learner_key", "course_id", "skill_id"], name="unique_learner_course_skill")]


class StoredCourse(models.Model):
    course_id = models.CharField(max_length=64, unique=True)
    learner_key = models.CharField(max_length=64, db_index=True)
    body = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)


class CourseCompletion(models.Model):
    learner_key = models.CharField(max_length=64, db_index=True)
    course_id = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["learner_key", "course_id"], name="unique_course_completion")]


class StoredRoadmap(models.Model):
    roadmap_id = models.CharField(max_length=64, unique=True)
    learner_key = models.CharField(max_length=64, db_index=True)
    prompt = models.TextField()
    body = models.JSONField()
    status = models.CharField(max_length=20, default="roadmap")
    course_id = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
