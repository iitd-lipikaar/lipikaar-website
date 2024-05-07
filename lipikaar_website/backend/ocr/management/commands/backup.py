# import json
# from django.core.management.base import BaseCommand, CommandError

# from ocr.models import Upload, Detection
# from ocr.utils import generate_processing_status_string
# from ocr.cache import clear_cache
# from ocr.cloud_storage import delete_unreferenced_files_from_cloud_storage
# from ocr.utils import try_parse_json_str
# from ocr.redis import delete_cancelled_queued_uploads


# def startup_code():
#         """
#         Executed only once when the server starts. Does the following:
#         1) Clean the cache.
#         2) Marked all previous uploads whose processingStatus is not 5 or 6 as status 6.
#         """

#         print("Deleting cancelled_queued_uploads set from Redis... ", end="")
#         delete_cancelled_queued_uploads()
#         print("Done.")

#         print("Clearing the cache... ", end="")
#         clear_cache()
#         print("Done.")
        
#         print("Marking previously unprocessed uploads as errored... ", end="")
#         unprocessed_upload_count = 0
#         all_uploads = Upload.objects.all()
#         for upload_object in all_uploads:
#             upload_processing_status = try_parse_json_str(upload_object.processing_status)
#             if not 'statusCode' in upload_processing_status or not upload_processing_status['statusCode'] in [5, 6, 7]:
#                 unprocessed_upload_count += 1
#                 upload_object.processing_status = generate_processing_status_string(6, "", "", "")
#                 upload_object.save()
#         print(f"Found {unprocessed_upload_count} such uploads... ", end="")
#         print("Done.")

#         print("Removing media files not referenced in the db... ", end="")
#         all_detections = Detection.objects.all()
#         all_referenced_filenames = [detection_object.image_filename for detection_object in all_detections]
#         delete_unreferenced_files_from_cloud_storage("detection_images", all_referenced_filenames)
#         print("Done.")


# class Command(BaseCommand):
#     help = 'Cleans the cache and marks previously unprocessed uploads as errored.'

#     def handle(self, *args, **kwargs):
#         try:
#             startup_code()
#         except Exception as e:
#             print(e)
#             raise CommandError('Initalization failed.')
