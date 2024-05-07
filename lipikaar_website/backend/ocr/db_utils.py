import os
import json
import uuid
from datetime import (
    datetime,
    time,
    timezone as py_timezone,
)
from django.utils import timezone

from ocr_app.settings import (
    PAGE_LIMIT_PER_USER_PER_DAY,
    CACHE_ROOT,
)
from ocr.models import (
    Upload,
    Detection,
)
from ocr.utils import ( 
    get_filename,
    get_path_safe_string,
    try_parse_json_str,
    get_extension,
    get_path_safe_current_datetime,
)
from ocr.cache import (
    create_folder_in_cache,
    zip_folder_in_cache,
    remove_folder_from_cache,
    download_from_cloud_storage_to_cache,
)
from ocr.cloud_storage import (
    upload_to_cloud_storage_from_cache,
)
from ocr_app.settings import (
    BACKEND_BASE_URL,
)

        
def zip_uploads(upload_ids):
    uploads = Upload.objects.filter(id__in=upload_ids)
    uploads = sorted(uploads, key=lambda upload: upload_ids.index(upload.id))
    uploads_successfully_zipped = []
    folder_name = str(uuid.uuid4()) # Generate a unique name for the folder, that will later be zipped
    folder_path = create_folder_in_cache(folder_name) # Create the folder in the cache

    for upload_object in upload_objects:
        # If the selected upload has not been processed successfully, skip it
        upload_processing_status = try_parse_json_str(upload_object.processing_status)
        if not 'statusCode' in upload_processing_status or upload_processing_status['statusCode'] not in [5, 7]:
            continue
        
        # Set up the directory structure for this upload
        upload_cache_folder_name = f"{upload_object.id} - {get_path_safe_string(get_filename(upload_object.filename))}"
        upload_cache_folder_path = os.path.join(folder_name, upload_cache_folder_name)
        create_folder_in_cache(upload_cache_folder_path)

        upload_cache_images_folder_name = os.path.join(upload_cache_folder_path, "images")
        create_folder_in_cache(upload_cache_images_folder_name)

        upload_cache_upload_details_json_file_path = os.path.join(folder_path, upload_cache_folder_name, "uploadDetails.json")
        upload_cache_detections_json_file_path = os.path.join(folder_path, upload_cache_folder_name, "detections.json")

        # construct the upload details and write them to the json file
        upload_details = {
            'user': upload_object.user.id,
            'created_at': str(upload_object.created_at),
            'filename': upload_object.filename,
            'detection_ids': upload_object.detection_ids,
            'processing_status': upload_processing_status,
            'upload_type': upload_object.upload_type,
        }
        upload_details_json = json.dumps(upload_details, indent=4)
        with open(upload_cache_upload_details_json_file_path, "w+") as outfile:
            outfile.write(upload_details_json)

        # Get all the detections for the upload
        detection_ids = try_parse_json_str(upload_object.detection_ids, "list")
        detections = Detection.objects.filter(id__in=detection_ids)
        detections = sorted(detections, key=lambda detection: detection_ids.index(detection.id))
        
        all_detection_details = [] # To store all the detections for this upload
        for i, detection_object in enumerate(detections):
            try:
                # copy the image into the images folder
                download_from_cloud_storage_to_cache(
                    os.path.join("detection_images", detection_object.image_filename),
                    os.path.join(upload_cache_images_folder_name, f"Page-{i+1}" + get_extension(detection_object.image_filename))
                )
            except:
                print(f"Failed to download image detection_images/{detection_object.image_filename} from cloud storage into cache.")
                continue

            # construct the detection details from the detection object and add them to the list
            all_detection_details.append({
                'user': detection_object.user.id,
                'upload': detection_object.upload.id,
                'image_filename': f"Page-{i+1}" + get_extension(detection_object.image_filename),
                'document_parser': detection_object.document_parser,
                'parsing_postprocessor': detection_object.parsing_postprocessor,
                'text_recognizer': detection_object.text_recognizer,
                'original_detections': try_parse_json_str(detection_object.original_detections, "list"),
                'detections': try_parse_json_str(detection_object.detections, "list"),
            })
        
        # write the detection details into the json file
        all_detection_details_json = json.dumps(all_detection_details, indent=4, ensure_ascii=False)
        with open(upload_cache_detections_json_file_path, "w+") as outfile:
            outfile.write(all_detection_details_json)

        uploads_successfully_zipped.append(upload_object.id)

    zip_file_path = zip_folder_in_cache(folder_name) # Zip this folder inside the cache
    zip_file_name = os.path.basename(zip_file_path)
    upload_to_cloud_storage_from_cache(zip_file_name, "zipped") # Upload the zip file to cloud storage
    # TODO: automatically delete this file from the cloud storage after a while

    remove_folder_from_cache(folder_name) # Delete the folder from the cache

    uploads_failed_to_zip = [id for id in upload_ids if id not in uploads_successfully_zipped]

    return {
        'zipFileName': zip_file_name,
        'uploadsFailedToZip': uploads_failed_to_zip,
    }

