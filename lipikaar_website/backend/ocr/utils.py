import os
import json
from uuid import uuid4
from datetime import datetime
from pdf2image import convert_from_path

from time import time

# from ocr_app.settings import CACHE_ROOT
# from ocr.models import Upload, Detection
# from ocr.cache import (
#     create_folder_in_cache,
#     download_from_cloud_storage_to_cache,
# )

def generate_unique_filename(file_extension = None):
    if not file_extension:
        return f"{uuid4()}_{round(time() * 1000)}"
    
    return f"{uuid4()}_{round(time() * 1000)}{file_extension}"

def get_extension(file_path):
    file_name, file_extension = os.path.splitext(os.path.basename(file_path))
    return file_extension

def get_filename(file_path):
    file_name, file_extension = os.path.splitext(os.path.basename(file_path))
    return file_name

def find_dict_in_list_by_key_and_value(dict_list, target_key, target_value):
    for d in dict_list:
        if d.get(target_key, None) == target_value:
            return d
    
    return None

def get_path_safe_string(str):
    return "".join([c for c in str if c.isalpha() or c.isdigit() or c==' ']).rstrip()

def split_pdf_to_images(pdf_path, output_dir):
    filename, file_extension = os.path.splitext(os.path.basename(pdf_path))

    # Convert the PDF to a list of PIL Image objects
    images = convert_from_path(pdf_path)
    
    image_filenames = []
    # Iterate over each image and save it to disk
    for page_num, image in enumerate(images):
        # Create a new file name for the image
        img_file_name = os.path.join(output_dir, f'{filename}_{page_num+1}.jpg')
        
        # Save the image file to disk
        image.save(img_file_name, 'JPEG')

        image_filenames.append(img_file_name)
    
    # Delete the original PDF file
    os.remove(pdf_path)

    return image_filenames

def generate_processing_status_string(status_code, status_string, pages_progress, bboxes_progress):
    status_json = {
        'statusCode': status_code,
        'statusString': status_string,
        'pagesProgress': pages_progress,
        'bboxesProgress': bboxes_progress,
    }
    return json.dumps(status_json)

def try_parse_json_str(json_str, json_type="dict"):
    try:
        return json.loads(json_str)
    except ValueError as e:
        print(e)

        if json_type == "list":
            return []

        return {}

def get_path_safe_current_datetime():
    current_time_str = str(datetime.now())
    current_time_str = current_time_str.replace(" ", "-")
    current_time_str = current_time_str.replace(":", "-")
    current_time_str = current_time_str.replace(".", "-")
    return current_time_str

def normalize_detections_text(detections):
    normalized_text_detections = []
    for detection in detections:
        print(detection['text'])
        print(json.dumps(detection['text']))
        normalized_text_detections.append({
            'text_id': detection['text_id'],
            'text_bbox': detection['text_bbox'],
            'text': json.dumps(detection['text'], ensure_ascii=False),
        })
    
    # print(detections)
    # print(normalized_text_detections)

    return normalized_text_detections

def generate_queued_processing_status_string(num_pages):
    str_1 = "Pages" if num_pages > 1 else "Page"
    return generate_processing_status_string(
        0,
        f"{num_pages} {str_1} parsed. Queued for processing...",
        "",
        ""
    )

def generate_processed_page_processing_status_string(current_image_num, num_total_images):
    num_pages_remaining = num_total_images - current_image_num
    str_1 = "Pages" if current_image_num > 1 else "Page"
    str_2 = "Pages" if num_pages_remaining > 1 else "Page"
    return generate_processing_status_string(
        1,
        f"{current_image_num} {str_1} processed. {num_pages_remaining} {str_2} queued.",
        f"{current_image_num + 1}/{num_total_images}",
        ""
    )

def generate_processing_page_processing_status_string(current_image_num, num_total_images):
    return generate_processing_status_string(
        2,
        "",
        f"{current_image_num}/{num_total_images}",
        ""
    )

