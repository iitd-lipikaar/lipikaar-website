import os
import json
import time
from math import ceil
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from indic_transliteration import sanscript

from ocr_app.settings import (
    MEDIA_ROOT,
    CACHE_ROOT,
    NEW_UPLOAD_QUEUE_SIZE_LIMIT,
    BACKEND_VERSION,
    FRONTEND_VERSION,
    GET_MULTIPLE_UPLOADS_LIMIT,
    CAN_DELETE_MULTIPLE_UPLOADS_IN_SINGLE_REQUEST,
)
SERVICE_API_KEY = "foo-the-service"
from ocr.config import (
    language_to_indic_transliteration_script,
)
from ocr.serializers import (
    RegisterUserSerializer,
    CustomTokenObtainPairSerializer,
    CustomTokenRefreshSerializer,
    UploadSerializer,
    DetectionSerializer,
    DeleteUploadSerializer,
    ResetPasswordSerializer,
    CustomOCRSerializer,
    UploadChangeFilenameSerializer,
    MergeUploadsSerializer,
    IdSerializer,
    UploadIdSerializer,
    DetectionFilenameOnlySerializer,
    UploadIdsSerializer,
    PDFGenerationInputSerializer,
    TransliterateInputSerializer,
)
from ocr.models import (
    Upload,
    Detection
    )
from ocr.db_utils import (
    zip_upload,
    zip_uploads,
)
from ocr.cache import (
    save_image_or_pdf_to_cache,
    delete_multiple_files_from_cache,
    load_frontend_build_file_into_cache,
    download_from_cloud_storage_to_cache,
)
from ocr.cloud_storage import (
    upload_to_cloud_storage_from_cache,
    delete_from_cloud_storage,
    duplicate_inside_cloud_storage
)
from ocr.lipikar_utils.pdf_generation import (
    generate_pdf_for_images_and_detections,
)
from ocr.utils import (
    get_filename,
    get_extension,
    upload_processing_status_generators,
    try_parse_json_str,
    generate_new_upload_file_name,
    generate_unique_filename,
)
from ocr.responses import (
    test_response,
    generate_validation_errors_response,
    generate_user_cannot_compute_error_response,
    user_daily_upload_limit_reached_response,
    generate_invalid_ocr_config_response,
    queue_full_response,
    generate_invalid_id_response,
    invalid_credentials_response,
)
from ocr.language_ocr_models.main import (
    OCR
)
ocr_instance = OCR()
ocr_instance_config = ocr_instance.get_config()
from ocr.tasks import (
    perform_ocr_for_new_upload,
    perform_ocr_for_service,
    re_run_ocr_for_bbox,
)
from ocr.QueueManager import QueueManager


class TestAPIView(APIView): # Done
    "Get server status and application version."

    permission_classes = [AllowAny]

    def get(self, request):
        return test_response


class RegisterAPIView(APIView): # Done
    """
    Register a new user.
    Method: post
    """

    permission_classes = [AllowAny]

    def post(self, request, format=None):
        body_serializer = RegisterUserSerializer(data=request.data)
        if not body_serializer.is_valid():
            return generate_validation_errors_response('body', body_serializer.errors)
        
        user = body_serializer.save()

        return Response({
            'success': True,
            'message': 'User created successfully.'
        }, status=status.HTTP_201_CREATED)


class CustomTokenObtainPairView(TokenObtainPairView): # Done
    "Obtain Access and Refresh tokens."

    serializer_class = CustomTokenObtainPairSerializer


class CustomTokenRefreshView(TokenRefreshView): # Done
    "Refresh Access token."

    serializer_class = CustomTokenRefreshSerializer


class LogoutAPIView(APIView):
    def post(self, request):
        token = RefreshToken(request.data.get('refresh'))
        token.blacklist()
        return Response({
            'success': True,
        }, status=status.HTTP_200_OK)


