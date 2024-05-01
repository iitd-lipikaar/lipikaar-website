from celery import shared_task
from time import sleep
import os
import json

from ocr_app.settings import CACHE_ROOT, MEDIA_ROOT
from .models import Upload, Detection, CustomUser
from ocr.language_ocr_models.main import OCR
ocr_instance = OCR()
from ocr.cloud_storage import upload_to_cloud_storage_from_cache
from ocr.utils import generate_processing_status_string, upload_processing_status_generators
from ocr.cache import delete_multiple_files_from_cache
# from ocr.redis import (
#     redis_set_methods,
#     redis_map_methods,
# )
from ocr.QueueManager import QueueManager


@shared_task(bind=True)
def perform_ocr_for_new_upload(
        self,
        upload_id,
        user_id,
        current_image_num,
        num_total_images,
        image_filenames,
        ocr_config
    ):
    try:
        # Get the user and the upload object
        try:
            user = CustomUser.objects.get(id=user_id)
            upload_object = Upload.objects.get(id=upload_id)
        except:
            return False

        if QueueManager.check_if_upload_is_cancelled(upload_id): # check if the upload was cancelled
            # Update upload_object and save it
            upload_object.processing_status = upload_processing_status_generators['cancelled']()
            upload_object.is_cancelled = True
            upload_object.save()

            delete_multiple_files_from_cache(image_filenames) # delete remaining images of this upload from the cache
            QueueManager.remove_cancelled_upload(upload_id)

            print(f"Upload cancelled, not processing further pages. Upload id: {upload_id}")
            return f"Upload cancelled, not processing further pages. Upload id: {upload_id}"

        # Run OCR for one more page: first page in the image_filenames
        # Save the detection results and add the detection to the detections of the upload
        # Recurse for the remaining images

        detection_ids = json.loads(upload_object.detection_ids)

        image_filename = image_filenames[0]
        image_path = os.path.join(CACHE_ROOT, image_filename)

        detections = ocr_instance.perform_ocr_on_full_image(
            upload_object.id,
            image_path,
            current_image_num,
            num_total_images,
            ocr_config
        )
        new_detection = Detection.objects.create(
            user=user,
            upload=upload_object,
            image_filename=os.path.basename(image_filename),
            document_parser=json.dumps(ocr_config['document_parser']),
            parsing_postprocessor="no_postprocessor",
            text_recognizer=json.dumps(ocr_config['text_recognizer']),
            original_detections=json.dumps(detections),
            detections=json.dumps(detections)
        )
        detection_ids.append(new_detection.id)

        upload_object.detection_ids = json.dumps(detection_ids)
        upload_object.save()
        
        if not upload_to_cloud_storage_from_cache(os.path.basename(image_filename), "detection_images"):
            # Delete remaining images from cache ?
            upload_object.processing_status = upload_processing_status_generators['errored']()
            upload_object.save()

            QueueManager.mark_upload_as_processed(upload_id)

            print(f"Failed to upload image: {image_filename} from Cache to Cloud Storage. Upload id: {upload_id}")
            return f"Failed to upload image: {image_filename} from Cache to Cloud Storage. Upload id: {upload_id}"

        image_filenames.pop(0)
        user.credits = user.credits - 1.0
        user.save()

        if len(image_filenames) == 0:
            upload_object.processing_status = upload_processing_status_generators['completed']()
            upload_object.save()

            QueueManager.mark_upload_as_processed(upload_id)

            print(f"Finished processing from Upload id: {upload_id}. Processed {num_total_images} images.")
            return f"Finished processing from Upload id: {upload_id}. Processed {num_total_images} images."

        progress_processing_status = upload_processing_status_generators['processed_page'](current_image_num, num_total_images)
        QueueManager.update_upload_processing_status(upload_id, progress_processing_status)

        perform_ocr_for_new_upload.delay(
            upload_id,
            user_id,
            current_image_num + 1,
            num_total_images,
            image_filenames,
            ocr_config
        )
    except Exception as e:
        try:
            upload_object = Upload.objects.get(id=upload_id)
        except:
            return False

        upload_object.processing_status = generate_processing_status_string(6, "error", "", "")
        upload_object.is_cancelled = False
        upload_object.save()

        QueueManager.mark_upload_as_processed(upload_id)

        print("Exception in running OCR for new upload")
        print(e)
        return False

@shared_task(bind=True)
def re_run_ocr_for_bbox(
        self,
        image_filename,
        bbox,
        text_recognizer
    ):
    # print(f"Rerunning for {image_filename}")

    try:
        # if using cloud storage, image has to be first downloaded and stored in local cache
        image_path = os.path.join(MEDIA_ROOT, "detection_images", image_filename)
        
        recognized_text = ocr_instance.perform_ocr_for_single_bbox(
            image_path,
            bbox,
            text_recognizer
        )
        return recognized_text
    except Exception as e:
        print("Exception in rerunning OCR")
        print(e)
        return "" # return empty string

@shared_task(bind=True)
def perform_ocr_for_service(
        self,
        image_filenames,
        ocr_config
    ):
    # try:
        image_filename = image_filenames[0]
        image_path = os.path.join(CACHE_ROOT, image_filename)

        detections = ocr_instance.perform_ocr_on_full_image(
            None,
            image_path,
            None,
            None,
            ocr_config
        )

        delete_multiple_files_from_cache([os.path.basename(image_filename)])

        return detections
    # except Exception as e:
    #     print("Exception in performing OCR for service.")
    #     print(e)
    #     return False
