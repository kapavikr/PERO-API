import subprocess
import sys
import importlib.metadata
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from tkinter import font
import os
import zipfile
import json
import requests
from datetime import datetime
import csv
from collections import defaultdict
import subprocess
import platform
from tkinter import messagebox
import shutil
import hashlib
import xml.etree.ElementTree as ET
import cv2
import platform

SETTINGS_FILE = "settings.json"
JPG_FOLDER = "jpg"
ALTO_FOLDER = "alto"
MASTERCOPY_FOLDER = "mastercopy"
TXT_FOLDER = "txt"
MD5_PREFIX = "md5"
INFO_PREFIX = "info"
RESULT_FOLDER = "result"
DATA_FILE = "data.csv"
QUALITY_FILE = "quality.csv"
QUALITYCOMPARISON_FILE = "qualityComparison.csv" 
WINDOW_WIDTH = 1000

###############################################################################
# Upravené kopie funkcí z post_ocr_request.py
###############################################################################
def LoadEnginesFromAPI(server_url, api_key):
    r = requests.get(f"{server_url}/get_engines", headers={"api-key": api_key})
    print(r.status_code)
    if r.status_code != 200:
        ShowError(f'ERROR: Failed to get available OCR engine list. Code: {r.status_code}')
        print(f'ERROR: Failed to get available OCR engine list. Code: {r.status_code}')
        return None

    try:
        result = r.json()
        if result['status'] not in ["success", "succes"]:
            ShowError(f'ERROR: Failed to get available OCR engine list. Status: {result["status"]}')
            print(f'ERROR: Failed to get available OCR engine list. Status: {result["status"]}')
            return None
    except:
        print(f'ERROR: Communication with API failed.')
        return None

    return result['engines']

def CreateRequest(engine_id, url_file):
    request_dict = {"engine": engine_id, "images": {}}
    with open(url_file, 'r') as f:
        for i, line in enumerate(f):
            words = line.split()
            img_name = words[0]
            if len(words) != 1:
                progress.set('ERROR: Multiple words per file line {i}:', *words)
                print('ERROR: Multiple words per file line {i}:', *words)

            request_dict['images'][img_name] = None

    return request_dict

def PostRequest(server_url, api_key, request_dict):
    r = requests.post(f"{server_url}/post_processing_request",
                      json=request_dict,
                      headers={"api-key": api_key, "Content-Type": "application/json"})

    if r.status_code == 404:
        ShowError(f'ERROR: Requested engine was not found on server.')
        print(f'ERROR: Requested engine was not found on server.')
        return None
    elif r.status_code == 422:
        ShowError(f'ERROR: Request JSON has wrong format.')
        print(f'ERROR: Request JSON has wrong format.')
        return None
    elif r.status_code != 200:
        ShowError(f'ERROR: Request returned with unexpected status code: {r.status_code}')
        print(f'ERROR: Request returned with unexpected status code: {r.status_code}')
        return None

    else:
        response = r.json()
        if response['status'] != "success":
            ShowError(f'ERROR: Request status is wrong: {response["status"]}')
            print(f'ERROR: Request status is wrong: {response["status"]}')
            print(response)

        return response['request_id']

def UploadImages(server_url, api_key, request_dict, request_id, image_path):
    session = requests.Session()
    headers = {"api-key": api_key}
    total = len(request_dict['images'])
    uploaded = 0
    
    for idx, image_name in enumerate(request_dict['images']):
        file_path = os.path.join(image_path, image_name)
        if not os.path.exists(file_path):
            ShowError(f'ERROR: Missing file {file_path}')
            print(f'ERROR: Missing file {file_path}')
            continue

        url = f'{server_url}/upload_image/{request_id}/{image_name}'
        UpdateProgress('Uploading image ' + str(idx+1) + '/' + str(total) + "...")

        with open(file_path, 'rb') as f:
            r = session.post(url, files={'file': f}, headers=headers)
        print(r.text)
        if r.status_code == 200:
            uploaded = uploaded + 1
            continue
        if r.status_code == 202:
            ShowError(f'ERROR: Page in wrong state.')
            print(f'ERROR: Page in wrong state.')
            continue
        if r.status_code == 400:
            ShowError(f'ERROR: Request with id {request_id} does not exist.')
            print(f'ERROR: Request with id {request_id} does not exist.')
            continue
        if r.status_code == 401:
            ShowError(f'ERROR: Request with id {request_id} does not belong to this API key.')
            print(f'ERROR: Request with id {request_id} does not belong to this API key.')
            continue
        if r.status_code == 404:
            ShowError(f'ERROR: Page with name {image_name} does not exist in request {request_id}.')
            print(f'ERROR: Page with name {image_name} does not exist in request {request_id}.')
            continue
        if r.status_code == 422:
            ShowError(f'ERROR: Unsupported image file extension {image_name}.')
            print(f'ERROR: Unsupported image file extension {image_name}.')
            continue
        if r.status_code != 200:
            ShowError(f'ERROR: Request returned with unexpected status code: {r.status_code}')
            print(f'ERROR: Request returned with unexpected status code: {r.status_code}')
            print(r.text)
            continue

    return uploaded