class ResetPasswordAPIView(APIView): # Done
    """
    Reset user's password.
    Requires auth
    Method: post
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, format=None):
        body_serializer = ResetPasswordSerializer(data=request.data)
        if not body_serializer.is_valid():
            return generate_validation_errors_response('body', body_serializer.errors)

        # Get the request data
        username = request.data.get('username')
        current_password = request.data.get('currentPassword')
        new_password = request.data.get('newPassword')

        # Authenticate the user
        user = authenticate(username=username, password=current_password)

        if user == None: # user credentials are invalid
            return invalid_credentials_response

        if user != request.user: # someone is trying to reset someone else's password
            return invalid_credentials_response        

        # update the password and respond with success
        user.set_password(new_password)
        user.save()

        return Response({
            'success': True,
        }, status=status.HTTP_200_OK)


class ConfigAPIView(APIView): # Done
    """
    Get OCR config
    Requires auth
    Method: get
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
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


class UploadAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get_parser_classes(self):
        if self.request.method == 'POST':
            return [MultiPartParser]
        elif self.request.method == 'DELETE':
            return [JSONParser]
        else:
            return [JSONParser]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UploadSerializer
        elif self.request.method == 'DELETE':
            return DeleteUploadSerializer
        
        return UploadSerializer

    def get(self, request):
        user = request.user # get the authenticated user

        id = request.query_params.get('id', None)
        processing_status_only = request.query_params.get('processing_status_only', None)
        latest_upload_id = request.query_params.get('latest_upload_id', float('inf'))
        
        if id == None:
            num_uploads_of_user = Upload.objects.filter(user=user).count()

            if latest_upload_id != float('inf'):
                uploads = Upload.objects.filter(user=user, id__lte=latest_upload_id).order_by('-id')[:GET_MULTIPLE_UPLOADS_LIMIT]
            else:
                uploads = Upload.objects.filter(user=user).order_by('-id')[:GET_MULTIPLE_UPLOADS_LIMIT]

            serializer = UploadSerializer(uploads, many=True)
            return Response({
                'success': True,
                'result': {
                    'uploads': serializer.data,
                    'numUploadsOfUser': num_uploads_of_user,

                },
            }, status=status.HTTP_200_OK)

        if processing_status_only == "1":
            if QueueManager.check_if_upload_is_cancelled(id):
                return Response({
                    'success': True,
                    'result': {
                        'uploadId': id,
                        'processingStatus': upload_processing_status_generators['cancelled']()
                    }
                })

            try:
                upload_processing_status = QueueManager.get_upload_processing_status(id)
                if upload_processing_status is not None:
                    return Response({
                        'success': True,
                        'result': {
                            'uploadId': id,
                            'processingStatus': upload_processing_status,
                        }
                    })

                upload_processing_status = Upload.objects.filter(user=user, id=id).values('processing_status').first()['processing_status']
                return Response({
                    'success': True,
                    'result': {
                        'uploadId': id,
                        'processingStatus': upload_processing_status,
                    }
                })
            except Exception as e:
                print(e)
                return Response({
                    'success': False,
                    'error': {
                        'errorCode': 0,
                        'message': f"Upload with id: {id} not found for user."
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

        try:
            upload_object = Upload.objects.get(user=user, id=id)
            serializer = UploadSerializer(upload_object)
            return Response({
                'success': True,
                'result': {
                    'upload': serializer.data
                }
            })
        except:
            return Response({
                'success': False,
                'error': {
                    'errorCode': 0,
                    'message': f"Upload with id: {id} not found for user."
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        user = request.user # get the authenticated user
        if not user.can_compute: # check if user can compute
            return Response({
                'success': False,
                'error': {
                    "errorCode": 0,
                    "message": "User does not have compute permission."
                    }            
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        text_recognizer = request.query_params.get('text_recognizer')
        # if not text_recognizer in ocr_instance_config['ocr_config']: # TODO: Add this check
        #     return generate_invalid_ocr_config_response('text_recognizer')

        document_parser = request.query_params.get('document_parser')
        # if not document_parser in ocr_instance_config['ocr_config'][text_recognizer]: # TODO: Add this check
        #     return generate_invalid_ocr_config_response('document_parser')

        parsing_postprocessor = request.query_params.get('parsing_postprocessor')

        if QueueManager.get_num_uploads_in_queue() > NEW_UPLOAD_QUEUE_SIZE_LIMIT:
            print(QueueManager.get_num_uploads_in_queue())
            return queue_full_response
        
        file = request.FILES.get('file')
        template_filename = request.data.get('file')

        if file != None:
            filename, file_extension = os.path.splitext(file.name)
            if file_extension not in [".pdf", ".jpg", ".jpeg"]:
                return Response({
                    'success': False,
                    'error': {
                        "errorCode": 0,
                        "message": "Unacceptable file format. Only .pdf, .jpg, or .jpeg files are accepted."
                        }            
                }, status=status.HTTP_400_BAD_REQUEST)
            
            image_filenames = save_image_or_pdf_to_cache(file, file_extension) # get the image file names
        elif template_filename != None:
            loaded_frontend_template_filename = load_frontend_build_file_into_cache(template_filename)
            if loaded_frontend_template_filename == None:
                return Response({
                    'success': False,
                    'error': {
                        "errorCode": 0,
                        "message": "Invalid Template Image."
                        }            
                }, status=status.HTTP_400_BAD_REQUEST)
            image_filenames = [load_frontend_build_file_into_cache(template_filename)]
        else:
            return Response({
                'success': False,
                'error': {
                    "errorCode": 0,
                    "message": "No file given."
                    }            
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # User limit on processing

        if float(len(image_filenames)) > user.credits:
            delete_multiple_files_from_cache(image_filenames)
            return Response({
                'success': False,
                'error': {
                    'errorCode': 0,
                    'message': "You do not have enough Page Credits to process this file.",
                }
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        new_upload_processing_status = upload_processing_status_generators['queued'](len(image_filenames))

        filename = file.name if file != None else template_filename

        new_upload = Upload.objects.create(
            user=user,
            filename=filename,
            detection_ids=json.dumps([]),
            processing_status=new_upload_processing_status,
            upload_type="original"
            )

        ocr_config = ocr_instance.get_full_ocr_config(document_parser, text_recognizer)

        print(ocr_config)

        perform_ocr_for_new_upload.delay(
            new_upload.id,
            user.id,
            1,
            len(image_filenames),
            image_filenames,
            ocr_config
        )

        QueueManager.update_upload_processing_status(new_upload.id, new_upload_processing_status)

        return Response({
            'success': True,
            'result': {
                'upload': {
                    'id': new_upload.id,
                },
            },
        }, status=status.HTTP_206_PARTIAL_CONTENT)
    
    def delete(self, request): # done
        user = request.user # get the authenticated user

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.data)

        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': {
                        'errorCode': 2,
                        'validationErrors': serializer.errors
                   } 
                }, status=status.HTTP_400_BAD_REQUEST)
        
        upload_ids = request.data.get('uploadIds')
        if not CAN_DELETE_MULTIPLE_UPLOADS_IN_SINGLE_REQUEST and len(upload_ids) > 1:
            return Response({
                'success': False,
                'error': {
                        'errorCode': 2,
                        'message': "Deletion of multiple uploads in a single request is currently prohibited."
                   } 
                }, status=status.HTTP_400_BAD_REQUEST)

        # for each upload
            # check if the upload is created by this user
            # get all detections for the upload
            # for each detection
                # delete the detection image from cloud storage
                # delete the detection
            # delete the upload
        for upload_id in upload_ids:
            try:
                upload_object = Upload.objects.get(user=user, id=upload_id)
            except:
                return Response({
                    'success': False,
                    'error': {
                        'errorCode': 0,
                        'message': f"Upload with id {upload_id} not found for the user."
                    }
                    }, status=status.HTTP_400_BAD_REQUEST)

            zip_upload(upload_id, "deleted-uploads")
            
            # if upload_object.upload_type === "original":
            detection_objects = Detection.objects.filter(upload=upload_object)
            for detection_object in detection_objects:
                if not delete_from_cloud_storage(f"detection_images/{detection_object.image_filename}"):
                    # error deleting from cloud storage
                    # return Response({
                    #     'success': False,
                    #     'error': {
                    #         'errorCode': 0,
                    #         'message': "Cloud storage error"
                    #     }
                    # }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    pass
                detection_object.delete()
            
            upload_object.delete()
        
        return Response({
                'success': True,
            }, status=status.HTTP_200_OK)


class UserCreditsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        user = request.user

        return Response({
            'success': True,
            'result': {
                'credits': user.credits,
            },
        }, status=status.HTTP_200_OK)


class UploadsHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get(self, request):
        user = request.user # get the authenticated user

        page_num = int(request.query_params.get('page_num', 1))
        num_uploads_per_page = int(request.query_params.get('num_uploads_per_page', GET_MULTIPLE_UPLOADS_LIMIT))

        num_total_uploads_of_user = Upload.objects.filter(user=user).count()
        current_page_first_upload_num = num_uploads_per_page * (page_num - 1) + 1
        current_page_last_upload_num = min(num_total_uploads_of_user, current_page_first_upload_num + num_uploads_per_page - 1)
        uploads = Upload.objects.filter(user=user).order_by('-id')[current_page_first_upload_num - 1 : current_page_last_upload_num]

        serializer = UploadSerializer(uploads, many=True)
        return Response({
            'success': True,
            'result': {
                'uploads': serializer.data,
                'currentPage': page_num,
                'totalPages': ceil(num_total_uploads_of_user / num_uploads_per_page),
                'currentPageFirstUploadNum': current_page_first_upload_num,
                'currentPageLastUploadNum': current_page_last_upload_num,
                'numTotalUploadsOfUser': num_total_uploads_of_user,
            },
        }, status=status.HTTP_200_OK)


class CustomOCRAPIView(APIView): # Done
    parser_classes = [JSONParser]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        user = request.user # get the authenticated user

        query_serializer = CustomOCRSerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return generate_validation_errors_response('query', query_serializer.errors)

        detection_id = request.query_params.get('detectionId')
        x_min = round(float(request.query_params.get('xMin')))
        y_min = round(float(request.query_params.get('yMin')))
        x_max = round(float(request.query_params.get('xMax')))
        y_max = round(float(request.query_params.get('yMax')))
        rotation = float(request.query_params.get('rotation'))
        
        try:
            detection = Detection.objects.get(user=user, id=detection_id)
        except:
            return generate_invalid_id_response("detection")
        
        image_filename = detection.image_filename

        bbox = {
            'x_min': x_min,
            'y_min': y_min,
            'x_max': x_max,
            'y_max': y_max,
            'rotation': rotation,
        }

        re_run_ocr_async_result = re_run_ocr_for_bbox.apply_async(
            kwargs={
                'image_filename': image_filename,
                'bbox': bbox,
                'text_recognizer': json.loads(detection.text_recognizer),
                }
        )
        recognized_text = re_run_ocr_async_result.get()

        return Response({
            'success': True,
            'result': {
                'recognized_text': recognized_text,
            },
        }, status=status.HTTP_200_OK)


class DetectionAPIView(APIView): # Done
    serializer_class = UploadSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        user = request.user # get the authenticated user

        query_serializer = UploadIdSerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return generate_validation_errors_response('query', query_serializer.errors)

        upload_id = request.query_params.get('uploadId')
        filenames_only = request.query_params.get('filenamesOnly', None)

        # check if there is an upload with the given id and user
        try:
            upload_object = Upload.objects.get(user=user, id=upload_id)
        except:
            return generate_invalid_id_response("upload")
        
        detection_objects = []

        if filenames_only == "1":
            for detection_id in json.loads(upload_object.detection_ids):
                detection_object = Detection.objects.filter(id=detection_id).values('id', 'image_filename').first()
                detection_objects.append(detection_object)
            
            serializer = DetectionFilenameOnlySerializer(detection_objects, many=True)
        else:
            for detection_id in json.loads(upload_object.detection_ids):
                detection_object = Detection.objects.filter(id=detection_id).first()
                detection_objects.append(detection_object)
            
            serializer = DetectionSerializer(detection_objects, many=True)
        
        return Response({
            'success': True,
            'result': {
                'detections': serializer.data
            }
        })
    
    def patch(self, request):
        user = request.user # get the authenticated user
        # if not user.can_compute:
        #     return generate_user_cannot_compute_error_response()

        query_serializer = IdSerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return generate_validation_errors_response('query', query_serializer.errors)

        id = request.query_params.get('id')

        detections = request.data['detections']
        detection_object = Detection.objects.get(id=id)

        # update the detection object and save it
        detection_object.detections = json.dumps(detections).replace("\\\\","\\")
        detection_object.save()
            
        # serialize and return the updated object
        serializer = DetectionSerializer(detection_object)
        return Response({
            'success': True,
            'result': {
                'detection': serializer.data
            }
        }, status=status.HTTP_200_OK)


class MergeUploadsAPIView(APIView): # Done
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        user = request.user # get the authenticated user
        if not user.can_compute:
            return generate_user_cannot_compute_error_response()

        body_serializer = MergeUploadsSerializer(data=request.data)
        if not body_serializer.is_valid():
            return generate_validation_errors_response('body', body_serializer.errors)
        
        filename = request.data.get('filename')
        new_filename_without_extension = get_filename(filename)
        upload_ids = request.data.get('uploadIds')
        combined_detection_ids = []

        # for each upload
            # check if the upload is created by this user
            # get all the detections for that upload and add them to the combined detections
        for upload_id in upload_ids:
            try:
                upload_object = Upload.objects.get(user=user, id=upload_id)
            except:
                return generate_invalid_id_response("upload")
            
            combined_detection_ids += json.loads(upload_object.detection_ids)

        new_upload = Upload.objects.create(
            user=user,
            filename=f"{new_filename_without_extension}.pdf",
            detection_ids=json.dumps([]),
            processing_status=upload_processing_status_generators['completed'](),
            upload_type="merged"
            )

        new_detection_ids = []

        # create new detection objects, this is required since the user may delete the old upload
        for detection_id in combined_detection_ids:
            try:
                detection_object = Detection.objects.get(id=detection_id)
            except:
                return Response({
                    'success': False,
                    'error': {
                        'errorCode': 0,
                        'message': f"Could not find Detection object with id {detection_id}.",
                    },
                }, status=status.HTTP_201_CREATED) 

            new_filename = duplicate_inside_cloud_storage(detection_object.image_filename, "detection_images")
            
            new_detection = Detection.objects.create(
                user=user,
                upload=new_upload,
                image_filename=os.path.basename(new_filename),
                document_parser=detection_object.document_parser,
                parsing_postprocessor=detection_object.parsing_postprocessor,
                text_recognizer=detection_object.text_recognizer,
                original_detections=detection_object.original_detections,
                detections=detection_object.detections
            )
            new_detection_ids.append(new_detection.id)
        
        new_upload.detection_ids = new_detection_ids
        new_upload.save()

        serializer = UploadSerializer(new_upload)
        return Response({
            'success': True,
            'result': {
                'upload': serializer.data
            }
        }, status=status.HTTP_201_CREATED)


class UploadChangeFilenameAPIView(APIView): # Done
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def patch(self, request):
        user = request.user # get the authenticated user

        query_serializer = IdSerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return generate_validation_errors_response('query', query_serializer.errors)

        body_serializer = UploadChangeFilenameSerializer(data=request.data)
        if not body_serializer.is_valid():
            return generate_validation_errors_response('body', body_serializer.errors)

        id = request.query_params.get('id')
        filename = body_serializer.validated_data.get('filename')

        try:
            upload = Upload.objects.get(user=user, id=id)
        except:
            return generate_invalid_id_response("upload")

        saved_filename_extension = get_extension(upload.filename)
        new_filename_without_extension = get_filename(filename)

        upload.filename = new_filename_without_extension + saved_filename_extension
        upload.save()

        serializer = UploadSerializer(upload)
        return Response({
            'success': True,
            'result': {
                'upload': serializer.data
            }
        }, status=status.HTTP_200_OK)


class CancelUploadAPIView(APIView): # Done
    def patch(self, request):
        user = request.user # get the authenticated user

        query_serializer = IdSerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return generate_validation_errors_response('query', query_serializer.errors)

        upload_id = request.query_params.get('id')

        try:
            upload = Upload.objects.get(user=user, id=upload_id)
        except:
            return generate_invalid_id_response("upload")

        QueueManager.cancel_upload(upload_id)

        response_serializer = UploadSerializer(upload)
        return Response({
            'success': True,
            'result': {
                'upload': response_serializer.data,
            },
        }, status=status.HTTP_200_OK)


class ImportSingleUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get_parser_classes(self):
        if self.request.method == 'POST':
            return [MultiPartParser]
        else:
            return [JSONParser]

    def post(self, request):
        user = request.user # get the authenticated user

        detections_json_file = request.FILES.get('detections.json', None)
        if detections_json_file is None:
            return generate_validation_errors_response('body', "File: detections.json not provided.")
        try:
            detections = json.load(detections_json_file)
        except json.JSONDecodeError:
            return generate_validation_errors_response('body', "File: detections.json is not valid JSON.")

        upload_details_json_file = request.FILES.get('uploadDetails.json', None)
        if upload_details_json_file is None:
            upload_details = {}
        else:
            try:
                upload_details = json.load(upload_details_json_file)
            except json.JSONDecodeError:
                return generate_validation_errors_response('body', "File: uploadDetails.json is not valid JSON.")
        
        cached_detection_images_file_names = []
        for i, detection_object in enumerate(detections):
            detection_object_detections = detection_object.get('detections', None)
            detection_object_original_detections = detection_object.get('original_detections', None)

            if detection_object_detections is None and detection_object_original_detections is None:
                return generate_validation_errors_response('body', f"File: detections.json has neither detections nor original_detections for detection index {i}.")
            elif detection_object_detections is None and detection_object_original_detections is not None:
                detection_object['detections'] = detection_object_original_detections
            elif detection_object_detections is not None and detection_object_original_detections is None:
                detection_object['original_detections'] = detection_object_detections

            if detection_object.get('image_filename', None) is None:
                return generate_validation_errors_response('body', f"File: detections.json does not have image_filename for detection index {i}.")

            if detection_object.get('text_recognizer', None) is None:
                return generate_validation_errors_response('body', f"File: detections.json does not have text_recognizer for detection index {i}.")

            detection_image_file = request.FILES.get(f"{detection_object['image_filename']}", None)
            if detection_image_file is None:
                return generate_validation_errors_response('body', f"File: {detection_object['image_filename']} not provided.")
            
            filename, file_extension = os.path.splitext(detection_image_file.name)
            saved_file_names = save_image_or_pdf_to_cache(detection_image_file, file_extension)
            cached_detection_images_file_names.append(saved_file_names[0])

        upload_file_name = upload_details.get('filename', generate_new_upload_file_name(len(cached_detection_images_file_names)))
        
        new_upload = Upload.objects.create(
            user=user,
            filename=upload_file_name,
            detection_ids=json.dumps([]),
            upload_type="imported",
            is_cancelled=False,
            processing_status=upload_processing_status_generators['completed'](),
        )

        new_upload_detection_ids = []
        for i, detection_object in enumerate(detections):
            image_filename = os.path.basename(cached_detection_images_file_names[i])
            new_detection = Detection.objects.create(
                user=user,
                upload=new_upload,
                image_filename=image_filename,
                document_parser=json.dumps(detection_object.get('document_parser', '{}')),
                parsing_postprocessor="no_postprocessor",
                text_recognizer=json.dumps(detection_object['text_recognizer']),
                original_detections=json.dumps(detection_object['original_detections']),
                detections=json.dumps(detection_object['detections'])
            )

            if not upload_to_cloud_storage_from_cache(os.path.basename(image_filename), "detection_images"):
                new_detection.delete()

                new_upload.processing_status = upload_processing_status_generators['errored']()
                new_upload.save()

            print(f"Failed to upload image: {image_filename} from Cache to Cloud Storage. Upload id: {new_upload.id}")

            new_upload_detection_ids.append(new_detection.id)
            new_upload.detection_ids = json.dumps(new_upload_detection_ids)
            new_upload.save()
        
        return Response({
            'success': True,
            'result': {
                'upload': {
                    'id': new_upload.id,
                },
            },
        }, status=status.HTTP_201_CREATED)


class ExportUploadsAPIView(APIView): # Untested
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        user = request.user # get the authenticated user
        
        body_serializer = UploadIdsSerializer(data=request.data)
        if not body_serializer.is_valid():
            return generate_validation_errors_response('body', body_serializer.errors)
        
        upload_ids = request.data.get('uploadIds')

        zip_uploads_result = zip_uploads(upload_ids)

        return Response({
            'success': True,
            'result': zip_uploads_result
        }, status=status.HTTP_201_CREATED)


class PDFGenerationAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        user = request.user

        body_serializer = PDFGenerationInputSerializer(data=request.data)
        if not body_serializer.is_valid():
            return generate_validation_errors_response('body', body_serializer.errors)
        
        upload_id = body_serializer.validated_data['uploadId']
        page_numbers = body_serializer.validated_data['pageNumbers']
        pdf_generation_mode = body_serializer.validated_data['pdfGenerationMode']

        try:
            upload_object = Upload.objects.get(user=user, id=upload_id)
        except:
            return Response({
                'success': False,
                'error': {
                    "errorCode": 0,
                    "message": f"Upload with id {upload_id} not found for user."
                    }            
            }, status=status.HTTP_400_BAD_REQUEST)
        
        detection_ids = json.loads(upload_object.detection_ids)
        selected_detection_ids = [
            detection_id
            for i, detection_id in enumerate(detection_ids)
            if (i + 1) in page_numbers
        ]

        selected_detection_objects = []
        for detection_id in selected_detection_ids:
            try:
                detection_object = Detection.objects.get(user=user, id=detection_id)
                selected_detection_objects.append(detection_object)
            except:
                return Response({
                    'success': False,
                    'error': {
                        "errorCode": 0,
                        "message": f"Detection with id {detection_id} not found for user."
                        }            
                }, status=status.HTTP_400_BAD_REQUEST)
        
        pdf_generator_detections = []
        pdf_generator_image_paths = []
        
        for detection_object in selected_detection_objects:
            detection_object.detections = json.loads(detection_object.detections)

            detection_object_dict = {
                'detections': [],
            }

            for detection in detection_object.detections:
                detection_object_dict['detections'].append(detection)

            pdf_generator_detections.append(detection_object_dict)

            cached_image_name = generate_unique_filename(".jpg")
            cached_image_path = download_from_cloud_storage_to_cache(f"detection_images/{detection_object.image_filename}", cached_image_name)
            pdf_generator_image_paths.append(os.path.join(CACHE_ROOT, cached_image_path))

        generated_pdf_filename = generate_unique_filename(".pdf")
        generated_pdf_filepath = os.path.join(CACHE_ROOT, generated_pdf_filename)

        pdf_generator_kwargs = {
            'draw_bbox_borders': False,
            'fill_bboxes': pdf_generation_mode == "overlayedText",
            'write_text': pdf_generation_mode == "overlayedText",
            'write_transparent_text': pdf_generation_mode == "transparentText",
        }

        generate_pdf_for_images_and_detections(
            pdf_generator_detections,
            generated_pdf_filepath,
            pdf_generator_image_paths,
            title=generated_pdf_filename,
            **pdf_generator_kwargs
        )

        if not upload_to_cloud_storage_from_cache(generated_pdf_filename, "generated-pdfs"):
            return Response({
                'success': False,
                'error': {
                    "errorCode": 0,
                    "message": "PDF generated successfully, but failed to upload it to cloud storage."
                    }            
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'success': True,
            'result': {
                'mediaUrl': f"generated-pdfs/{generated_pdf_filename}",
            },
        }, status=status.HTTP_201_CREATED)


class TransliterateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        body_serializer = TransliterateInputSerializer(data=request.data)
        if not body_serializer.is_valid():
            return generate_validation_errors_response('body', body_serializer.errors)
        
        source_texts = request.data.get('sourceTexts', None)
        source_language = request.data.get('sourceLanguage', None)
        target_language = request.data.get('targetLanguage', None)

        source_transliteration_script = language_to_indic_transliteration_script.get(source_language, None)
        target_transliteration_script = language_to_indic_transliteration_script.get(target_language, None)

        if source_transliteration_script is None:
            return generate_validation_errors_response('body', 'Unsupported sourceLanguage')
        
        if target_transliteration_script is None:
            return generate_validation_errors_response('body', 'Unsupported targetLanguage')
        
        result_texts = []

        for text_to_transliterate in source_texts:
            transliterated_text = sanscript.transliterate(
                text_to_transliterate, source_transliteration_script, target_transliteration_script
            )
            result_texts.append(transliterated_text)
           
        return Response({
            'success': True,
            'result': {
                'texts': result_texts,
            },
        }, status=status.HTTP_200_OK)


