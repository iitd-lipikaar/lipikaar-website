from base64 import b64encode
from copy import deepcopy
from io import BytesIO
from os.path import dirname, join
from PIL import Image

from cv2 import (
    copyMakeBorder,
    cvtColor,
    getRotationMatrix2D,
    rectangle,
    transform,
    warpAffine,
    BORDER_CONSTANT,
    COLOR_BGR2RGB,
    COLOR_RGB2BGR,
)
from numpy import (
    array,
    ceil,
    sqrt,
    float32,
)


#region Debug Utils
def draw_bbox_on_image(image, bbox, color=(0, 255, 0), thickness=2):
    image_with_rectangle = image.copy()
    
    x_min, y_min, x_max, y_max = bbox['x_min'], bbox['y_min'], bbox['x_max'], bbox['y_max']
    rectangle(image_with_rectangle, (x_min, y_min), (x_max, y_max), color, thickness)
    
    return image_with_rectangle

#endregion


#region Image Cropping
def get_required_padding_for_image_rotation(image):
    height, width, _ = image.shape
    diagonal_size = int(ceil(sqrt(height ** 2 + width ** 2)))
    padding_horizontal = int(ceil((diagonal_size - width) / 2))
    padding_vertical = int(ceil((diagonal_size - height) / 2))

    return [padding_vertical, padding_vertical, padding_horizontal, padding_horizontal]