###############################################################################
# Upravené kopie funkcí z retrieve_ocr_results.py
###############################################################################
def get_request_status(server_url, api_key, request_id):
    url = f"{server_url}/request_status/{request_id}"
    r = requests.get(url, headers={"api-key": api_key})

    if r.status_code == 401:
        ShowError(f'ERROR: Request with id {request_id} does not belong to this API key.')
        print(f'ERROR: Request with id {request_id} does not belong to this API key.')
    if r.status_code == 404:
        ShowError(f'ERROR: Request with id {request_id} does not exist.')
        print(f'ERROR: Request with id {request_id} does not exist.')
    if r.status_code != 200:
        ShowError(f'ERROR: Request returned with unexpected status code: {r.status_code}')
        print(f'ERROR: Request returned with unexpected status code: {r.status_code}')
        print(r.text)

    response = r.json()

    if response['status'] != "success":
        ShowError(f'ERROR: Unexpected request query status: {response["status"]}')
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
            ShowError(f'ERROR: Unknown export format: {file_format}')
            print(f'ERROR: Unknown export format: {file_format}')
            continue
        if r.status_code == 401:
            ShowError(f'ERROR: Request with id {request_id} does not belong to this API key.')
            print(f'ERROR: Request with id {request_id} does not belong to this API key.')
            continue
        if r.status_code == 404:
            ShowError(f'ERROR: Request with id {request_id} does not exist.')
            print(f'ERROR: Request with id {request_id} does not exist.')
            continue
        if r.status_code != 200:
            ShowError(f'ERROR: Request returned with unexpected status code: {r.status_code}')
            print(f'ERROR: Request returned with unexpected status code: {r.status_code}')
            print(r.text)
            continue

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(r.text)


###############################################################################
# GUI
###############################################################################
root = Tk()
root.geometry(str(WINDOW_WIDTH) + "x600")

root.grid_columnconfigure(0, minsize=400)
root.grid_columnconfigure(1, minsize=400)

root.title("updatePSPviaAPI") 
tabControl = ttk.Notebook(root) 
  
tab1 = ttk.Frame(tabControl) 
tab2 = ttk.Frame(tabControl)
tab3 = ttk.Frame(tabControl)
  
tabControl.add(tab1, text ='Zadání') 
tabControl.add(tab2, text ='Výsledky')
tabControl.add(tab3, text ='Manuální nahrazení') 
tabControl.pack(expand = 1, fill ="both")

###############################################################################
# tab 1 - Zadání
###############################################################################
def ShowError(text):
    UpdateProgress(text, 'red')

def ShowSuccess(text):
    UpdateProgress(text, 'green')
    
def UpdateProgress(text, color = None):
    progress.set(text)
    if color != None:
        progressLabel.config(foreground=color)
    else:
        progressLabel.config(foreground='black')
    root.update()

def CreateTextboxRow(frame, rowIndex, label):
    label = ttk.Label(frame, text = label)
    label.grid(row = rowIndex, column = 0, sticky = W, padx = 10, pady = 10)
    text_box = Text(frame, wrap='word', width=50, height=1)
    text_box.grid(row=rowIndex, column=1, sticky = W, padx = 10, pady = 10)
    return text_box

def CreateButtonRow(frame, rowIndex, text, command, var):
    button = ttk.Button(frame, width=15, text = text, command=command)
    button.grid(row = rowIndex, column = 0, padx = 10, pady = 10)
    if (var != None):
        label = ttk.Label(frame, textvariable = var)
        label.grid(row = rowIndex, column = 1, sticky = W, padx = 10, pady = 10)

def OpenPSPFolder():
    global lastDir
    path = filedialog.askopenfilename(
        title="Select PSP file",
        filetypes=[("Zip Files", "*.zip")])
    pspFolder.set(path)
    lastDir = os.path.dirname(path)
    workingFolder.set(lastDir)

def OpenPSPFolder2():
    global lastDir
    path = filedialog.askdirectory(
        title="Select PSP folder")
    pspFolder.set(path)
    lastDir = os.path.dirname(path)
    workingFolder.set(lastDir)

def OpenWorkingFolder():
    global lastDir
    path = filedialog.askdirectory(initialdir=lastDir, title="Choose PSP")
    workingFolder.set(path)
    lastDir = os.path.dirname(path)

def UnzipFile(zip_path, extract_to):
    top_level_dirs = set()

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

        for member in zip_ref.namelist():
            top_level_dir = os.path.normpath(member).split(os.sep)[0]
            top_level_dirs.add(top_level_dir)

    return list(top_level_dirs)[0]

