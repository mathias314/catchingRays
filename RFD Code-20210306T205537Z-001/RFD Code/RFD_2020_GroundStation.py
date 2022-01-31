#####################################################################################
#   PC interface for RFD900_Pi_V8 over the RFD900 Modem using a baudrate of 57600   #
#   to send photos and real time data. Constructed for MSGC Borealis program.       #
#   Author: Dylan Trafford in 1/19/2015 for MSFC                                    #
#                                                                                   #
#   Editor: Dalton Lund (SDSGC) Created: 6/16/2020     Python Version: 3.7.6        #
#                               Edited: Constantly :)  OS: Windows 10.18363.778     #
#                                                                                   #
#####################################################################################

# Library Imports

# Used Libraries

import time  # = native time functions (ex. runtime)
import datetime
import serial  # = RS232 software serial modules on Rx Tx pins
import base64  # = encodes an image in b64 Strings (and decodes)
import hashlib  # = generates hashes
import subprocess
import sys
import PIL.Image  # = for image processing
from PIL import ImageTk
from tkinter import *
import tkinter as tk
from tkinter import messagebox
from array import array  # = for generating a byte array
import os  # = ?? was required for io module to convert Image to bytes
import io  # = creating a String or Byte Array of data (streaming images)

#folder = "/Desktop/RFD Ground Station"
folder ="/Desktop/RFD Ground Station/%s/" % time.strftime("%m%d%Y_%H%M%S")
dir = os.path.dirname(folder)
if (not os.path.exists(dir)):
    os.makedirs(dir)

# Serial Variables
rfdport = "COM5"  # This is a computer dependent setting.
# Open Device Manager to determine which port the RFD900 Modem is plugged into
rfdbaud = 57600
rfdtimeout = 5  # Sets the ser.read() timeout period, or when to continue in the
# code when no data is received after the timeout period (in seconds)

# Initializations
ser = serial.Serial(port=rfdport, baudrate=rfdbaud, timeout=rfdtimeout)
wordlength = 10000  # Variable to determine spacing of checksum.
imagedatasize = 10000
extension = ".jpg"
timeupdateflag = 0  # determines whether to update timevar on the camera settings

# Camera Variables
width = 650
height = 450
sharpness = 0  # Default  =0; range = (-100 to 100)
brightness = 50  # Default = 50; range = (0 to 100)
contrast = 0  # Default = 0; range = (-100 to 100)
saturation = 0  # Default = 0; range = (-100 to 100)
iso = 400  # Default; range = (100 to 800)
angle = 90 # Default; range = (45 to 135)

file = open('camerasettings.txt', 'w')
file.close()


def updateslider():
    # Updates the slider values in the Gui
    try:
        global width
        global height
        global sharpness
        global brightness
        global contrast
        global saturation
        global iso
        global timeupdateflag
        global angle
        widthslide.set(width)
        heightslide.set(height)
        sharpnessslide.set(sharpness)
        brightnessslide.set(brightness)
        contrastslide.set(contrast)
        saturationslide.set(saturation)
        isoslide.set(iso)
        angleslide.set(angle)
    except:
        print("error setting slides to new values")
        print("here are current values")
        print(width, height, sharpness, brightness, contrast, saturation, iso, angle)
        sys.stdout.flush()
    try:
        if (timeupdateflag == 1):
            timevar.set(
                "Last Updated: " + str(datetime.datetime.now().strftime("%Y/%m/%d @ %H:%M:%S")))
            timeupdateflag = 0
        else:
            timevar.set("No Recent Update")
        widthvar.set("Current Width = " + str(width))
        heightvar.set("Current Height = " + str(height))
        sharpnessvar.set("Current Sharpness = " + str(sharpness))
        brightnessvar.set("Current Brightness = " + str(brightness))
        contrastvar.set("Current Contrast = " + str(contrast))
        saturationvar.set("Current Saturation = " + str(saturation))
        isovar.set("Current ISO = " + str(iso))
        anglevar.set("Current Cam Angle = " + str(angle))
    except:
        print("error setting slides to new values")
        print("here are current values")
        print(width, height, sharpness, brightness, contrast, saturation, iso, angle)


