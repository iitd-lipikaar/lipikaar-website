import os
import time
import shutil
from uuid import uuid4

from ocr.dirs import CACHE_FOLDER
from ocr_app.settings import MEDIA_ROOT
from ocr.utils import get_extension

def upload_to_cloud_storage_from_cache(filename, upload_folder):
    try:
        print(filename)
        shutil.move(os.path.join(CACHE_FOLDER, filename), os.path.join(MEDIA_ROOT, upload_folder, filename))
        print("Uploaded to cloud storage")
    except Exception as e:
        print(e)
        return False
    
    return True

def delete_from_cloud_storage(filepath):
    try:
        os.remove(os.path.join(MEDIA_ROOT, filepath))
    except Exception as e:
        print(e)
        return False
    
    return True

# def delete_multiple_from_cloud_storage(filepaths):


def duplicate_inside_cloud_storage(filename, upload_folder):
    try:
        src_path = os.path.join(MEDIA_ROOT, upload_folder, filename)

        extension = get_extension(filename)
        new_filename = f"{uuid4()}_{round(time.time() * 1000)}{extension}" # generate unique file name
        dest_path = os.path.join(MEDIA_ROOT, upload_folder, new_filename)

        shutil.copyfile(src_path, dest_path)

        return new_filename
    except Exception as e:
        print(e)
        return False

    return True


def delete_unreferenced_files_from_cloud_storage(folder, referenced_filenames):
    all_files_in_folder = os.listdir(os.path.join(MEDIA_ROOT, folder))
    all_unreferenced_files = list(set(all_files_in_folder) - set(referenced_filenames))

    print(f"Found {len(all_unreferenced_files)} unreferenced files in cloud storage... ", end="")

    for unreferenced_filename in all_unreferenced_files:
        delete_from_cloud_storage(os.path.join(folder, unreferenced_filename))

