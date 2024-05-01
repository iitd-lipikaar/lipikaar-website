import os
import time
from uuid import uuid4
import shutil

from ocr.utils import split_pdf_to_images, get_extension
from ocr_app.settings import BASE_DIR, CACHE_ROOT, MEDIA_ROOT


def save_image_or_pdf_to_cache(image_or_pdf_file, extension):
    """
    save the file in cache
    image is saved in cache and it's new name is returned
    pdf is split into images and names of those images are returned
    """
    filename = f"{uuid4()}_{round(time.time() * 1000)}{extension}" # generate unique file name
    filepath = os.path.join(CACHE_ROOT, filename) # save to the cache folder
    with open(filepath, 'wb+') as destination: # write the file
        for chunk in image_or_pdf_file.chunks():
            destination.write(chunk)

    if extension != ".pdf": # if the file is an image, return the file name
        return [filename]

    # have to split the pdf into pages
    # split the pdf into images, one image per page, and get the file names of the images
    return split_pdf_to_images(os.path.join(CACHE_ROOT, filename), CACHE_ROOT)

def delete_multiple_files_from_cache(filenames):
    all_deletes_successful = True

    for filename in filenames:
        file_path = os.path.join(CACHE_ROOT, filename)

        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
            else:
                all_deletes_successful = False
        except Exception as e:
            print(e)
            all_deletes_successful = False

    return all_deletes_successful

def clear_cache():
    "Delete all the files in the cache folder."
    filenames = os.listdir(CACHE_ROOT)
    print(f"Found {len(filenames)} files in cache... ", end="")
    delete_multiple_files_from_cache(filenames)

def create_folder_in_cache(folder_name):
    folder_path = os.path.join(CACHE_ROOT, folder_name)

    if os.path.exists(folder_path):
        return False
    
    os.makedirs(folder_path)
    return folder_path

def remove_folder_from_cache(folder_name):
    folder_path = os.path.join(CACHE_ROOT, folder_name)
    shutil.rmtree(folder_path)

def download_from_cloud_storage_to_cache(source_file_path, dest_file_path):
    abs_source_file_path = os.path.join(MEDIA_ROOT, source_file_path)
    abs_dest_file_path = os.path.join(CACHE_ROOT, dest_file_path)

    shutil.copyfile(abs_source_file_path, abs_dest_file_path)
    return dest_file_path

def zip_folder_in_cache(folder_name):
    folder_path = os.path.join(CACHE_ROOT, folder_name)
    output_file_path = os.path.join(CACHE_ROOT, folder_name)

    shutil.make_archive(output_file_path, 'zip', folder_path)
    return output_file_path + ".zip"

def load_frontend_build_file_into_cache(filename):
    filename = os.path.basename(filename)
    file_extension = get_extension(filename)
    new_file_name = str(uuid4()) + file_extension

    try:
        shutil.copyfile(os.path.join(BASE_DIR, "build", filename), os.path.join(CACHE_ROOT, new_file_name))
        return new_file_name
    except:
        return None