def reset_cam():
    global width
    global height
    global sharpness
    global brightness
    global contrast
    global saturation
    global iso
    global angle
    width = 650
    height = 450
    sharpness = 0  # Default  =0; range = (-100 to 100)
    brightness = 50  # Default = 50; range = (0 to 100)
    contrast = 0  # Default = 0; range = (-100 to 100)
    saturation = 0  # Default = 0; range = (-100 to 100)
    iso = 400  # Default; range = (100 to 800)
    angle = 90 # Default; range = (45 to 90)
    print("Default width:", width)
    print("Default height:", height)
    print("Default sharpness:", sharpness)
    print("Default brightness:", brightness)
    print("Default contrast:", contrast)
    print("Default saturation:", saturation)
    print("Default ISO:", iso)
    print("Default Angle:", angle)
    sys.stdout.flush()
    try:
        widthslide.set(width)
        heightslide.set(height)
        sharpnessslide.set(sharpness)
        brightnessslide.set(brightness)
        contrastslide.set(contrast)
        saturationslide.set(saturation)
        isoslide.set(iso)
        angleslide.set(angle)
    except:
        print("error setting slides to new values")
        print("here are current values")
        print(width, height, sharpness, brightness, contrast, saturation, iso, angle)
        sys.stdout.flush()
    return


def image_to_b64(path):
    # Converts an image to 64 bit encoding
    with open(path, "rb") as imageFile:
        return base64.b64encode(imageFile.read())


def b64_to_image(data, savepath):
    # Converts a 64 bit encoding to an image
    fl = open(savepath, "wb")
    fl.write(base64.b64decode(data))
    fl.close()


def gen_checksum(data):
    # Creates a checksum based on data
    return hashlib.md5(data).hexdigest()


def sendword(data, pos):
    # Sends the appropriately sized piece of the total picture encoding
    if (pos + wordlength < len(data)):  # Take a piece of size self.wordlength from the whole, and send it
        ser.write(data[pos:pos + wordlength])
        print(data[pos:pos + wordlength])
        return
    else:  # If the self.wordlength is greater than the amount remaining, send everything left
        ser.write(data[pos:pos + len(data)])
        print(data[pos:pos + len(data)])
        return


def sync():
    # Synchronizes the data stream between the ground station and the Pi
    print("Attempting to Sync - This should take approx. 2 sec")
    middleman = b''
    sync = ''
    addsync0 = ''
    addsync1 = ''
    addsync2 = ''
    addsync3 = ''
    while (sync != "sync"):
        # Program is held until no data is being sent (timeout) or until the pattern 's' 'y' 'n' 'c' is found
        middleman = ser.read()
        addsync0 = middleman.decode('utf-8')
        addsync0 = str(addsync0)
        if (addsync0 == ''):
            break
        sync = addsync3 + addsync2 + addsync1 + addsync0
        addsync3 = addsync2
        addsync2 = addsync1
        addsync1 = addsync0
    sync = ""
    ser.write(b'S')
    # Notifies sender that the receiving end is now synced
    print("System Match")
    time.sleep(0.5)

    # Flush buffers to be ready
    ser.flushInput()
    ser.flushOutput()
    return


