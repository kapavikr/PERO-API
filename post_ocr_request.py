import os
import requests

def create_request_dict(engine_id, url_file):
    request_dict = {"engine": engine_id, "images": {}}
    with open(url_file, 'r') as f:
        for i, line in enumerate(f):
            words = line.split()
            img_url = words[0]
            if len(words) == 1:
                img_name = f'{i:03d}'
            elif len(words) >= 2:
                img_name = ' '.join(words[1:])
            request_dict['images'][img_name] = img_url

    return request_dict


def create_request_dict_for_file_upload(engine_id, url_file):
    request_dict = {"engine": engine_id, "images": {}}
    with open(url_file, 'r') as f:
        for i, line in enumerate(f):
            words = line.split()
            img_name = words[0]
            if len(words) != 1:
                print('ERROR: Multiple words per file line {i}:', *words)

            request_dict['images'][img_name] = None

    return request_dict


def post_request(server_url, api_key, request_dict):
    r = requests.post(f"{server_url}/post_processing_request",
                      json=request_dict,
                      headers={"api-key": api_key, "Content-Type": "application/json"})

    if r.status_code == 404:
        return 'ERROR: Requested engine was not found on server.'
    if r.status_code == 422:
        return 'ERROR: Request JSON has wrong format.'
    if r.status_code != 200:
        return 'ERROR: Request returned with unexpected status code: {r.status_code}.'

    response = r.json()

    if response['status'] != "success":
        return 'ERROR: Request status is wrong: {response["status"]}.'

    return response['request_id']


def upload_images(server_url, api_key, request_dict, request_id, image_path):
    session = requests.Session()
    headers = {"api-key": api_key}
    for image_name in request_dict['images']:
        file_path = os.path.join(image_path, image_name)
        if not os.path.exists(file_path):
            print(f'ERROR: Missing file {file_path}')
            continue

        url = f'{server_url}/upload_image/{request_id}/{image_name}'
        print(url)
        with open(file_path, 'rb') as f:
            r = session.post(url, files={'file': f}, headers=headers)
        print(r.text)
        if r.status_code == 202:
            print(f'ERROR: Page in wrong state.')
            continue
        if r.status_code == 400:
            print(f'ERROR: Request with id {request_id} does not exist.')
            continue
        if r.status_code == 401:
            print(f'ERROR: Request with id {request_id} does not belong to this API key.')
            continue
        if r.status_code == 404:
            print(f'ERROR: Page with name {image_name} does not exist in request {request_id}.')
            continue
        if r.status_code == 422:
            print(f'ERROR: Unsupported image file extension {image_name}.')
            continue
        if r.status_code != 200:
            print(f'ERROR: Request returned with unexpected status code: {r.status_code}')
            print(r.text)
            continue

def SendToAPI(apiUrl, apiKey, engineId, imagesPath, urlList):
    request_dict = create_request_dict_for_file_upload(engineId, urlList)
    request_id = post_request(apiUrl, apiKey, request_dict)
    upload_images(apiUrl, apiKey, request_dict, request_id, imagesPath)
    return request_id
