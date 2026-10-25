from django.urls import path
from routing import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/health/", views.health, name="health"),
    path("api/config/", views.config, name="config"),
    path("api/reverse-geocode/", views.reverse_geocode, name="reverse_geocode"),
    path("api/plan/", views.plan, name="plan"),
    path("api/heatmap/", views.heatmap, name="heatmap"),
]