def receive_image(savepath, wordlength):
    print("confirmed photo request")  # Notifies User we have entered the receiveimage() module
    sys.stdout.flush()
    # Module Specific Variables
    trycnt = 0  # Initializes the checksum timeout (timeout value is not set here)
    finalstring = b''  # Initializes the data string so that the += function can be used
    done = False  # Initializes the end condition
    # Retrieve Data Loop (Will end when on timeout)
    while (not done):
        print("Current Receive Position: ", str(len(finalstring)))
        checktheirs = ""
        checktheirs = ser.read(32)  # Asks first for checksum.
        checktheirs = checktheirs.decode('utf-8')
        # Checksum is asked for first so that if data is less than wordlength, it won't error out the checksum data
        word = ser.read(wordlength)  # Retrieves characters,
        # wholes total string length is predetermined by variable wordlength
        checkours = gen_checksum(word)  # Retrieves a checksum based on the received data string
        # CHECKSUM gen_checksum(word, checktheirs
        if (checkours != checktheirs):
            if (trycnt < 10):  # This line sets the maximum number of checksum resend attempts.
                # Ex. trycnt = 5 will attempt to receive data 5 times before failing
                # #I've found that the main cause of checksum errors is a bit drop or add desync, this adds a 2
                # second delay and resyncs both systems
                ser.write(b'N')
                trycnt += 1
                print("try number:", str(trycnt))
                print("\tresend last")  # This line is mostly used for troubleshooting,
                # allows user to view that both devices are at the same position when a checksum error occurs
                print("\tpos @", str(len(finalstring)))
                sys.stdout.flush()
                sync()  # This corrects for bit deficits or excesses
                # ######  THIS IS A MUST FOR DATA TRANSMISSION WITH THE RFD900s!!!! #####
            else:
                ser.write(b'N')  # Kind of a worst case, checksum trycnt is reached
                # so we save the image and end the receive, a partial image will render if enough data
                finalstring += word
                done = True
                break
        else:
            trycnt = 0
            ser.write(b'Y')
            finalstring += word
        if (word == ""):
            done = True
            break
        if (checktheirs == ""):
            done = True
            break
    try:  # This will attempt to save the image as the given filename,
        # if it for some reason errors out, the image will go to the except line
        b64_to_image(finalstring, savepath)
        imagedisplay.set(savepath)
    except:
        print("Error with filename, saved as newimage" + extension)
        sys.stdout.flush()
        b64_to_image(finalstring, "newimage" + extension)
        # Save image as newimage.jpg due to a naming error

    print("Image Saved")
    sys.stdout.flush()


def mostRecentImage():
    # Command 1: Download most recent image
    global im
    global photo
    global tmplabel
    global reim
    ser.write(b'1')
    killtime = 0
    while (ser.read() != b'A'):  # Waiting for Pi to acknowledge
        print("Waiting for Acknowledge")
        sys.stdout.flush()
        ser.write(b'1')
        killtime += 1
        if(killtime == 10):
            print("No Acknowledge Received. Please try again")
            return
    sendfilename = b''
    temp = 0
    while (temp <= 14):
        sendfilename += ser.read()
        temp += 1
    sendfilename = sendfilename.decode('utf-8')
    imagepath = imagename.get()
    if (imagepath == ""):
        try:
            if (sendfilename[0] == "i"):
                imagepath = sendfilename
            else:
                imagepath = ("image_%s%s" % (
                    str(datetime.datetime.now().strftime("%Y%m%d_T%H%M%S")), extension))
        except:
            imagepath = ("image_%s%s" % (str(datetime.datetime.now().strftime("%Y%m%d_T%H%M%S")), extension))
    else:
        imagepath = (imagepath + extension)
    
    print("Image will be saved as:", imagepath)
    messagebox.showinfo("In Progress..", message="Image request received.\nImage will be saved as " + imagepath)
    timecheck = time.time()
    sys.stdout.flush()
    receive_image(str(imagepath), wordlength)
    im = PIL.Image.open(str(imagepath))
    reim = im.resize((650, 450), PIL.Image.ANTIALIAS)
    photo = ImageTk.PhotoImage(reim)
    tmplabel.configure(image=photo)
    tmplabel.pack(fill=BOTH, expand=1)
    print("Receive Time =", (time.time() - timecheck))
    sys.stdout.flush()
    return


def imageData():
    # Command 2: Requests the imagedata.txt file that shows all images taken during current flight
    try:
        listbox.delete(0, END)
    except:
        print("Failed to delete Listbox, window may have been destroyed")
        sys.stdout.flush()
    ser.write(b'2')
    while (ser.read() != b'A'):
        print("Waiting for Acknowledge")
        sys.stdout.flush()
        ser.write(b'2')
    try:
        datafilepath = datafilename.get()
        if (datafilepath == ""):
            datafilepath = "imagedata"
        file = open(datafilepath + ".txt", "w")
    except:
        print("Error with opening file")
        sys.stdout.flush()
        return
    sys.stdin.flush()
    timecheck = time.time()
    temp = ser.readline()
    while (temp != b''):
        file.write(temp.decode('utf-8'))
        try:
            listbox.insert(0, temp)
        except:
            print("error adding items")
            break
        temp = ser.readline()
    file.close()
    print("File Received, Attempting Listbox Update")
    sys.stdin.flush()
    subGui.lift()
    subGui.mainloop()
    return