def generate_processing_bbox_processing_status_string(
    current_image_num,
    num_total_images,
    current_bbox_num,
    num_total_bboxes
    ):
    return generate_processing_status_string(
        3,
        "",
        f"{current_image_num}/{num_total_images}",
        f"{current_bbox_num}/{num_total_bboxes}"
    )

def generate_completed_processing_status_string():
    return generate_processing_status_string(5, "", "", "")

def generate_errored_processing_status_string():
    return generate_processing_status_string(6, "", "", "")

def generate_cancelled_processing_status_string():
    return generate_processing_status_string(7, "cancelled", "", "")

def generate_new_upload_file_name(num_pages):
    file_extension = ".jpg" if num_pages == 1 else ".pdf"
    return f"{str(uuid4())}{file_extension}"

upload_processing_status_generators = {
    'queued': generate_queued_processing_status_string,
    'cancelled': generate_cancelled_processing_status_string,
    'completed': generate_completed_processing_status_string,
    'processed_page': generate_processed_page_processing_status_string,
    'errored': generate_errored_processing_status_string,
    'processing_page': generate_processing_page_processing_status_string,
    'processing_bbox': generate_processing_bbox_processing_status_string,
}

# def generate_reportlab_color_from_rgba_tuple(rgba_tuple):
#     return colors.Color(
#         rgba_tuple[0] / 255,
#         rgba_tuple[1] / 255,
#         rgba_tuple[2] / 255,
#         alpha=(rgba_tuple[3] / 255)
#     )

# def calculate_font_size_for_text_and_dimensions(text, width, height, font_name, max_font_size=100):
#     "Function to calculate the font size that fits text within the given width and height"

#     temp_canvas = canvas.Canvas("temp-font-size-calculator.pdf", pagesize=(width, height))
#     current_font_size = max_font_size

#     # Decrease the font size iteratively until the text fits
#     while current_font_size > 0:
#         text_width = temp_canvas.stringWidth(text, font_name, current_font_size)
#         if text_width <= width:
#             return current_font_size
#         current_font_size -= 1

#     return 0  # Return 0 if text cannot fit in the bounding box

# def generate_pdf_for_images_and_detections(
#         all_images_detections,
#         output_file_path,
#         images_dir=CACHE_ROOT,
#         title="untitled",
#         draw_bbox_borders = False,
#         fill_bboxes = True,
#         write_text = True,
#         write_transparent_text = False,
#         bbox_border_color_override=None,
#         text_background_color_override=None,
#         text_color_override=None,
#         transparent_text_color_override=None,
#     ):
#     # TODO: generate pdf in memory and return it in HTTP response as base64
#     if bbox_border_color_override is not None:
#         bbox_border_color_override = generate_reportlab_color_from_rgba_tuple(bbox_border_color_override)

#     if text_background_color_override is not None:
#         text_background_color_override = generate_reportlab_color_from_rgba_tuple(text_background_color_override)

#     if text_color_override is not None:
#         text_color_override = generate_reportlab_color_from_rgba_tuple(text_color_override)

#     transparent_text_color = colors.Color(0, 0, 0, alpha=0) \
#         if transparent_text_color_override is None \
#         else generate_reportlab_color_from_rgba_tuple(transparent_text_color_override)
    
#     should_compute_default_colors = bbox_border_color_override is not None \
#         and text_background_color_override is not None \
#         and text_color_override is not None

#     upload_images = []
#     max_width = 0
#     max_height = 0
#     for detection_object in all_images_detections:
#         image = Image.open(os.path.join(images_dir, detection_object['image_filename']))
        
#         image_width, image_height = image.size
#         max_width = max(max_width, image_width)
#         max_height = max(max_height, image_height)

#         upload_images.append(image)
    
#     main_canvas = canvas.Canvas(output_file_path, pagesize=(max_width, max_height))
#     main_canvas.setTitle(title)

#     for i, detection_object in enumerate(all_images_detections):
#         image = upload_images[i]
#         image_width, image_height = image.size

