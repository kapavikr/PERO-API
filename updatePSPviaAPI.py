from tkinter import *
from tkinter import ttk
from tkinter import filedialog
import os
  
def CreateRow(frame, rowIndex, text, command, var):
    button = ttk.Button(frame, width=15, text = text, command=command)
    button.grid(row = rowIndex, column = 0, padx = 10, pady = 10)
    if (var != None):
        label = Label(frame, textvariable = var)
        label.grid(row = rowIndex, column = 1, sticky = W, padx = 10, pady = 10)
        
def OpenPSPFolder():
    global lastDir
    path = filedialog.askopenfilename(
        title="Select PSP file",
        filetypes=[("ZIP files", "*.zip")])
    pspFolder.set(path)
    lastDir = os.path.dirname(path)
    workingFolder.set(lastDir)

def OpenWorkingFolder():
    global lastDir
    path = filedialog.askdirectory(initialdir=lastDir, title="Choose PSP")
    pspFolder.set(path)
    lastDir = os.path.dirname(path)
  
def Run():
    print("Send to PERO")
    
root = Tk()
root.geometry("800x400")

root.columnconfigure(0, minsize=150)
root.columnconfigure(1, minsize=550)

NOT_SELECTED = "[Folder not selected]"
pspFolder = StringVar()
workingFolder = StringVar()
pspFolder.set(NOT_SELECTED)  
workingFolder.set(NOT_SELECTED) 


root.title("updatePSPviaAPI") 
tabControl = ttk.Notebook(root) 
  
tab1 = ttk.Frame(tabControl) 
tab2 = ttk.Frame(tabControl)
  
tabControl.add(tab1, text ='Tab 1') 
tabControl.add(tab2, text ='Tab 2') 
tabControl.pack(expand = 1, fill ="both")

label = ttk.Label(tab1, text = "Select source PSP and working folder, to which unzipped data will be saved.")
label.grid(row = 0, column = 0, columnspan = 2, padx = 10, pady = 10)

CreateRow(tab1, 1, "PSP folder", OpenPSPFolder, pspFolder)
CreateRow(tab1, 2, "Working folder", OpenWorkingFolder, workingFolder)  

button = ttk.Button(tab1, width=15, text = "Send to PERO", command=Run)
button.grid(row = 3, column = 0, columnspan = 2, padx = 10, pady = 10)

label = ttk.Label(tab2, text = "Pending packages.")
label.grid(row = 0, column = 0, columnspan = 2, padx = 10, pady = 10)

label = ttk.Label(tab2, text = "Package 1 with qute a long title")
label.grid(row = 1, column = 0, padx = 10, pady = 10)

label = ttk.Label(tab2, text = "Button")
label.grid(row = 1, column = 1, padx = 10, pady = 10)
  
root.mainloop()   