def requestedImage():
    # Command 3: request specific image
    global im
    global photo
    global tmplabel
    global reim
    random = 0
    item = map(int, listbox.curselection())
    try:
        data = listbox.get(ACTIVE)
    except:
        print("Nothing Selected")
        sys.stdout.flush()
        return
    data = data[0:15]
    data = data.decode('utf-8')
    if (data[10] != 'b'):
        result = messagebox.askquestion("W A R N I N G", message="You have selected the high resolution image."
                                                                 "\n Are you sure you want to continue?\n"
                                                                 "This download could take 15+ min.",
                                        icon="warning")
        if (result == 'yes'):
            ser.write(b'3')
            while (ser.read() != b'A'):
                print("Waiting for Acknowledge")
                sys.stdout.flush()
                random += 1
                if (random > 5):
                    return
            imagepath = data
            ser.write(data.encode('utf-8'))
            timecheck = time.time()
            messagebox.showinfo("In Progress...",
                                message="Image request received.\nImage will be saved as " + imagepath)
            print("Image will be saved as:", imagepath)
            sys.stdout.flush()
            receive_image(str(imagepath), wordlength)
            im = PIL.Image.open(imagepath)
            reim = im.resize((650, 450), PIL.Image.ANTIALIAS)
            photo = ImageTk.PhotoImage(reim)
            tmplabel.configure(image=photo)
            tmplabel.pack(fill=BOTH, expand=1)
            print("Receive Time =", (time.time() - timecheck))
            return
        else:
            return
    else:
        ser.write(b'3')
        while (ser.read() != b'A' and random < 5):
            print("Waiting for Acknowledge")
            sys.stdout.flush()
            random += 1
            if (random == 5):
                return
        imagepath = data
        ser.write(data.encode('utf-8'))
        timecheck = time.time()
        messagebox.showinfo("In Progress...",
                            message="Image request received.\nImage will be saved as " + imagepath)
        print("Image will be saved as:", imagepath)
        sys.stdout.flush()
        receive_image(str(imagepath), wordlength)
        im = PIL.Image.open(imagepath)
        reim = im.resize((650, 450), PIL.Image.ANTIALIAS)
        photo = ImageTk.PhotoImage(reim)
        tmplabel.configure(image=photo)
        tmplabel.pack(fill=BOTH, expand=1)
        print("Receive Time =", (time.time() - timecheck))
        return


def retrieveCameraSettings():
    # Command 4: Retrieve the current camera settings from the Pi
    global width
    global height
    global sharpness
    global brightness
    global contrast
    global saturation
    global iso
    global timeupdateflag
    print("Retrieving Camera Settings")
    try:
        killtime = time.time() + 10
        ser.write(b'4')
        while ((ser.read() != b'A') & (time.time() < killtime)):
            print("Waiting for Acknowledge")
            ser.write(b'4')
        timecheck = time.time()
        messagebox.showinfo("In Progress..", message="Downloading Settings")
        try:
            file = open("camerasettings.txt", "w")
            print("File Successfully Created")
        except:
            print("Error with opening file")
            sys.stdout.flush()
            return
        timecheck = time.time()
        temp = b'Y'
        while (temp != b""):
            temp = ser.read()
            file.write(temp.decode('utf-8'))
        file.close()
        print("Receive Time =", (time.time() - timecheck))
        sys.stdout.flush()
        file = open("camerasettings.txt", "r")
        twidth = file.readline()  # Default = 650; range = (1 to 2592)
        width = int(twidth)  # Convert str to int
        print("width = ", width)
        theight = file.readline()  # Default = 450; range = (1 to 1944)
        height = int(theight)  # Convert str to int
        print("height = ", height)
        tsharpness = file.readline()  # Default = 0; range = (-100 to 100)
        sharpness = int(tsharpness)  # Convert str to int
        print("sharpness = ", sharpness)
        tbrightness = file.readline()  # Default = 50; range = (0 to 100)
        brightness = int(tbrightness)  # Convert str to int
        print("brightness = ", brightness)
        tcontrast = file.readline()  # Default = 0; range = (-100 to 100)
        contrast = int(tcontrast)  # Convert str to int
        print("contrast = ", contrast)
        tsaturation = file.readline()  # Default = 0; range = (-100 to 100)
        saturation = int(tsaturation)  # Convert str to int
        print("saturation = ", saturation)
        tiso = file.readline()  # Default - 400; range = (100 to 800)
        iso = int(tiso)  # Convert str to int
        print("iso = ", iso)
        file.close()
        timeupdateflag = 1
        updateslider()
    except:
        print("Camera Setting Retrieval Error")
    return