def get_rotation_matrix_for_image(image, angle):
    center = (image.shape[1] // 2, image.shape[0] // 2)
    rotation_matrix = getRotationMatrix2D(center, angle, 1.0)
    return rotation_matrix


def get_bbox_after_rotation_transform(bbox, rotation_matrix, use_bbox_center_for_pivot=False):
    bbox_height = bbox['y_max'] - bbox['y_min']
    bbox_width = bbox['x_max'] - bbox['x_min']

    if use_bbox_center_for_pivot:
        bbox_center = [
            (bbox['x_min'] + bbox['x_max']) / 2,
            (bbox['y_min'] + bbox['y_max']) / 2,
        ]
        bbox_center = array([bbox_center], dtype=float32)
        transformed_bbox_center = transform(bbox_center.reshape(1, -1, 2), rotation_matrix)[0][0]

        return {
            'x_min': int(transformed_bbox_center[0] - bbox_width / 2),
            'y_min': int(transformed_bbox_center[1] - bbox_height / 2),
            'x_max': int(ceil(transformed_bbox_center[0] + bbox_width / 2)),
            'y_max': int(ceil(transformed_bbox_center[1] + bbox_height / 2)),
        }

    bbox_min_point = [
        bbox['x_min'],
        bbox['y_min'],
    ]
    bbox_min_point = array([bbox_min_point], dtype=float32)
    transformed_bbox_min_point = transform(bbox_min_point.reshape(1, -1, 2), rotation_matrix)[0][0]

    return {
        'x_min': int(transformed_bbox_min_point[0]),
        'y_min': int(transformed_bbox_min_point[1]),
        'x_max': int(transformed_bbox_min_point[0] + bbox_width),
        'y_max': int(transformed_bbox_min_point[1] + bbox_height),
    }


def crop_bboxes_from_image(image, bboxes):
    bboxes = deepcopy(bboxes)
    # imwrite(join(fp, "original-image.png"), image)

    paddings = get_required_padding_for_image_rotation(image)
    padded_image = copyMakeBorder(image, paddings[0], paddings[1], paddings[2], paddings[3], BORDER_CONSTANT)

    # imwrite(join(fp, "padded-image.png"), padded_image)

    for bbox in bboxes:
        bbox['x_min'] += paddings[2]
        bbox['x_max'] += paddings[2]
        bbox['y_min'] += paddings[0]
        bbox['y_max'] += paddings[0]
    
    cropped_images = []

    # TODO: if any bboxes have the same rotation, group them together
    for bbox in bboxes:
        # imwrite(join(fp, "original-image-with-bbox.png"), draw_bbox_on_image(image, bbox))
        # imwrite(join(fp, "padded-image-with-bbox.png"), draw_bbox_on_image(padded_image, bbox))

        rotation_matrix = get_rotation_matrix_for_image(padded_image, bbox['rotation'])
        rotated_image = warpAffine(padded_image, rotation_matrix, (padded_image.shape[1], padded_image.shape[0]))

        bbox = get_bbox_after_rotation_transform(bbox, rotation_matrix)

        # imwrite(join(fp, "rotated-image.png"), rotated_image)
        # imwrite(join(fp, "rotated-image-with-bbox.png"), draw_bbox_on_image(rotated_image, bbox))

        cropped_bbox_image = rotated_image[bbox['y_min']:bbox['y_max'], bbox['x_min']:bbox['x_max']]
        cropped_images.append(cropped_bbox_image)
    
    return cropped_images
#endregion


def clamp(value, lower_limit, upper_limit):
    return max(lower_limit, min(upper_limit, value))


def remove_bboxes_with_low_width_or_height(bboxes, min_width, min_height):
    bboxes = [
        bbox for bbox in bboxes 
        if (bbox['x_max'] - bbox['x_min'] >= min_width) and (bbox['y_max'] - bbox['y_min'] >= min_height)
    ]
    return bboxes


def pil_image_to_base64_str(pil_image):
    buffer = BytesIO()
    pil_image.save(buffer, format="PNG") #("JPEG" if pil_image.mode == "RGB" else "PNG"))
    base64_image = b64encode(buffer.getvalue()).decode("utf-8")
    return base64_image


def save_pil_image(pil_image, output_path=None):
    if output_path == None:
        output_path = join(dirname(__file__), f"debug.{('jpeg') if pil_image.mode == 'RGB' else 'png'}")

    pil_image.save(output_path)


def get_cropped_images_for_bboxes(pil_image, bboxes):
    cv2_image = cvtColor(array(pil_image), COLOR_RGB2BGR)
    
    cropped_images = crop_bboxes_from_image(cv2_image, bboxes)
    
    cropped_images = [Image.fromarray(cvtColor(image, COLOR_BGR2RGB)) for image in cropped_images]
    return cropped_images


def get_detections_from_bboxes_and_recognized_texts(bboxes, recognized_texts):
    if len(bboxes) != len(recognized_texts):
        print("Error at ocr.language_ocr_models.utils.get_detections_from_bboxes_and_recognized_texts")
        print(4 * " " + "bboxes and recognized_texts lists have different lengths")
        print(4 * " " + f"len(bboxes): {len(bboxes)}")
        print(4 * " " + f"len(recognized_texts): {len(recognized_texts)}")
        
        return []

    detections = []
    for i, bbox in enumerate(bboxes):
        detections.append({
            'text_id': str(i),
            'text_bbox': {
                'x_min': bbox['x_min'],
                'x_max': bbox['x_max'],
                'y_min': bbox['y_min'],
                'y_max': bbox['y_max'],
                'line_index': bbox['line_index'],
                'word_index': bbox['word_index'],
            },
            'text_language': bbox['text_language'],
            'text': recognized_texts[i],
        })
    
    return detections


def underscore_to_camelcase(s):
    words = s.split('_')
    return words[0] + ''.join(word.capitalize() for word in words[1:])


def flatten_dict(d):
    flat_dict = {}

    def _flatten_dict(curr_dict):
        for k, v in curr_dict.items():
            if isinstance(v, dict):
                _flatten_dict(v)
            else:
                flat_dict[k] = v

    _flatten_dict(d)

    updated_dict = {}
    for k, v in flat_dict.items():
        updated_dict[underscore_to_camelcase(k)] = v

    return updated_dict


def log_FastAPI_response_error(response):
    try:
        response_data = response.text
        print(response_data)
    except:
        pass
