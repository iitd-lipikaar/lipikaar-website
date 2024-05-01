from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from ocr.views import (
    TestAPIView,
    RegisterAPIView,
    # Custom DRF simple jwt views
    CustomTokenObtainPairView,
    CustomTokenRefreshView,    
    LogoutAPIView,
    ResetPasswordAPIView,
    ConfigAPIView,
    UploadAPIView,
    UploadsHistoryAPIView,
    CustomOCRAPIView,
    DetectionAPIView,
    MergeUploadsAPIView,
    UploadChangeFilenameAPIView,
    CancelUploadAPIView,
    ImportSingleUploadAPIView,
    ExportUploadsAPIView,
    PDFGenerationAPIView,
    TransliterateAPIView,
    ServiceUploadAPIView,
    UserCreditsAPIView,
    ServiceConfigAPIView,
)


urlpatterns = [
    # OCR Views
    path('test/', TestAPIView.as_view(), name='test'),
    path('auth/register/', RegisterAPIView.as_view(), name='register'),
    path('auth/reset-password/', ResetPasswordAPIView.as_view(), name='reset_password'),
    path('ctr/', CustomTokenRefreshView.as_view(), name='ctr'),
    path('config/', ConfigAPIView.as_view(), name='config'),
    path('uploads/', UploadAPIView.as_view(), name='uploads'),
    path('uploads/history/', UploadsHistoryAPIView.as_view(), name='uploads_history'),
    path('custom-ocr/', CustomOCRAPIView.as_view(), name='custom_ocr'),
    path('detections/', DetectionAPIView.as_view(), name='detections'),
    path('uploads/merge/', MergeUploadsAPIView.as_view(), name='upload_merge'),
    path('uploads/change-filename/', UploadChangeFilenameAPIView.as_view(), name='upload_change_filename'),
    path('uploads/cancel/', CancelUploadAPIView.as_view(), name='cancel_upload'),
    path('uploads/import-single/', ImportSingleUploadAPIView.as_view(), name='import_single'),
    path('utils/generate-pdf/', PDFGenerationAPIView.as_view(),name='generate_pdf'),
    path('utils/transliterate/',TransliterateAPIView.as_view(),name='transliterate'),
    path('user/credits/', UserCreditsAPIView.as_view(), name='user_credits'),

    # Lipikar Services
    path('services/config/', ServiceConfigAPIView.as_view(), name='config'),
    path('services/new-ocr/',ServiceUploadAPIView.as_view(),name='service_new_ocr'),
    
    # path('uploads/export/', ExportUploadsAPIView.as_view(), name='export_uploads'),
    
    # Custom DRF simple jwt views
    path('auth/login/', CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path('auth/token/refresh/', CustomTokenRefreshView.as_view(), name="token_refresh"),
    path('auth/logout/', LogoutAPIView.as_view(), name="logout"),
]
