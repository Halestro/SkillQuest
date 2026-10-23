from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("roadmaps/create/", views.create_roadmap, name="create_roadmap"),
    path("roadmaps/<str:roadmap_id>/", views.roadmap_review, name="roadmap_review"),
    path("roadmaps/<str:roadmap_id>/gamify/", views.gamify, name="gamify"),
    path("courses/<str:course_id>/", views.course_map, name="course_map"),
    path("courses/<str:course_id>/skills/<str:skill_id>/", views.lesson, name="lesson"),
    path("courses/<str:course_id>/skills/<str:skill_id>/answer/", views.submit_answer, name="submit_answer"),
    path("courses/<str:course_id>/boss/", views.boss, name="boss"),
    path("courses/<str:course_id>/boss/answer/", views.submit_boss, name="submit_boss"),
]