def uploadCameraSettings():
    # Command 5: Upload new camera settings to the pi from the sliders
    global width
    global height
    global sharpness
    global brightness
    global contrast
    global saturation
    global iso
    width = widthslide.get()
    height = heightslide.get()
    sharpness = sharpnessslide.get()
    brightness = brightnessslide.get()
    contrast = contrastslide.get()
    saturation = saturationslide.get()
    iso = isoslide.get()
    file = open("camerasettings.txt", "w")
    file.write(str(width) + "\n")
    file.write(str(height) + "\n")
    file.write(str(sharpness) + "\n")
    file.write(str(brightness) + "\n")
    file.write(str(contrast) + "\n")
    file.write(str(saturation) + "\n")
    file.write(str(iso) + "\n")
    file.close()
    ser.write(b'5')
    killtime = 0
    while (ser.read() != b'A'):
        print("Waiting for Acknowledge")
        killtime += 1
        if (killtime > 10):
            print("Acknowledge not received")
            return
    timecheck = time.time()
    messagebox.showinfo("In Progress..", message="Downloading Settings")
    try:
        file = open("camerasettings.txt", "r")
    except:
        print("Error with opening file")
        sys.stdout.flush()
        return
    timecheck = time.time()
    temp = b'Y'
    while (temp != b"" and temp !=''):
        temp = file.readline()
        ser.write(temp.encode('utf-8'))
    file.close()
    killtime = 0
    while (ser.read() != b'A'):
        print("Waiting for Acknowledge")
        killtime += 1
        if (killtime > 10):
            print("Acknowledge not received")
            return
    print("Send Time =", (time.time() - timecheck))
    sys.stdout.flush()
    return


