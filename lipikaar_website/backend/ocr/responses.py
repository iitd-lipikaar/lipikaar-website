from rest_framework import status
from rest_framework.response import Response

from ocr_app.settings import (
    BACKEND_VERSION,
    FRONTEND_VERSION,
    PAGE_LIMIT_PER_USER_PER_DAY,
)

from ocr_app.settings import NEW_OCR_ACCEPTED_FILE_EXTENSIONS

test_response = Response({
    'success': True,
    'result': {
        'message': "Server is running.",
        'version': {
            'backend': BACKEND_VERSION,
            'frontend': FRONTEND_VERSION,
        },
    },
}, status=status.HTTP_200_OK)

def generate_validation_errors_response(location, validation_errors):
    return Response({
        'success': False,
        'error': {
            'errorCode': 2,
            'location': location,
            'validationErrors': validation_errors,
        },
    }, status=status.HTTP_400_BAD_REQUEST)

def generate_user_cannot_compute_error_response():
    return Response({
        'success': False,
        'error': {
            "errorCode": 0,
            "message": "User does not have compute permission."
            }            
    }, status=status.HTTP_401_UNAUTHORIZED)

user_daily_upload_limit_reached_response = Response({
    'success': False,
    'error': {
        'errorCode': 0,
        'message': f"Cannot process upload: processing this file will cross your daily upload limit of {PAGE_LIMIT_PER_USER_PER_DAY} pages. Please process tomorrow.",
    }
}, status=status.HTTP_429_TOO_MANY_REQUESTS)

def generate_invalid_ocr_config_response(key):
    return Response({
        'success': False,
        'error': {
            'errorCode': 2,
            'message': f"Invalid {key}.",
        },
    }, status=status.HTTP_400_BAD_REQUEST)

queue_full_response = Response({
    'success': False,
    'error': {
        'errorCode': 0,
        'message': "Upload queue full. Please try again in a few minutes.",
    }
}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

def generate_invalid_id_response(table_name):
    return Response({
        'success': False,
        'error': {
            "errorCode": 0,
            "message": f"Invalid {table_name} id.",
        },
    }, status=status.HTTP_400_BAD_REQUEST)

invalid_credentials_response = Response({
    'success': False,
    'error': {
        'errorCode': 0,
        'message': "Invalid credentials."
    }
}, status=status.HTTP_401_UNAUTHORIZED)


def generate_invalid_ocr_config_response2(keys):
    return Response({
        'success': False,
        'error': {
            'errorCode': 2,
            'message': f"Invalid {str(keys)}.",
        },
    }, status=status.HTTP_400_BAD_REQUEST)

def generate_ocr_no_file_response():
    return Response({
        'success': False,
        'error': {
            "errorCode": 0,
            "message": "No file given."
            }            
    }, status=status.HTTP_400_BAD_REQUEST)

def generate_ocr_unaccepted_file_extension_response():
    return Response({
        'success': False,
        'error': {
            "errorCode": 0,
            "message": f"Unacceptable file format. Only {str(NEW_OCR_ACCEPTED_FILE_EXTENSIONS)} files are accepted."
            }            
    }, status=status.HTTP_400_BAD_REQUEST)

perform_ocr_responses = {
    'invalidConfig': generate_invalid_ocr_config_response2,
    'noFile': generate_ocr_no_file_response,
    'unacceptedFileExtension': generate_ocr_unaccepted_file_extension_response,
}


def generate_unauthorized_service_request_response():
    return Response({
        'success': False,
        'error': {
            'message': "Invalid Service API Key.",
        },
    }, status=status.HTTP_401_UNAUTHORIZED)

service_responses = {
    'unauthorized': generate_unauthorized_service_request_response,
}
