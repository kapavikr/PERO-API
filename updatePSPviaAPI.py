from tkinter import *
from tkinter import ttk
from tkinter import filedialog
import os
import zipfile
from PIL import Image
import requests
  
def CreateButtonRow(frame, rowIndex, text, command, var):
    button = ttk.Button(frame, width=15, text = text, padding=5, command=command)
    button.grid(row = rowIndex, column = 0, padx = 0, pady = 10)
    if (var != None):
        label = Label(frame, textvariable = var)
        label.grid(row = rowIndex, column = 1, sticky = W, padx = 10, pady = 10)
        
def CreateTextBoxRow(frame, rowIndex, text):
    label = ttk.Label(frame, text = text)
    label.grid(row = rowIndex, column = 0, padx = 10, pady = 10)
    textBox = Text(frame, wrap='word', width=50, height=1)
    textBox.grid(row = rowIndex, column = 1, sticky = W, padx = 10, pady = 10)
    return textBox
    
def CreateRadioButtonRow(frame, rowIndex, value, text, var):
    radioButton = ttk.Radiobutton(frame, text=text, variable=var, value=value)
    radioButton.grid(row = rowIndex, column = 1, sticky = W, padx = 10, pady = 10)
        
def ShowAvailableEngines(serverUrl, apiKey, var):
    r = requests.get(f"{serverUrl}/get_engines", headers={"api-key": apiKey})
    if r.status_code != 200:
        return 'ERROR: Failed to get available OCR engine list. Code: {r.status_code}'
    result = r.json()
    if result['status'] not in ["success", "succes"]:
        return 'ERROR: Failed to get available OCR engine list. Status: {result["status"]}'
    engines = result['engines']
    buttonLoadEngines.destroy()
    row = 3
    for idx, value in enumerate(engines):
        row+=idx
        CreateRadioButtonRow(tab1, row, engines[value]['id'], value, engine)
        if (idx == 0):
            engine.set(engines[value]['id'])
    row+=1
    CreateSelectFoldersControls(row)
    
def CreateSelectFoldersControls(row):
    label = ttk.Label(tab1, text = "Select source PSP and working folder, to which unzipped data will be saved:")
    label.grid(row = row, column = 0, columnspan = 2, sticky = W, padx = 10, pady = 10)

    CreateButtonRow(tab1, row+1, "PSP folder", OpenPSPFile, pspFile)
    CreateButtonRow(tab1, row+2, "Working folder", OpenWorkingFolder, workingFolder)
    global sendButton
    sendButton = ttk.Button(tab1, width=15, text = "Send to PERO", padding=5, command=Run)
    sendButton.grid(row = row+3, column = 0, columnspan = 2, padx = 10, pady = 10)
    sendButton["state"] = "disable"
    
        
def OpenPSPFile():
    global lastDir
    global sendButton
    path = filedialog.askopenfilename(
        title="Select PSP file",
        filetypes=[("ZIP files", "*.zip")])
    pspFile.set(path)
    print(path)
    lastDir = os.path.dirname(path)
    workingFolder.set(lastDir)
    if (path != ""):
        sendButton["state"] = "normal"
    else:
        sendButton["state"] = "disabled"

def OpenWorkingFolder():
    global lastDir
    path = filedialog.askdirectory(initialdir=lastDir, title="Choose working folder")
    workingFolder.set(path)
    lastDir = os.path.dirname(path)
    if (path == ""):
        sendButton["state"] = "disabled"
  
def Run():
    workingPath = workingFolder.get()
    
    # 1) Unzip the folder with PSP data
    unzippedName = Unzip(pspFile.get(), workingPath)
    
    # 2) Convert jp2s to jpgs with max quality (95); TODO: when the result is > 8 MB, we should lower the quality to get under 8 MB 
    masterCopyPath = os.path.join(workingPath, unzippedName[0], "mastercopy")
    imagesPath = os.path.join(workingPath, "jpg")
    ConvertJP2toJPG(masterCopyPath, imagesPath)
 
    # 3) Create file contaning all filenames
    CreateFilelist(imagesPath, os.path.join(imagesPath, "list.txt"))
 
def Unzip(zip, to):
    print("to:" + to)
    if not os.path.exists(to):
        os.makedirs(to)
    with zipfile.ZipFile(zip, 'r') as zip_ref:
        zip_ref.extractall(to)
    return zip_ref.namelist()

def ConvertJP2toJPG(input, output, quality=95):
    if not os.path.exists(output):
        os.makedirs(output)
        
    for filename in os.listdir(input):
        if filename.lower().endswith('.jp2'):
            jp2Path = os.path.join(input, filename)
            img = Image.open(jp2Path)
            jpgFilename = os.path.splitext(filename)[0] + '.jpg'
            jpgPath = os.path.join(output, jpgFilename)
            img.convert('RGB').save(jpgPath, 'JPEG', quality=quality)
            
def CreateFilelist(directoryPath, filePath):
    if os.path.exists(filePath):
        os.remove(filePath)
        
    files = os.listdir(directoryPath)
    with open(filePath, 'w') as file:
        for filename in files:
            file.write(filename + '\n')
 
 
# GUI   
root = Tk()
root.geometry("800x600")

root.title("updatePSPviaAPI") 
tabControl = ttk.Notebook(root) 
  
tab1 = ttk.Frame(tabControl) 
tab2 = ttk.Frame(tabControl)

tabControl.add(tab1, text ='Tab 1') 
tabControl.add(tab2, text ='Tab 2') 
tabControl.pack(expand = 1, fill ="both")

# Tab 1 - Výběr PSP balíčku, jeho rozzipování, konfigurace PERO a jeho odeslání k přečtení

tab1.columnconfigure(0, minsize=150)
tab1.columnconfigure(1, minsize=550)

NOT_SELECTED = "[Folder not selected]"
pspFile = StringVar()
workingFolder = StringVar()
engine = StringVar()
pspFile.set(NOT_SELECTED)
workingFolder.set(NOT_SELECTED)

serverUrl = CreateTextBoxRow(tab1, 1, "Server URL:")
serverUrl.insert(END, "https://pero-ocr.fit.vutbr.cz/api")
apiKey = CreateTextBoxRow(tab1, 2, "API key:")
apiKey.insert(END, "Nl6AxLWWvf0JxRSievnM2WLnGyCgrGWbsInx1ZPTctE")

label = ttk.Label(tab1, text = "Engine:")
label.grid(row = 3, column = 0, padx = 10, pady = 10)
buttonLoadEngines = ttk.Button(tab1, width=15, text = "Load engines", padding=5, command=lambda: ShowAvailableEngines(serverUrl.get("1.0",END).strip(), apiKey.get("1.0",END).strip(), engine))
buttonLoadEngines.grid(row = 3, column = 1, padx = 10, pady = 10)

if (serverUrl.get("1.0",END).strip() != "" and apiKey.get("1.0",END).strip() != ""):
    ShowAvailableEngines(serverUrl.get("1.0",END).strip(), apiKey.get("1.0",END).strip(), engine)

# Tab 2 - Přehled přečtených balíčků, výsledky a možnost výměny dat za data z PERO

label = ttk.Label(tab2, text = "Pending packages.")
label.grid(row = 0, column = 0, columnspan = 2, padx = 10, pady = 10)

label = ttk.Label(tab2, text = "Package 1 with quite a long title")
label.grid(row = 1, column = 0, padx = 10, pady = 10)

label = ttk.Label(tab2, text = "Button")
label.grid(row = 1, column = 1, padx = 10, pady = 10)
  
root.mainloop()   