def zip_upload(upload_id, dest_folder_name):
    try:
        upload_object = Upload.objects.get(id=upload_id)
    except Exception as e:
        print(e)
        return False

    upload_processing_status = try_parse_json_str(upload_object.processing_status)
    if not upload_processing_status['statusCode'] in [5, 7]: # upload has not been processed completely or there was a processing error
        return False

    upload_cache_folder_name = f"{upload_id}-{get_path_safe_string(get_filename(upload_object.filename))}--{get_path_safe_current_datetime()}"
    upload_cache_folder_path = create_folder_in_cache(upload_cache_folder_name)
    if upload_cache_folder_path == False:
        upload_cache_folder_path = os.path.join(CACHE_ROOT, upload_cache_folder_name)

    upload_cache_images_folder_name = os.path.join(upload_cache_folder_name, "images")
    create_folder_in_cache(upload_cache_images_folder_name)

    upload_cache_upload_details_json_file_path = os.path.join(upload_cache_folder_path, "uploadDetails.json")
    upload_cache_detections_json_file_path = os.path.join(upload_cache_folder_path, "detections.json")

    # construct the upload details from the upload object
    upload_details = {
        'user': upload_object.user.id,
        'created_at': str(upload_object.created_at),
        'filename': upload_object.filename,
        'detection_ids': upload_object.detection_ids,
        'processing_status': upload_processing_status,
        'upload_type': upload_object.upload_type,
    }

    # write the upload details to the json file
    upload_details_json = json.dumps(upload_details, indent=4)
    with open(upload_cache_upload_details_json_file_path, "w+") as outfile:
        outfile.write(upload_details_json)

    detection_ids = try_parse_json_str(upload_object.detection_ids, "list") # Get all the detections for the upload
    all_detection_details = [] # To store all the detections for this upload
    for i, detection_id in enumerate(detection_ids):
        try:
            detection_object = Detection.objects.get(id=detection_id)
        except Exception as e:
            print(e)
            continue
            
        try:
            # copy the image into the images folder
            download_from_cloud_storage_to_cache(
                os.path.join("detection_images", detection_object.image_filename),
                os.path.join(upload_cache_images_folder_name, f"Page-{i+1}" + get_extension(detection_object.image_filename))
            )
        except:
            print(f"Failed to download image detection_images/{detection_object.image_filename} from cloud storage into cache.")
            continue

        # construct the detection details from the detection object and add them to the list
        all_detection_details.append({
            'user': detection_object.user.id,
            'upload': detection_object.upload.id,
            'image_filename': f"Page-{i+1}" + get_extension(detection_object.image_filename),
            'document_parser': detection_object.document_parser,
            'parsing_postprocessor': detection_object.parsing_postprocessor,
            'text_recognizer': detection_object.text_recognizer,
            'original_detections': try_parse_json_str(detection_object.original_detections, "list"),
            'detections': try_parse_json_str(detection_object.detections, "list"),
        })

    # write the detection details into the json file
    all_detection_details_json = json.dumps(all_detection_details, indent=4)
    with open(upload_cache_detections_json_file_path, "w+") as outfile:
        outfile.write(all_detection_details_json)

    zip_file_path = zip_folder_in_cache(upload_cache_folder_name) # Zip this folder inside the cache
    zip_file_name = os.path.basename(zip_file_path)
    upload_to_cloud_storage_from_cache(zip_file_name, dest_folder_name)

    remove_folder_from_cache(upload_cache_folder_name) # Delete the folder from the cache
    
    return True
