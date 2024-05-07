import requests

from .utils import pil_image_to_base64_str, flatten_dict, log_FastAPI_response_error
from ocr_app.settings import DOCUMENT_PARSERS_API_PROVIDER_URL


def get_document_parsers_config(api_provider_url): # TODO: fix this (and more importantly, standardize it)
    if not api_provider_url:
        return []
    
    get_text_recognizers_config_url = api_provider_url + "/config/"
    response = requests.get(get_text_recognizers_config_url)
    if response.status_code != 200:
        return []

    response_data = response.json()
    dp_config = response_data['result']['documentParsersConfig']
    dp2 = []
    for dp in dp_config:
        dp2.append(flatten_dict(dp))
    return dp2


class LipikarDocumentParserClient:
    def __init__(self):
        self.endpoint = DOCUMENT_PARSERS_API_PROVIDER_URL + "/get-bboxes-for-image/"
    
    def get_bboxes_for_image(self, image, model_id, language, allow_padding):
        request_body = {
            'imageContent': pil_image_to_base64_str(image),
            'parser': model_id,
            'language': language,
            'allowPadding': allow_padding,
        }
        
        # TODO: Add API Key in headers
        response = requests.post(self.endpoint, json=request_body)
        if response.status_code != 200:
            print("Error at ocr.language_ocr_models.text_recognizers.LipikarULCA_TextRecognizerClient")
            print(4 * " " + f"Received status code {response.status_code} for ocr request")
            print(4 * " " + f"Endpoint: {self.endpoint}")
            # print(4 * " " + f"Num images: {len(images)}")
            print(4 * " " + f"model_id: {model_id}")

            log_FastAPI_response_error(response)

            return [""] * len(images)
        
        response_data = response.json()

        # TODO: remove the following once Document Parser API returns text_language with bbox
        bboxes = response_data['result']['bboxes']
        for i in range(len(bboxes)):
            bboxes[i]['text_language'] = language
        
        return bboxes

document_parsers_config = get_document_parsers_config(DOCUMENT_PARSERS_API_PROVIDER_URL)
