from json import load as json_load
from os import listdir, makedirs
from os.path import dirname, exists, isfile, join
from PIL import Image

from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


fonts_dir = join(dirname(__file__), "fonts")


language_to_font_file_map = {
    "hindi" : "NotoSans-VariableFont_wdth,wght.ttf",
    "assamese": "NotoSansBengali-VariableFont_wdth,wght.ttf",
    "kannada": "NotoSansKannada-VariableFont_wdth,wght.ttf",
    "urdu": "Alvi Nastaleeq Regular.ttf",
    "punjabi":"NotoSansGurmukhi-VariableFont_wdth,wght.ttf",
    "bengali":"NotoSansBengali-VariableFont_wdth,wght.ttf",
    "english":"NotoSans-VariableFont_wdth,wght.ttf",
    "oriya":"NotoSansOriya-VariableFont_wdth,wght.ttf",
    "malyalam":"NotoSansMalayalam-VariableFont_wdth,wght.ttf",
    "telugu":"NotoSansTelugu-VariableFont_wdth,wght.ttf",
    "gujarati":"NotoSansGujarati-VariableFont_wdth,wght.ttf",
    "tamil":"NotoSansTamil-VariableFont_wdth,wght.ttf",
}

def register_default_fonts():
    for language, font_file_name in language_to_font_file_map.items():
        font_file_path = join(fonts_dir, font_file_name)
        if not (exists(font_file_path) and isfile(font_file_path)):
            continue
        
        pdfmetrics.registerFont(TTFont(f'DefaultFontFamily_{language}', font_file_path))


def generate_reportlab_color_from_rgba_tuple(rgba_tuple):
    return colors.Color(
        rgba_tuple[0] / 255,
        rgba_tuple[1] / 255,
        rgba_tuple[2] / 255,
        alpha=(rgba_tuple[3] / 255)
    )


def calculate_font_size_for_text_and_dimensions(text, width, height, font_name, max_font_size=100):
    "Function to calculate the font size that fits text within the given width and height"

    temp_canvas = canvas.Canvas("temp-font-size-calculator.pdf", pagesize=(width, height))
    current_font_size = max_font_size

    # Decrease the font size iteratively until the text fits
    while current_font_size > 0:
        text_width = temp_canvas.stringWidth(text, font_name, current_font_size)
        if text_width <= width:
            return current_font_size
        current_font_size -= 1

    return 0  # Return 0 if text cannot fit in the bounding box


def generate_pdf_for_images_and_detections(
        all_images_detections,
        output_file_path,
        upload_images_paths,
        title="untitled",
        draw_bbox_borders = False,
        fill_bboxes = True,
        write_text = True,
        write_transparent_text = False,
        bbox_border_color_override=(0, 0, 0, 255),
        text_background_color_override=(255, 255, 255, 255),
        text_color_override=(0, 0, 0, 255),
        transparent_text_color_override=None,
    ):
    # TODO: generate pdf in memory and return it in HTTP response as base64
    if bbox_border_color_override is not None:
        bbox_border_color_override = generate_reportlab_color_from_rgba_tuple(bbox_border_color_override)

    if text_background_color_override is not None:
        text_background_color_override = generate_reportlab_color_from_rgba_tuple(text_background_color_override)

    if text_color_override is not None:
        text_color_override = generate_reportlab_color_from_rgba_tuple(text_color_override)

    transparent_text_color = colors.Color(0, 0, 0, alpha=0) \
        if transparent_text_color_override is None \
        else generate_reportlab_color_from_rgba_tuple(transparent_text_color_override)
    
    should_compute_default_colors = bbox_border_color_override is not None \
        and text_background_color_override is not None \
        and text_color_override is not None

    max_width = 0
    max_height = 0
    for image_path in upload_images_paths:
        image = Image.open(image_path)
        image_width, image_height = image.size
        max_width = max(max_width, image_width)
        max_height = max(max_height, image_height)
    
    main_canvas = canvas.Canvas(output_file_path, pagesize=(max_width, max_height))
    main_canvas.setTitle(title)

    for i, detection_object in enumerate(all_images_detections):
        image = Image.open(image_path)
        image_width, image_height = image.size

        if should_compute_default_colors:
            image_default_colors = 1 + 1

        bbox_border_color = image_default_colors[i]['bbox_border'] if bbox_border_color_override is None else bbox_border_color_override
        text_background_color = image_default_colors[i]['text_background'] if text_background_color_override is None else text_background_color_override
        text_color = image_default_colors[i]['text'] if text_color_override is None else text_color_override
        
        image_x = int((max_width - image_width) / 2)
        image_y = int((max_height - image_height) / 2)

        main_canvas.drawImage(upload_images_paths[i], x=image_x, y=image_y, width=image_width, height=image_height)
        
        for detection in detection_object['detections']:
            bbox = detection['text_bbox']
            text = detection.get('text', '')
            text_language = detection.get('text_language', 'english')
            
            x_min = image_x + bbox['x_min']
            x_max = image_x + bbox['x_max']
            y_min = image_y + image_height - bbox['y_min']
            y_max = image_y + image_height - bbox['y_max']

            if fill_bboxes: # fill bbox with text background color
                main_canvas.setFillColor(text_background_color)
                main_canvas.rect(x_min, y_min, x_max - x_min, y_max - y_min, stroke=0, fill=1)

            if draw_bbox_borders: # draw bbox border
                main_canvas.setFillColor(bbox_border_color)
                main_canvas.rect(x_min, y_min, x_max - x_min, y_max - y_min, stroke=1, fill=0)
            
            if write_text:
                main_canvas.setFillColor(text_color)
            elif write_transparent_text:
                main_canvas.setFillColor(transparent_text_color)
            else:
                continue

            fitting_font_size = calculate_font_size_for_text_and_dimensions(text, bbox['x_max'] - bbox['x_min'], bbox['y_max'] - bbox['y_min'], f'DefaultFontFamily_{text_language}', max_font_size=100)

            text_width = main_canvas.stringWidth(text, f'DefaultFontFamily_{text_language}', fitting_font_size)
            # text_height = abs(y_max - y_min) # Assuming this is the case
            
            # Center the text inside the bbox
            x_margin = abs(x_max - x_min) - text_width
            # y_margin = abs(y_max - y_min) - text_height
            x_text = x_min + int(x_margin / 2)
            y_text = y_max + int(abs(y_max - y_min) / 4)

            main_canvas.setFont(f'DefaultFontFamily_{text_language}', fitting_font_size)
            main_canvas.drawString(x_text, y_text, text)
        
        main_canvas.showPage()

    main_canvas.save()
    print(f"PDF file '{output_file_path}' created successfully.")


register_default_fonts()
