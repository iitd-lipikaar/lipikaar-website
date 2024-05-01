from django.urls import path, re_path

from frontend_core.views import index

urlpatterns = [
    path('', index, name="index"),
    re_path(r"^$", index, name="index"),
    re_path(r"^(?:.*)/?$", index, name="index"),
]
