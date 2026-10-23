from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Attempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("learner_key", models.CharField(db_index=True, max_length=64)),
                ("course_id", models.CharField(db_index=True, max_length=64)),
                ("skill_id", models.CharField(max_length=64)),
                ("answer", models.TextField(blank=True)),
                ("correct", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="CourseCompletion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("learner_key", models.CharField(db_index=True, max_length=64)),
                ("course_id", models.CharField(db_index=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="SkillState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("learner_key", models.CharField(db_index=True, max_length=64)),
                ("course_id", models.CharField(db_index=True, max_length=64)),
                ("skill_id", models.CharField(max_length=64)),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("mastered", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="StoredCourse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("course_id", models.CharField(max_length=64, unique=True)),
                ("learner_key", models.CharField(db_index=True, max_length=64)),
                ("body", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddConstraint(
            model_name="coursecompletion",
            constraint=models.UniqueConstraint(fields=("learner_key", "course_id"), name="unique_course_completion"),
        ),
        migrations.AddConstraint(
            model_name="skillstate",
            constraint=models.UniqueConstraint(fields=("learner_key", "course_id", "skill_id"), name="unique_learner_course_skill"),
        ),
    ]