#         if should_compute_default_colors:
#             image_default_colors = 1 + 1

#         bbox_border_color = image_default_colors[i]['bbox_border'] if bbox_border_color_override is None else bbox_border_color_override
#         text_background_color = image_default_colors[i]['text_background'] if text_background_color_override is None else text_background_color_override
#         text_color = image_default_colors[i]['text'] if text_color_override is None else text_color_override

#         image_x = int((max_width - image_width) / 2)
#         image_y = int((max_height - image_height) / 2)
#         main_canvas.drawImage(os.path.join(images_dir, detection_object['image_filename']), x=image_x, y=image_y, width=image_width, height=image_height)
        
#         for detection in detection_object['detections']:
#             bbox = detection['text_bbox']
#             text = detection['text'].encode().decode('unicode-escape')

#             x_min = image_x + bbox['x_min']
#             x_max = image_x + bbox['x_max']
#             y_min = image_y + image_height - bbox['y_min']
#             y_max = image_y + image_height - bbox['y_max']

#             if fill_bboxes: # fill bbox with text background color
#                 main_canvas.setFillColor(text_background_color)
#                 main_canvas.rect(x_min, y_min, x_max - x_min, y_max - y_min, stroke=0, fill=1)

#             if draw_bbox_borders: # draw bbox border
#                 main_canvas.setFillColor(bbox_border_color)
#                 main_canvas.rect(x_min, y_min, x_max - x_min, y_max - y_min, stroke=1, fill=0)
            
#             if write_text:
#                 main_canvas.setFillColor(text_color)
#             elif write_transparent_text:
#                 main_canvas.setFillColor(transparent_text_color)
#             else:
#                 continue

#             fitting_font_size = calculate_font_size_for_text_and_dimensions(text, bbox['x_max'] - bbox['x_min'], bbox['y_max'] - bbox['y_min'], "Helvetica", max_font_size=100)

#             text_width = main_canvas.stringWidth(text, "Helvetica", fitting_font_size)
#             # text_height = abs(y_max - y_min) # Assuming this is the case
            
#             # Center the text inside the bbox
#             x_margin = abs(x_max - x_min) - text_width
#             # y_margin = abs(y_max - y_min) - text_height
#             x_text = x_min + int(x_margin / 2)
#             y_text = y_max + int(abs(y_max - y_min) / 4)

#             main_canvas.setFont("Helvetica", fitting_font_size)
#             main_canvas.drawString(x_text, y_text, text)
        
#         main_canvas.showPage()

#     main_canvas.save()
#     print(f"PDF file '{output_file_path}' created successfully.")

# def generate_pdf_for_upload_id_and_pages(
#     upload_id,
#     page_indices,
#     draw_bbox_borders,
#     fill_bboxes,
#     write_text,
#     write_transparent_text
# ):
#     # Get detections
#     upload_object = Upload.objects.get(id=upload_id)
#     detection_ids = try_parse_json_str(upload_object['detection_ids'], "list")

#     upload_images_new_cache_folder = create_folder_in_cache(f"temp-pdf-generation-images")
#     output_pdf_file_name = ""

#     all_images_detections = []
#     for i in page_indices:
#         detection_id = detection_ids[i]
#         detection_object = Detection.objects.get(id=detection_id)
#         page_detections = try_parse_json_str(detection_object['detections'], "list")
#         all_images_detections.append(page_detections)

#         download_from_cloud_storage_to_cache(
#             "detection_images/" + detection_object['image_filename'],
#             upload_images_new_cache_folder + "/" + detection_object['image_filename']
#         )

#     generate_pdf_for_images_and_detections(
#         all_images_detections,
#         "",
#         upload_images_new_cache_folder,
#         upload_object['filename'],
#         draw_bbox_borders,
#         fill_bboxes,
#         write_text,
#         write_transparent_text
#     )

        

        




#     # Create new folder in cache and put images there

#     pass