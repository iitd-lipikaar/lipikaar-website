from django.contrib.auth.models import AbstractUser
from django.db import models

from ocr_app import settings


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True, max_length=255)
    can_login = models.BooleanField(default=False)
    can_compute = models.BooleanField(default=False)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    organization = models.CharField(max_length=255)
    credits = models.FloatField(default=0.0, blank=False)
    credits_refresh_policy = models.TextField(default="None", blank=False)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username


class Upload(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=255)
    detection_ids = models.TextField()
    processing_status = models.CharField(max_length=255)
    is_cancelled = models.BooleanField(default=False)
    upload_type = models.CharField(max_length=255)


class Detection(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE)
    image_filename = models.CharField(max_length=255)
    document_parser = models.CharField(max_length=255)
    parsing_postprocessor = models.CharField(max_length=255)
    text_recognizer = models.CharField(max_length=255)
    original_detections = models.TextField()
    detections = models.TextField()
  