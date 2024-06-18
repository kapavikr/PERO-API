import os
import sys
import requests
from collections import defaultdict

def get_request_status(server_url, api_key, request_id):
    url = f"{server_url}/request_status/{request_id}"
    r = requests.get(url, headers={"api-key": api_key})

    if r.status_code == 401:
        print(f'ERROR: Request with id {request_id} does not belong to this API key.')
    if r.status_code == 404:
        print(f'ERROR: Request with id {request_id} does not exist.')
    if r.status_code != 200:
        print(f'ERROR: Request returned with unexpected status code: {r.status_code}')
        print(r.text)

    response = r.json()

    if response['status'] != "success":
        print(f'ERROR: Unexpected request query status: {response["status"]}')
        print(response)

    return response['request_status']


def download_results(page_name, session, server_url, api_key, request_id, output_path, alto, page, txt):
    path = os.path.join(output_path, page_name)
    requested_formats = []
    if alto:
        requested_formats.append('alto')
    if page:
        requested_formats.append('page')
    if txt:
        requested_formats.append('txt')

    for file_format in requested_formats:
        file_path = f'{path}.{file_format}'
        if os.path.exists(file_path):
            continue

        url = f"{server_url}/download_results/{request_id}/{page_name}/{file_format}"
        r = session.get(url, headers={"api-key": api_key})
        if r.status_code == 400:
            print(f'ERROR: Unknown export format: {file_format}')
            continue
        if r.status_code == 401:
            print(f'ERROR: Request with id {request_id} does not belong to this API key.')
            continue
        if r.status_code == 404:
            print(f'ERROR: Request with id {request_id} does not exist.')
            continue
        if r.status_code != 200:
            print(f'ERROR: Request returned with unexpected status code: {r.status_code}')
            print(r.text)
            continue

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(r.text)


def Retrieve(apiUrl, apiKey, requestId, outputPath):
    page_status = get_request_status(apiUrl, apiKey, requestId)
    os.makedirs(outputPath, exist_ok=True)
    session = requests.Session()
    state_counts = defaultdict(int)
    for page_name in sorted(page_status):
        if page_status[page_name]['state'] == 'PROCESSED':
            print(page_name, page_status[page_name]['state'], page_status[page_name]['quality'])
            download_results(page_name, session, apiUrl, apiKey, requestId, outputPath, True, False, True)
        else:
            print(page_name, page_status[page_name]['state'])

        state_counts[page_status[page_name]['state']] += 1

    print('SUMMARY:')
    for state in state_counts:
        print(state, state_counts[state])

    if state_counts['WAITING'] + state_counts['PROCESSING'] == 0:
        print('ALL PAGES DONE')
        return 0
    else:
        return 1