def CheckPackage(package):
    masterCopy = os.path.join(package, MASTERCOPY_FOLDER)

    global MD5_PREFIX
    checksumFile = FindFile(package, MD5_PREFIX, ".md5")
    if checksumFile is None: 
        MD5_PREFIX = "MD5"
        checksumFile = FindFile(package, MD5_PREFIX, ".md5")

    infoFile = FindFile(package, INFO_PREFIX, ".xml")

    #print(masterCopy)
    #print(checksumFile)
    #print(infoFile)

    return os.path.exists(masterCopy) and checksumFile is not None and infoFile is not None
    

def ConvertToJpg(input_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    files = os.listdir(input_dir)
    total = len(files)
    for idx,filename in enumerate(files):
        if filename.lower().endswith('.jp2'):
            jp2_path = os.path.join(input_dir, filename)
            jpg_filename = os.path.splitext(filename)[0] + '.jpg'
            jpg_path = os.path.join(output_dir, jpg_filename) 
            UpdateProgress('Converting to JPG ' + str(idx+1) + '/' + str(total) + "...")
            
            img = cv2.imread(jp2_path)       
            cv2.imwrite(jpg_path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])  # Save the image as jpg
            
            if (CheckLimit(jpg_path)):
                print(jpg_path)

def CreateFilesList(directory, output_file):
    if os.path.exists(output_file):
        os.remove(output_file)

    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    with open(output_file, 'w') as file:
        for filename in files:
            file.write(filename + '\n')