def time_sync():
    # Command T: Syncs the time between the ground station and the pi

    ser.flushInput()
    ser.write(b'T')
    termtime = time.time() + 10
    temp = b''
    while (ser.read() != b'T'):
        print("Waiting for Acknowledge")
        ser.write(b'T')
        if (termtime < time.time()):
            print("No Acknowledge Received, Connection Error")
            sys.stdout.flush()
            return
    localtime = str(datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S"))
    killtime = 0
    for x in localtime:
        ser.write(x.encode('utf-8'))
    while (ser.read() != b'T' and killtime < 5):
        print("Waiting for Acknowledge")
        killtime += 1
        for x in localtime:
            ser.write(x.encode('utf-8'))
    temp = ser.readline()
    temp = localtime.encode('utf-8')
    rasptime = temp.decode('utf-8')
    print("##################################\nRaspb Time = %s\nLocal Time = %s\n##################################"
          % (rasptime, localtime))
    sys.stdin.flush()
    connectiontest(10)
    return


def connectiontest(numping):
    # Command P: Sends pings to Pi and returns the pingtime
    ser.write(b'P')
    termtime = time.time() + 20
    while (ser.read() != b'P'):
        print("Waiting for Acknowledge")
        ser.write(b'P')
        if (termtime < time.time()):
            print("No Acknowledge Received, Connection Error")
            sys.stdout.flush()
            return
    avg = 0
    ser.write(b'P')
    temp = ""
    for x in range(1, numping):
        sendtime = time.time()
        receivetime = 0
        termtime = sendtime + 10
        while ((temp != b'P') & (time.time() < termtime)):
            ser.write(b'P')
            temp = ser.read()
            receivetime = time.time()
        if (receivetime == 0):
            print("Connection Error, No return ping within 10 seconds")
            ser.write(b'D')
            sys.stdout.flush()
            return
        else:
            temp = ""
            avg += receivetime - sendtime
    ser.write(b'P')
    avg = avg / numping
    print("Ping Response Time = " + str(avg)[0:4] + " seconds")
    sys.stdout.flush()
    return


def getGPSfile():
    # Command G: Asks for Pi GPS log
    ser.write(b'G')
    killtime = 0
    while (ser.read() != b'A'):
        print("Waiting for Acknowledge")
        sys.stdout.flush()
        ser.write(b'G')
        killtime += 1
        if (killtime > 10):
            print("No Acknowledge Received")
            return
    timecheck = time.time()
    try:
        file = open("gpslog.txt", "w")
    except:
        print("Error with opening file")
        sys.stdout.flush()
        return
    timecheck = time.time()
    sys.stdin.flush()
    termtime = time.time() + 90
    temp = ser.readline()
    while (temp != b""):
        file.write(temp.decode('utf-8'))
        temp = ser.readline()
        if (termtime < time.time()):
            print("Error recieving gpslog.txt")
            file.close()
            return
    file.close()
    print("GPSfile.txt saved to local folder")
    print("Receive Time =", (time.time() - timecheck))
    sys.stdout.flush()
    return


def reboot_pi():
    # Command R: Reboots Pi
    ser.write(b'R')
    while (ser.read() != b'A'):
        print("Waiting for Acknowledge")
        ser.write(b'R')
    print("Pi rebooting. See you soon!")
    return


def device_status():
    # Command D: Gets status of Camera and GPS if the RFD is working
    ser.write(b'D')
    while (ser.read() != b'A'):
        print("Waiting for Acknowledge")
        ser.write(b'D')
    try:
        status = ser.readline()
        print(status.decode('utf-8'))
        time.sleep(2)
    except:
        print("Error with device status")
        sys.stdout.flush()
        return


def shutdown_pi():
    # Command Q: Shuts down the pi. Used once recovered to help ensure no sd card corruption
    ser.write(b'Q')
    while (ser.read() != b'A'):
        print("Waiting for Acknowledge")
        ser.write(b'Q')
    print("Pi is powering off. See you back at home base!")
    return


def set_camera_angle():
    # Command H: Lets you select camera angle based on slider
    global angle
    ser.write(b'H')
    killtime = 0
    temp = ''
    while (ser.read() != b'A'):
        print("Waiting for Acknowledge")
        #ser.write(b'H')
        killtime += 1
        if (killtime > 10):
            print("No Acknowledge Received")
            return
    try:
        angle = angleslide.get()
        temp = angle
        angle = int(angle * 4.4444 + 1300)
        angle = str(angle)
        ser.write(angle.encode('utf-8'))
        angle = temp
        print("Sent Angle to pi camera servo")
    except:
        print("Error with sending angle")
        sys.stdout.flush()
        return
    killtime = 0
    while (ser.read() != b'A'):
        print("Waiting for Acknowledge")
        killtime += 1
        if (killtime > 10):
            print("No Acknowledge Received, Pi failed to adjust Angle")
            return
    print("Pi Has Successfully adjusted Camera Angle")
    updateslider()
    return


class Unbuffered:
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.stream.flush()
        logfile.write(data)
        logfile.flush()

    def flush(self):
        self.stream.flush()

    def close(self):
        self.stream.close()


# ##############################################Contructs the GUI ######################################################

mGui = Tk()
mGui.iconbitmap(default="bc.ico")
imagename = StringVar()
datafilename = StringVar()
imagedisplay = StringVar()
pingcount = StringVar()

widthvar = StringVar()
heightvar = StringVar()
sharpnessvar = StringVar()
brightnessvar = StringVar()
contrastvar = StringVar()
saturationvar = StringVar()
isovar = StringVar()
anglevar = StringVar()
timevar = StringVar()
logfile = open('runtimedata.txt','w')
logfile.close()
logfile = open('runtimedata.txt','a')
sys.stdout = Unbuffered(sys.stdout)


mGui.geometry("1300x550+30+30")
mGui.title("Montana Space Grant Consortium BOREALIS Program")

mlabel = Label(text="RFD900 Interface V8.0", fg='grey', font="Verdana 10 bold")
mlabel.pack()

cmdtitle = Label(text="Command Module", font="Verdana 12 bold")
cmdtitle.place(x=30, y=20)

imagetitle = Label(textvariable=imagedisplay, font="Verdana 12 bold")
imagetitle.place(x=300, y=20)

frame = Frame(master=mGui, width=665, height=465, borderwidth=5, bg="black", colormap="new")
frame.place(x=295, y=45)
im = PIL.Image.open('MSGC2.jpg')
reim = im.resize((650, 450), PIL.Image.ANTIALIAS)
photo = ImageTk.PhotoImage(reim)
tmplabel = Label(master=frame, image=photo)
tmplabel.pack(fill=BOTH, expand=1)

# Cmd1 Gui - Request Most Recent Image
cmd1button = Button(mGui, text="Most Recent Photo", command= mostRecentImage)
cmd1button.place(x=150, y=65)

cmd1label = Label(text="Image Save Name : Default = image_XXXX_b" + extension,
                  font="Verdana 6 italic")
cmd1label.place(x=10, y=50)

imagename = Entry(mGui, textvariable=imagename)
imagename.place(x=10, y=70)

# Cmd2 Gui - Request text file on imagedata.txt
cmd2button = Button(mGui, text="Request 'imagedata.txt'", command=imageData)
cmd2button.place(x=150, y=115)

datafilename = Entry(mGui, textvariable=datafilename)
datafilename.place(x=10, y=120)

cmd2label = Label(text="Data File Save Name: Default = imagedata.txt", font="Verdana 6 italic")
cmd2label.place(x=10, y=100)

# Cmd3 Gui - Request specific image
subGui = Tk()
subGui.iconbitmap(default="bc.ico")
listbox = Listbox(subGui, selectmode=BROWSE, font="Vernada 10")
subGuibutton = Button(subGui, text="Request Selected Image", command=requestedImage)
direction = Label(master=subGui, text="Click on the image you would like to request",
                  font="Vernada 12 bold")
subGui.geometry("620x400+20+20")
subGui.title("Image Data and Selection")
direction.pack()
scrollbar = Scrollbar(subGui)
scrollbar.pack(side=RIGHT, fill=Y)
listbox.pack(side=TOP, fill=BOTH, expand=1)
subGuibutton.pack()
listbox.config(yscrollcommand=scrollbar.set)
scrollbar.config(command=listbox.yview)


def subGuiconfirm():
    if messagebox.askokcancel("W A R N I N G", message="You cannot reopen this window.\n Are you sure you "
                                                       "want to close it?", icon="warning"):
        subGui.destroy()
subGui.protocol('WM_DELETE_WINDOW', subGuiconfirm)

# Cmd4 and Cmd 5 Gui - Camera Settings
camedge = Frame(mGui, height=330, width=250, background="black", borderwidth=3)
camedge.place(x=1000, y=50)
camframe = Frame(camedge, height=50, width=40)
camframe.pack(fill=BOTH, expand=1)

cambot = Frame(camframe, borderwidth=1)
cambot.pack(side=BOTTOM, fill=X, expand=1)
camleft = Frame(camframe)
camleft.pack(side=LEFT, fill=BOTH, expand=2)
camright = Frame(camframe)
camright.pack(side=RIGHT, fill=BOTH, expand=2)

widthslide = Scale(camleft, from_=1, to=2592, orient=HORIZONTAL)
widthslide.set(width)
widthslide.pack()

widlabel = Label(master=camright, textvariable=widthvar, font="Verdana 8")
widlabel.pack(pady=19)

heightslide = Scale(camleft, from_=1, to=1944, orient=HORIZONTAL)
heightslide.set(height)
heightslide.pack()
heilabel = Label(master=camright, textvariable=heightvar, font="Verdana 8")
heilabel.pack(pady=5)

sharpnessslide = Scale(camleft, from_=-100, to=100, orient=HORIZONTAL)
sharpnessslide.set(sharpness)
sharpnessslide.pack()
shalabel = Label(master=camright, textvariable=sharpnessvar, font="Verdana 8")
shalabel.pack(pady=18)

brightnessslide = Scale(camleft, from_=0, to=100, orient=HORIZONTAL)
brightnessslide.set(brightness)
brightnessslide.pack()
brilabel = Label(master=camright, textvariable=brightnessvar, font="Verdana 8")
brilabel.pack(pady=5)

contrastslide = Scale(camleft, from_=-100, to=100, orient=HORIZONTAL)
contrastslide.set(contrast)
contrastslide.pack()
conlabel = Label(master=camright, textvariable=contrastvar, font="Verdana 8")
conlabel.pack(pady=18)

saturationslide = Scale(camleft, from_=-100, to=100, orient=HORIZONTAL)
saturationslide.set(saturation)
saturationslide.pack()
satlabel = Label(master=camright, textvariable=saturationvar, font="Verdana 8")
satlabel.pack(pady=5)

isoslide = Scale(camleft, from_=100, to=800, orient=HORIZONTAL)
isoslide.set(iso)
isoslide.pack()
isolabel = Label(master=camright, textvariable=isovar, font="Verdana 8")
isolabel.pack(pady=18)

angleslide = Scale(camleft, from_= 45, to=135, orient=HORIZONTAL)
angleslide.set(angle)
angleslide.pack()
anglelabel = Label(master=camright, textvariable=anglevar, font="Verdana 8")
anglelabel.pack(pady=5)

cmd4button = Button(cambot, text="Get Current Settings", command=retrieveCameraSettings,
                    borderwidth=2, background="white", font="Verdana 10")
cmd4button.grid(row=1, column=1)

cmd5button = Button(cambot, text="Send New Settings", command=uploadCameraSettings,
                    borderwidth=2, background="white", font="Verdana 10")
cmd5button.grid(row=1, column=0)

defaultbutton = Button(cambot, text="Default Settings", command=reset_cam, borderwidth=2,
                       background="white", font="Verdana 10", width=20)
defaultbutton.grid(row=0, columnspan=2, pady=5)

timelabel = Label(master=mGui, textvariable=timevar, font="Verdana 8")
timelabel.place(x=1020, y=27)

updateslider()

# Cmd 6 - Gui setup for connection testing
conbutton = Button(mGui, text="Connection Test", command=time_sync,
                   borderwidth=2, font="Verdana 10", width=25)
conbutton.place(x=25, y=490)

# Cmd 7 - Gui setup for raspberry GPS file retrieval
gpsbutton = Button(mGui, text="Download Pi GPS Data", command=getGPSfile,
                     borderwidth=2, font="Verdana 10", width=25)
gpsbutton.place(x=25, y=520)

# Command selection gui config
commands = Frame(mGui, height=80, width=290, background="light gray", borderwidth=3)
commands.place(x=1002, y=465)
select_label = Label(master=commands, font="Verdana 10 bold", text="Commands:")
select_label.grid(row=0, columnspan=2, padx=30)

# command buttons
angle_button = Button(master=commands, text="      Angle       ", bg="light gray",
                     command=set_camera_angle)
angle_button.grid(row=1, padx=30)

device_button = Button(master=commands, text="Device Status", bg="light gray",
                       command=device_status)
device_button.grid(row=2, padx=30)

reset_button = Button(master=commands, text=" Shutdown Pi ", bg="light gray",
                      command=shutdown_pi)
reset_button.grid(row=1, column=1, padx=30)

reboot_button = Button(master=commands, text="   Reboot Pi    ", bg="light gray",
                       command=reboot_pi)
reboot_button.grid(row=2, column=1, padx=30)

# Final Setup. Here we go

rframe = Frame(mGui, height=40, width=35)
runlistbox = Listbox(rframe, selectmode=BROWSE, font="Vernada 8", width=35, height=20)
runscrollbar = Scrollbar(rframe)
runlistbox.config(yscrollcommand=runscrollbar.set)
runscrollbar.config(command=runlistbox.yview)
runscrollbar.pack(side=RIGHT, fill=Y)
runlistbox.pack(side=LEFT, fill=Y)
rframe.place(x=10, y=165)


def callback():
    global runlistbox
    global mGui
    try:
        runlistbox.delete(0, END)
    except:
        print("Failed to delete Listbox")
    print(str(datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")))
    sys.stdout.flush()
    for line in reversed(list(open("runtimedata.txt"))):
        runlistbox.insert(END, line.rstrip())
    mGui.after(5000, callback)
    return


def mGuicloseall():
    subGui.destroy()
    mGui.destroy()
    ser.close()
    print("Program Terminated")
    sys.stdout.close()
    return

mGui.protocol('WM_DELETE_WINDOW', mGuicloseall)
mGui.after(1000, time_sync())
callback()
mGui.mainloop()
