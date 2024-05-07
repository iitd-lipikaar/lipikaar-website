from os.path import splitext as path_splitext

from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser

from ocr.cache import save_image_or_pdf_to_cache
from ocr.config import language_to_indic_transliteration_script
from ocr.language_ocr_models.main import OCR
from ocr.responses import (
    perform_ocr_responses,
    service_responses,
)
from ocr.tasks import perform_ocr_for_service
from ocr_app.settings import NEW_OCR_ACCEPTED_FILE_EXTENSIONS


SERVICE_API_KEY = "foo-the-service"

ocr_instance = OCR()
ocr_instance_config = ocr_instance.get_config()


class ServiceConfigAPIView(APIView): # Done
    permission_classes = [AllowAny]

    def get(self, request):
        # Validate API Key
        api_key_header = request.META.get('HTTP_X_LIPIKAR_SERVICE_API_KEY', "")

        if api_key_header != SERVICE_API_KEY:
            return service_responses['unauthorized']()
        

        # Return Config
        return Response({
            'success': True,
            'result': {
                'config': {
                    **ocr_instance_config,
                    'transliteration': {
                        'supportedLanguages': language_to_indic_transliteration_script.keys(),
                    },
                },
            },
        }, status=status.HTTP_200_OK)


class ServiceUploadAPIView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [AllowAny]

    def post(self, request):
        # Validate API Key
        api_key_header = request.META.get('HTTP_X_LIPIKAR_SERVICE_API_KEY', "")

        if api_key_header != SERVICE_API_KEY:
            return service_responses['unauthorized']()
        

        # Validate OCR Config
        ocr_config = {
            'document_parser': request.query_params.get('document_parser', ""),
            'text_recognizer': request.query_params.get('text_recognizer', ""),
        }

        ocr_config_invalid_keys = ocr_instance.validate_config(ocr_config)
        if len(ocr_config_invalid_keys) > 0:
            return perform_ocr_responses['invalidConfig'](ocr_config_invalid_keys)
        

        # Validate Request Files
        file = request.FILES.get('file', None)
        if file == None:
            return perform_ocr_responses['noFile']()
        
        _filename, file_extension = path_splitext(file.name)
        if file_extension not in NEW_OCR_ACCEPTED_FILE_EXTENSIONS:
            return perform_ocr_responses['unacceptedFileExtension']()
        
        image_filenames = save_image_or_pdf_to_cache(file, file_extension)
        full_ocr_config = ocr_instance.get_full_ocr_config(ocr_config['document_parser'], ocr_config['text_recognizer'])

        perform_ocr_result = perform_ocr_for_service.apply_async(
            kwargs={
                'image_filenames': image_filenames,
                'ocr_config': full_ocr_config,
            }
        )
        detections = perform_ocr_result.get()

        if detections == False:
            return Response({
                'success': False,
                'error': {
                    'message': "Failed to perform OCR on file.",
                },
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'success': True,
            'result': {
                'detections': detections,
            },
        }, status=status.HTTP_200_OK)