def CheckLimit(file_path):
    file_size_bytes = os.path.getsize(file_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    return file_size_mb > 8

def SaveSettings(serverUrl, apiKey):
    settings = {
        "ServerURL": serverUrl,
        "APIKey": apiKey
    }
    json_object = json.dumps(settings, indent=4)
    with open(SETTINGS_FILE, "w") as outfile:
        outfile.write(json_object)

def LoadSettings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as openfile:
            settings = json.load(openfile)
        serverUrlTextbox.delete("1.0", END)
        serverUrlTextbox.insert(END, settings['ServerURL'])
        apiKeyTextbox.delete("1.0", END)
        apiKeyTextbox.insert(END, settings['APIKey'])

def LoadEngines(serverUrl, apiKey, loadEnginesButton):
    if (serverUrl != '' and apiKey != ''):
        SaveSettings(serverUrl, apiKey)
        enginesSelection = LoadEnginesFromAPI(serverUrl, apiKey)
        if (enginesSelection != None):
            LoadSettings()
            loadEnginesButton.destroy()
            ShowFullGUI(enginesSelection)
        else:
            ShowError("Nepodařilo se spopjit s API. Zkontrolujte zadané údaje a zkuste to znovu.")

def OpenFolder(folder_path):
    if platform.system() == "Windows":
        os.startfile(folder_path)
    elif platform.system() == "Darwin":  # macOS
        subprocess.run(["open", folder_path])
    else:  # Linux and other Unix-like systems
        subprocess.run(["xdg-open", folder_path])

def SendRequest(serverUrl, apiKey, engineId, url_file, imagesPath):
    request_dict = CreateRequest(engineId, url_file)
    requestId = PostRequest(serverUrl, apiKey, request_dict)
    if requestId != None:
        numberOfImages = UploadImages(serverUrl, apiKey, request_dict, requestId, imagesPath)
        return [requestId, numberOfImages]
    else:
        return None

def SaveRequest(pspFolder, package, workingFolder, requestId, numberOfImages, date):
    fileExists = os.path.isfile(DATA_FILE)
    with open(DATA_FILE, 'a', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        if not fileExists:
            csvwriter.writerow(["PSP", "Package", "Working", "ID", "Date", "Images", "Status", "Result"])
        csvwriter.writerow([pspFolder, package, workingFolder, requestId, date, numberOfImages, 'sent', ''])

def CalculateWC(folder, extension, output):
    numberOfFiles = 0
    with open(output, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(['File Name', 'Average WC'])
        
        for file_name in os.listdir(folder):            # Iterate through all XML files in the folder
            if file_name.endswith(extension):
                file_path = os.path.join(folder, file_name)
                avg_wc = CalculateAverageWC(file_path)

                if avg_wc is not None:
                    csvwriter.writerow([file_name, f"{avg_wc:.6f}"])    # Write the result to the CSV file
                    numberOfFiles = numberOfFiles + 1
                else:
                    csvwriter.writerow([file_name, '0'])        # Handle case where no WC values were found
    return numberOfFiles

def ExtractNamespace(root):
    if '}' in root.tag:
        return root.tag.split('}')[0].strip('{')
    return None

def CalculateAverageWC(file):
    tree = ET.parse(file)
    root = tree.getroot()

    namespace = ExtractNamespace(root)
    if not namespace:
        return None, None  # Handle case where no namespace is found

    # Find all 'String' elements and extract the 'WC' attribute
    wc_values = []
    for string_element in root.findall(f".//{{{namespace}}}String"):
        wc = string_element.get('WC')
        if wc is not None:
            wc_values.append(float(wc))

    # Calculate average WC, return None if there are no WC values
    if wc_values:
        return sum(wc_values) / len(wc_values)
    return None

def Run(serverUrl, apiKey, engine, pspFolder, workingFolder):
    SaveSettings(serverUrl, apiKey)

    if pspFolder == NOT_SELECTED or workingFolder == NOT_SELECTED:
        ShowError('Není vybrán PSP balíček a pracovní složka!')
        return

    if os.path.isfile(pspFolder) and zipfile.is_zipfile(pspFolder):
        UpdateProgress("Unzipping...")
        resultFolder = UnzipFile(pspFolder, workingFolder)
    else:
        resultFolder = pspFolder

    package = os.path.join(workingFolder, resultFolder)
    global ALTO_FOLDER
    altoFolder = os.path.join(package, ALTO_FOLDER)
    #print(altoFolder)
    CalculateWC(altoFolder, ".xml", os.path.join(workingFolder, QUALITY_FILE))

    if CheckPackage(package):
        jpgFolder = os.path.join(workingFolder, JPG_FOLDER)
        ConvertToJpg(os.path.join(package, MASTERCOPY_FOLDER), jpgFolder)
        fileList = os.path.join(jpgFolder, "list.txt")
        CreateFilesList(jpgFolder, fileList)
        UpdateProgress("Sending request to PERO...")
        [requestId, numberOfImages]= SendRequest(serverUrl, apiKey, engine, fileList, jpgFolder)
        if requestId != None:
            SaveRequest(pspFolder, package, workingFolder, requestId, numberOfImages, datetime.now())
            LoadData(tree)
            ShowSuccess('Request sent!')
    else:
        ShowError('Input is not a valid PSP package!')

NOT_SELECTED = "[Folder not selected]"
pspFolder = StringVar()
workingFolder = StringVar()
engine = StringVar()
progress = StringVar()
pspFolder.set(NOT_SELECTED)  
workingFolder.set(NOT_SELECTED)
engine.set(1)
progress.set('')
selectFileType = StringVar()
selectFileType.set("zip")
        
row = 1
serverUrlTextbox = CreateTextboxRow(tab1, row, "Server URL")
row += 1
apiKeyTextbox = CreateTextboxRow(tab1, row, "API key")
row += 1

loadEnginesButton = ttk.Button(tab1, width=15, text = "LoadEngines", command=lambda: LoadEngines(serverUrlTextbox.get("1.0", END).strip(), apiKeyTextbox.get("1.0", END).strip(), loadEnginesButton))
loadEnginesButton.grid(row = row, column = 0, columnspan = 2, padx = 10, pady = 10)
row += 1

progressLabel = ttk.Label(tab1, textvariable = progress)
progressLabel.grid(row = row, column = 0, columnspan = 2, padx = 10, pady = 10)

def ShowFullGUI(enginesSelection):
    global row

    label = ttk.Label(tab1, text = "Engine:")
    label.grid(row = row, column = 0, sticky = W, padx = 10, pady = (10, 0))

    for key, value in enginesSelection.items():
        radio_button = ttk.Radiobutton(tab1, text=key, variable=engine, value=value['id'])
        radio_button.grid(row = row, column = 1, sticky = W, pady = (10, 0))
        row += 1
    
    label = ttk.Label(tab1, text = "Select source PSP and working folder, to which unzipped data will be saved:")
    label.grid(row = row, column = 0, columnspan = 2, sticky= W, padx = 10, pady = (20, 10))
    row += 1

    selectionFrame = ttk.Frame(tab1)
    selectionFrame.grid(row = row, column = 0, padx = 10, pady = 10)

    button = ttk.Button(selectionFrame, width=15, text = "PSP zip", command=OpenPSPFolder)
    button.pack()
    button = ttk.Button(selectionFrame, width=15, text = "PSP folder", command=OpenPSPFolder2)
    button.pack()
    label = ttk.Label(tab1, textvariable = pspFolder)
    label.grid(row = row, column = 1, sticky = W, padx = 10, pady = 10)

    row += 1
    CreateButtonRow(tab1, row, "Working folder", OpenWorkingFolder, workingFolder)
    row += 1

    button = ttk.Button(tab1, width=15, text = "Send to PERO", command=lambda: Run(serverUrlTextbox.get("1.0", END).strip(), apiKeyTextbox.get("1.0", END).strip(), engine.get(), pspFolder.get(), workingFolder.get()))
    button.grid(row = row, column = 0, columnspan = 2, padx = 10, pady = 10)
    row += 1

    UpdateProgress('')
    progressLabel.grid(row = row, column = 0, columnspan = 2, padx = 10, pady = 10)


###############################################################################
# tab 2 - Výsledky
###############################################################################
def ShowError2(text):
    UpdateProgress2(text, 'red')

def ShowSuccess2(text):
    UpdateProgress2(text, 'green')
    
def UpdateProgress2(text, color = None):
    progress2.set(text)
    if color != None:
        progressLabel2.config(foreground=color)
    else:
        progressLabel2.config(foreground='black')
    root.update()

def LoadData(tree):    
    for row in tree.get_children():
        tree.delete(row)

    if not os.path.isfile(DATA_FILE):
        return

    with open(DATA_FILE, newline='') as file:
        reader = csv.reader(file)

        headers = next(reader)

        tree["columns"] = headers
        for header in headers:
            tree.heading(header, text=header)
            tree.column(header, width=(WINDOW_WIDTH-20)//(len(headers)-2), anchor=W, stretch=NO)

        replaced = []
        other = []
        
        for row in reader:
            if row[5] == "replaced":
                replaced.append(row)
            else:
                other.append(row)
        other.sort(key=lambda x: x[4], reverse = True)
        replaced.sort(key=lambda x: x[4], reverse = True)

        rows = other + replaced

        InsertRows(rows)
        
    SetDisplay(tree)

def InsertRows(rows):
    for i, row in enumerate(rows):
        if i % 2 == 0:
            tag = 'evenrow'
        else:
            tag = 'oddrow'
        row_id = tree.insert("", END, values=row, tags=(tag,))

def SetDisplay(tree):
    tree["displaycolumns"] = ["Date", "PSP", "Images", "Status", "Result"]
    tree.column("Date", width=(WINDOW_WIDTH-20) // 12*2)
    tree.column("PSP", width=(WINDOW_WIDTH-20) // 12*6)
    tree.column("Images", width=(WINDOW_WIDTH-20) // 12*1, anchor=E)
    tree.column("Status", width=(WINDOW_WIDTH-20) // 12*1, anchor=E)
    tree.column("Result", width=(WINDOW_WIDTH-20) // 12*2, anchor=E)

def UpdateStatus(requestId, newValue):
    UpdateData(requestId, 6, newValue)

def UpdateResult(requestId, newValue):
    UpdateData(requestId, 7, newValue)

def UpdateData(requestId, newValueIndex, newValue):
    rows = []
    with open(DATA_FILE, 'r', newline='') as file:
        reader = csv.reader(file)
        headers = next(reader)  # Save the headers
        for row in reader:
            if row[3] == requestId:
                row[newValueIndex] = newValue
            rows.append(row)

    with open(DATA_FILE, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)  # Write the headers
        writer.writerows(rows)  # Write the updated rows

def DeleteData(id, workingFolder, pspFolder, package):
    UpdateProgress2("Deleting data")
    DeleteFolder(os.path.join(workingFolder, JPG_FOLDER))
    DeleteFolder(os.path.join(workingFolder, RESULT_FOLDER))
    DeleteFile(os.path.join(workingFolder, QUALITY_FILE))
    DeleteFile(os.path.join(workingFolder, QUALITYCOMPARISON_FILE))
    if os.path.isfile(pspFolder) and zipfile.is_zipfile(pspFolder):
        DeleteFolder(package)
    UpdateProgress2("Deleting record")
    DeleteRequest(id)
    ShowSuccess2("Data deleted")

def DeleteFolder(folder):
    if os.path.exists(folder):
        shutil.rmtree(folder)       # Remove the folder and all its contents
        
def DeleteFile(file):
    if os.path.exists(file):
        if os.path.isfile(file):
            os.remove(file)
    
def DeleteRequest(id):
    with open(DATA_FILE, mode='r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        rows = list(reader)  # Convert the reader object to a list of rows

    updated_rows = [row for row in rows if row[3] != id]

    with open(DATA_FILE, mode='w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(updated_rows)
    LoadData(tree)

def RetrieveResult(serverUrl, apiKey, requestId, workingFolder):
    SaveSettings(serverUrl, apiKey)

    page_status = get_request_status(serverUrl, apiKey, requestId)

    resultFolder = os.path.join(workingFolder, RESULT_FOLDER)
    os.makedirs(resultFolder, exist_ok=True)

    session = requests.Session()

    state_counts = defaultdict(int)
    for page_name in sorted(page_status):
        if page_status[page_name]['state'] == 'PROCESSED':
            UpdateProgress2(page_name + ": " + page_status[page_name]['state'] + ", " + str(page_status[page_name]['quality']))
            download_results(page_name, session, serverUrl, apiKey, requestId, resultFolder, True, False, True)
        else:
            UpdateProgress2(page_name + ": " + page_status[page_name]['state'])

        state_counts[page_status[page_name]['state']] += 1

    print('SUMMARY:')
    for state in state_counts:
        print(state, state_counts[state])

    if state_counts['WAITING'] + state_counts['PROCESSING'] == 0:
        print('ALL PAGES DONE')
        numberOfFiles = CalculateWC(resultFolder, ".alto", os.path.join(resultFolder, QUALITY_FILE))
        comparison = CompareQuality(workingFolder, resultFolder)
        UpdateResult(requestId, str(round((numberOfFiles - len(comparison))/numberOfFiles*100) if numberOfFiles > 0 else 0) + " %")
        UpdateStatus(requestId, "processed")
        ProcessResult(resultFolder)
        ShowSuccess2("Results retrieved")
    else:
        ShowError2("All files are not yet processed, please try again later")
    LoadData(tree)

def ProcessResult(folder):
    txtFolder = os.path.join(folder, TXT_FOLDER)
    altoFolder = os.path.join(folder, ALTO_FOLDER)
    os.makedirs(txtFolder, exist_ok=True)
    os.makedirs(altoFolder, exist_ok=True)

    for filename in os.listdir(folder):         # Iterate through all files in the folder
        file_path = os.path.join(folder, filename)
        
        if os.path.isfile(file_path):
            new_name = filename.replace('.jpg', '')     # Remove ".jpg" from filename if present
            
            if filename.endswith('.txt'):
                new_path = os.path.join(txtFolder, new_name)
                shutil.move(file_path, new_path)        # Move .txt files to the "txt" subfolder

            elif filename.endswith('.alto'):
                new_name = new_name.replace('.alto', '.xml')        # Change extension from .xml to .alto and move to the "alto" subfolder
                new_path = os.path.join(altoFolder, new_name)
                shutil.move(file_path, new_path)

def ShowDetails(data):
    messagebox.showinfo("Details", f"{data}")
    
def show_context_menu(event):
    selected_item = tree.identify_row(event.y)
    if selected_item:
        tree.selection_set(selected_item)
        if tree.item(selected_item)['values'][6] != "sent":
            context_menu.entryconfigure("Replace files", state=NORMAL)
            context_menu.entryconfigure("Compare quality", state=NORMAL)
        else:
            context_menu.entryconfigure("Replace files", state=DISABLED)
            context_menu.entryconfigure("Compare quality", state=DISABLED)
        context_menu.post(event.x_root, event.y_root)

def on_context_menu_click(action):
    selected_item = tree.selection()[0]
    item_values = tree.item(selected_item, 'values')
    id = item_values[3]
    match action:
        case "Retrieve":
            RetrieveResult(serverUrlTextbox.get("1.0", END).strip(), apiKeyTextbox.get("1.0", END).strip(), id, item_values[2])
        case "Compare":
            ShowQualityComparison(item_values[2], os.path.join(item_values[2], RESULT_FOLDER))
        case "Replace":
            ReplaceFiles(os.path.join(item_values[2], RESULT_FOLDER), item_values[1], item_values[0], item_values[2], id)
        case "Open":
            folder = item_values[1]
            if item_values[7] != '':
                folder = os.path.join(item_values[2], RESULT_FOLDER)
            OpenFolder(folder)
        case "Delete":
            DeleteData(id, item_values[2], item_values[0], item_values[1])
        case "Details":
            ShowDetails(item_values)
        

def on_tree_click(event):
    selected_item = tree.identify_row(event.y)
    if selected_item:
        tree.selection_set(selected_item)
        item_values = tree.item(selected_item, 'values')
        ShowDetails(item_values)

progress2 = StringVar()
progress2.set('')

table_frame = ttk.Frame(tab2)
table_frame.pack(expand=True, fill='both')

progressLabel2 = ttk.Label(table_frame, textvariable = progress2)
progressLabel2.pack(side=TOP, pady=10)

columns = ('#1', '#2', '#3', '#4', '#5', '#6', '#7')
tree = ttk.Treeview(table_frame, columns=columns, show='headings')
tree.tag_configure('oddrow', background="lightgrey")
tree.tag_configure('evenrow', background="white")
tree.tag_configure('spacer', background='white')
style = ttk.Style()
style.configure("Treeview", rowheight=30)

# Create a vertical scrollbar for the Treeview
scrollbar = ttk.Scrollbar(table_frame, orient=VERTICAL, command=tree.yview)
tree.configure(yscroll=scrollbar.set)

# Load CSV content into the treeview
LoadData(tree)

# Pack the Treeview and scrollbar
tree.pack(side=LEFT, expand=True, fill='both')
scrollbar.pack(side=RIGHT, fill='y')

# Create the context menu
global context_menu
context_menu = Menu(tab2, tearoff=0)
context_menu.add_command(label="Retrieve result", command=lambda: on_context_menu_click("Retrieve"))
context_menu.add_command(label="Compare quality", command=lambda: on_context_menu_click("Compare"))
context_menu.add_command(label="Replace files", command=lambda: on_context_menu_click("Replace"))
context_menu.add_separator()
context_menu.add_command(label="Open folder", command=lambda: on_context_menu_click("Open"))
context_menu.add_command(label="Details", command=lambda: on_context_menu_click("Details"))
context_menu.add_separator()
context_menu.add_command(label="Delete", command=lambda: on_context_menu_click("Delete"))

# Bind right-click event to the treeview
tree.bind("<Button-3>", show_context_menu)
tree.bind("<Double-1>", on_tree_click)


###############################################################################
# tab 3 - nahrazení souborů
###############################################################################

def CopyFiles(sourceFolder, destinationFolder):
    fileNames = [f for f in sorted(os.listdir(destinationFolder))]
    files = [f for f in sorted(os.listdir(sourceFolder))]
    for i in range(len(fileNames)):
        sourcePath = os.path.join(sourceFolder, files[i])
        destinationPath = os.path.join(destinationFolder, fileNames[i])
        shutil.copy2(sourcePath, destinationPath)

def GenerateMD5(filePath):
    md5 = hashlib.md5()
    
    with open(filePath, "rb") as file:
        # Read the file in chunks to handle large files
        for chunk in iter(lambda: file.read(8192), b""):
            md5.update(chunk)
    
    return md5.hexdigest()

def GenerateMD5File(folderPath, outputPath, excludedFiles):      
    with open(outputPath, "w") as output:
        for foldername, subfolders, filenames in os.walk(folderPath):
            for filename in filenames:
                filePath = os.path.join(foldername, filename)
                if filePath in excludedFiles:
                    continue  # Skip generating hash for excluded files   
                md5Hash = GenerateMD5(filePath)
                relativePath = "/" + os.path.relpath(filePath, folderPath).replace("\\", "/")
                output.write(f"{md5Hash} {relativePath}\n")
                #print(f"Processed {file_path}")

def ReplaceChecksum(file, value):
    try:
        tree = ET.parse(file)
        root = tree.getroot()

        checksumElement = root.find(".//checksum")      # Find the element with the name "checksum"

        if checksumElement is not None:
            checksumElement.set("checksum", value)      # Update the "checksum" attribute with the new value
            tree.write(file)                            # Save the modified XML back to the file
        else:
            ShowError2("'checksum' element not found in the XML file.")

    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
    except Exception as e:
        print(f"Error: {e}")

def FindFile(folder, prefix, suffix):
    for filename in os.listdir(folder):
        if filename.startswith(prefix) and filename.endswith(suffix):
            return os.path.join(folder, filename)
    return None

def CountFilesInFolder(folderPath):
    if os.path.isdir(folderPath):
        return len([f for f in os.listdir(folderPath)])
    else:
        return 0

def ReadWCFromCsv(csvFile):
    wc_data = []
    with open(csvFile, mode='r', newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            wc_value = float(row['Average WC'])
            wc_data.append(wc_value)                # Store WC value by row index
    return wc_data

def ReadFilenames(csvFile):
    file_names = []
    with open(csvFile, mode='r', newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            file_names.append(row['File Name'])
    return file_names

def CompareQuality(originalFolder, resultFolder):
    originalQuality = os.path.join(originalFolder, QUALITY_FILE)
    resultQuality = os.path.join(resultFolder, QUALITY_FILE)
    
    wc_data_file1 = ReadWCFromCsv(originalQuality)
    wc_data_file2 = ReadWCFromCsv(resultQuality)

    file_names = ReadFilenames(originalQuality)  # Use the file names from the first file (in order)

    results = []
    for index, (wc1, wc2) in enumerate(zip(wc_data_file1, wc_data_file2)):
        results.append([file_names[index], wc1, wc2])

    return results

def ShowQualityComparison(originalFolder, resultFolder):
    results = CompareQuality(originalFolder, resultFolder)
    SaveQualityComparison(results, originalFolder)
    ShowTable(results, originalFolder)

def ShowTable(data, workingFolder):
    table_window = Toplevel()               # Create a new window for the table
    table_window.title("Result comparison")
    table_window.geometry("800x600")

    show_button = ttk.Button(table_window, text="Open in .csv", command=lambda: OpenCsv(os.path.join(workingFolder, QUALITYCOMPARISON_FILE)))
    show_button.pack(pady=10)

    monospace_font = font.Font(family="Courier", size=10)       # Set up a monospace font for alignment

    frame = Frame(table_window)             # Create a Frame to hold the Text widget and Scrollbar
    frame.pack(expand=True, fill="both")

    text_widget = Text(frame, wrap="none", font=monospace_font)     # Add a Text widget to display the table
    text_widget.pack(side="left", expand=True, fill="both")

    scrollbar = Scrollbar(frame, orient="vertical", command=text_widget.yview)      # Add a vertical scrollbar
    scrollbar.pack(side="right", fill="y")

    text_widget.configure(yscrollcommand=scrollbar.set)         # Link the Text widget to the scrollbar

    header = f"{'Page':<50} {'Original':>10} {'New':>10}\n"
    text_widget.insert("end", header)
    text_widget.insert("end", "=" * len(header) + "\n")

    for idx,row in enumerate(data):             # Add data rows
        title, value1, value2 = row
        row_text = f"{title:<50} {value1:>10.2f} {value2:>10.2f}\n"
        start_index = text_widget.index("end")  # Start index of the row text
        text_widget.insert("end", row_text)

        if value1 >= value2:
            bold_start = 57
        else:
            bold_start = 68

        rowNr = idx + 3
        text_widget.tag_add("bold", str(rowNr) + "." + str(bold_start), str(rowNr) + "." + str(bold_start+4))       # Highlight the larger value

    text_widget.tag_configure("bold", background="yellow")          # Configure the bold tag to mean yellow background
    text_widget.config(state="disabled")                            # Disable editing of the Text widget

def SaveQualityComparison(results, workingFolder):
    with open(os.path.join(workingFolder, QUALITYCOMPARISON_FILE), mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Title', 'Original', 'New'])
        writer.writerows(results)

def OpenCsv(file_path):
    if os.path.exists(file_path):
        system_name = platform.system()
        if system_name == "Windows":
            os.startfile(file_path)  # Windows
        elif system_name == "Darwin":
            os.system(f"open '{file_path}'")  # macOS
        elif system_name == "Linux":
            os.system(f"xdg-open '{file_path}'")  # Linux

def ReplaceFiles(sourceFolder, destinationFolder, destinationPackage, workingFolder, id = None):
    UpdateProgress2("Creating backup of PSP")
    CreateBackup(destinationPackage)
    
    altoSourceFolder = os.path.join(sourceFolder, ALTO_FOLDER)
    txtSourceFolder = os.path.join(sourceFolder, TXT_FOLDER)
    altoDestinationFolder = os.path.join(destinationFolder, ALTO_FOLDER)
    txtDestinationFolder = os.path.join(destinationFolder, TXT_FOLDER)
    checksumFile = FindFile(destinationFolder, MD5_PREFIX, ".md5")
    infoFile = FindFile(destinationFolder, INFO_PREFIX, ".xml")

    UpdateProgress2("Replacing ALTO")
    originalFilesCount = CountFilesInFolder(altoDestinationFolder)
    newFilesCount = CountFilesInFolder(altoSourceFolder)
    if originalFilesCount == newFilesCount:
        CopyFiles(altoSourceFolder, altoDestinationFolder)
        #print(f"ALTO updated")
    else:
        ShowError2(f"ALTO not updated: Number of files does not match! Number of original files: {originalFilesCount}; number of new files: {newFilesCount}.")
        return

    UpdateProgress2("Replacing TXT")
    originalFilesCount = CountFilesInFolder(txtDestinationFolder)
    newFilesCount = CountFilesInFolder(txtSourceFolder)
    if originalFilesCount == newFilesCount:
        CopyFiles(txtSourceFolder, txtDestinationFolder) 
        #print(f"TXT updated")
    else:
        ShowError2(f"TXT not updated: Number of files does not match! Number of original files: {originalFilesCount}; number of new files: {newFilesCount}.")
        return

    UpdateProgress2("Replacing hash")
    GenerateMD5File(destinationFolder, checksumFile, [os.path.join("", checksumFile), os.path.join("", infoFile)])
    #print(f"md5 updated")

    ReplaceChecksum(infoFile, GenerateMD5(checksumFile))
    #print(f"checksum updated")

    if os.path.isfile(destinationPackage):
        UpdateProgress2("Zipping")
        #print(destinationPackage)
        ZipFolder(destinationFolder, destinationPackage)

    if id != None:
        UpdateStatus(id, "replaced")
        LoadData(tree)
        DeleteData(id, workingFolder, destinationPackage, destinationFolder)

    ShowSuccess2("Replaced")

def CreateBackup(package):
    if os.path.isfile(package):
        backup_zip = package.replace('.zip', '_backup.zip')
        shutil.copyfile(package, backup_zip)
    elif os.path.isdir(package):
        backup_folder = f"{package}_backup"
        shutil.copytree(package, backup_folder)

def ZipFolder(folder, destination):
    baseFolder = os.path.basename(folder)
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.join(baseFolder, os.path.relpath(file_path, folder))        # Create the relative path to store in the zip file (starting with the folder name)
                zipf.write(file_path, relative_path)                                                # Add the file to the zip archive with the correct folder structure

###############################################################################
# načtení nastavení a spuštění programu
###############################################################################
LoadSettings()
LoadEngines(serverUrlTextbox.get("1.0", END).strip(), apiKeyTextbox.get("1.0", END).strip(), loadEnginesButton)

root.mainloop()
