from PIL import Image

from .document_parsers import document_parsers_config, LipikarDocumentParserClient
from .text_recognizers import text_recognizers_config, LipikarULCA_TextRecognizerClient
from .utils import (
    get_cropped_images_for_bboxes,
    get_detections_from_bboxes_and_recognized_texts,
    remove_bboxes_with_low_width_or_height,
    save_pil_image,
)
from ocr.models import Upload
from ocr.QueueManager import QueueManager
from ocr.utils import upload_processing_status_generators, find_dict_in_list_by_key_and_value


class OCR:
    def __init__(self):
        self.document_parsers_config = document_parsers_config
        self.document_parsers_client = LipikarDocumentParserClient()
        self.text_recognizers_config = text_recognizers_config
        self.text_recognizers_client = LipikarULCA_TextRecognizerClient()

        self.available_document_parsers = [document_parser['modelId'] for document_parser in document_parsers_config]
        self.available_text_recognizers = [text_recognizer['modelId'] for text_recognizer in text_recognizers_config]
    
    def get_config(self):
        return {
            'document_parsers': self.document_parsers_config,
            'text_recognizers': self.text_recognizers_config,
        }

    def validate_config(self, ocr_config):
        invalid_keys = []

        if not ocr_config.get('document_parser', "") in self.available_document_parsers:
            invalid_keys.append("document_parser")
        
        if not ocr_config.get('text_recognizer', "") in self.available_text_recognizers:
            invalid_keys.append("text_recognizer")

        return invalid_keys

    def get_full_ocr_config(self, document_parser_id, text_recognizer_id):
        return {
            'document_parser': find_dict_in_list_by_key_and_value(self.document_parsers_config, 'modelId', document_parser_id),
            'text_recognizer': find_dict_in_list_by_key_and_value(self.text_recognizers_config, 'modelId', text_recognizer_id),
        }

    def perform_ocr_on_full_image(
        self,
        upload_id,
        image_path,
        image_num,
        num_total_images,
        ocr_config
    ):
        if upload_id is not None and image_num is not None and num_total_images is not None:
            updated_processing_status = upload_processing_status_generators['processing_page'](image_num, num_total_images)
            QueueManager.update_upload_processing_status(upload_id, updated_processing_status)

        pil_image = Image.open(image_path)

        bboxes = self.document_parsers_client.get_bboxes_for_image(
            pil_image,
            ocr_config['document_parser']['modelId'],
            ocr_config['text_recognizer']['language'][0],
            True, #TODO: get allowPadding from the parser config
        )
        for bbox in bboxes:
            if not 'rotation' in bbox.keys():
                bbox['rotation'] = 0
        bboxes = remove_bboxes_with_low_width_or_height(bboxes, 1, 1)

        cropped_images = get_cropped_images_for_bboxes(pil_image, bboxes)

        recognized_texts = self.text_recognizers_client.get_texts_for_images(
            cropped_images,
            ocr_config['text_recognizer']['modelId']
        )

        detections = get_detections_from_bboxes_and_recognized_texts(bboxes, recognized_texts)

        return detections

    def perform_ocr_for_single_bbox(
        self,
        image_path,
        bbox,
        text_recognizer,
        copy_image = True
    ):
        pil_image = Image.open(image_path)
        print(bbox)
        cropped_images = get_cropped_images_for_bboxes(pil_image, [bbox])
        save_pil_image(cropped_images[0])
        recognized_texts = self.text_recognizers_client.get_texts_for_images(
            cropped_images,
            text_recognizer['modelId']
        )
        return recognized_texts[0]
