import os
import shutil
import json
import requests

from .utils import pil_image_to_base64_str, flatten_dict, log_FastAPI_response_error
from ocr_app.settings import TEXT_RECOGNIZERS_API_PROVIDER_URL


def get_text_recognizers_config(api_provider_url):
    if not api_provider_url:
        return []
    
    get_text_recognizers_config_url = api_provider_url + "/config/"
    response = requests.get(get_text_recognizers_config_url)
    if response.status_code != 200:
        return []

    response_data = response.json()
    tr_config = response_data['result']['processConfigs']
    tr_list = []
    for k, v in tr_config.items():
        tr_list.append(flatten_dict(v)) 

    return tr_list

class LipikarULCA_TextRecognizerClient:
    def __init__(self):
        self.endpoint = TEXT_RECOGNIZERS_API_PROVIDER_URL + "/get-texts-for-images/"
    
    def get_texts_for_images(self, images, model_id):
        request_images = [{'imageContent': pil_image_to_base64_str(image),} for image in images]
        request_config = {
            'modelId': model_id,
            'detectionLevel': "string",
            'modality': "string",
            'languages': [{
                    'sourceLanguageName': "string",
                    'sourceLanguage': "string",
                    'targetLanguage': "string",
                    'targetLanguageName': "string",
            }],
        }

        request_body = {
            'image': request_images,
            'config': request_config,
        }

        # TODO: Add API Key in headers
        response = requests.post(self.endpoint, json=request_body)
        if response.status_code != 200:
            print("Error at ocr.language_ocr_models.text_recognizers.LipikarULCA_TextRecognizerClient")
            print(4 * " " + f"Received status code {response.status_code} for ocr request")
            print(4 * " " + f"Endpoint: {self.endpoint}")
            print(4 * " " + f"Num images: {len(images)}")
            print(4 * " " + f"model_id: {model_id}")

            log_FastAPI_response_error(response)

            return [""] * len(images)

        response_data = response.json()
        recognized_texts = [img_text['source'] for img_text in response_data['output']]
        return recognized_texts

text_recognizers_config = get_text_recognizers_config(TEXT_RECOGNIZERS_API_PROVIDER_URL)
