#####################################################################################
#   PC interface for RFD900_Pi_V8 over the RFD900 Modem using a baudrate of 57600   #
#   to send photos and real time data. Constructed for MSGC Borealis program.       #
#   Author: Austin Langford, AEM, MnSGC created in March 2016                       #
#                                                                                   #
#   Editor: Dalton Lund, SDSGC         Amended: 6/16/2020                           #
#   Python Version: 3.7.6              Windows Version: 10.18363.778                #
#                                                                                   #
#####################################################################################

import time
import threading
import queue
from time import strftime
import datetime
import io
import picamera
import subprocess
import serial
import sys
import os
import PIL.Image
import base64
import hashlib
import pigpio
import serial.tools.list_ports
from io import StringIO
from array import array


class GPSThread(threading.Thread):
    # A thread to read in raw GPS information, and organize it for the main thread

    def __init__(self, threadID, gps, Q, exceptions, resetFlag, loggingGPS):  # Constructor
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.gpsSer = gps
        self.gpsQ = Q
        self.exceptionsQ = exceptions
        self.resetFlagQ = resetFlag
        self.loggingGPS = loggingGPS
        os.system('sudo modprobe w1-gpio')
        os.system('sudo modprobe w1-therm')
        self.rfdPort = serial.Serial(port="/dev/ttyAMA0", baudrate=57600, timeout=6)

        try:
            self.gpsPort = serial.Serial(port='/dev/ttyUSB0', baudrate=9600, timeout=3)
            print("GPS Found")
        except:
            self.gpsEnabled = False
            print("Unable to find GPS")

    def run(self):
        global folder
        try:
            while True:  # Run forever
                line = self.gpsSer.readline()
                line = line.decode('utf-8')
                if (line.find("$GNGGA") != -1):  # GPGGA indicates it's the GPS stuff we're looking for
                    try:
                        ### Parse the GPS Info ###
                        line = line.split(',')
                        if (line[1] == ''):
                            hours = 0
                            minutes = 0
                            seconds = 0
                        else:
                            hours = int(line[1][0:2])
                            minutes = int(line[1][2:4])
                            seconds = int(line[1][4:].split('.')[0])
                        if (line[2] == ''):
                            lat = 0
                        else:
                            lat = float(line[2][0:2]) + \
                                  (float(line[2][2:])) / 60
                        if (line[4] == ''):
                            lon = 0
                        else:
                            lon = -(float(line[4][0:3]) +
                                    (float(line[4][3:])) / 60)
                        if (line[9] == ''):
                            alt = 0
                        else:
                            alt = float(line[9])
                        sat = int(line[7])

                        lat = ("%.6f" % lat) #Set 6 decimals of accuracy for constistency in the gpslog.txt file
                        lon = ("%.6f" % lon) #Set 6 decimals of accuracy for constistency in the gps.log.txt file
                        ### Organize the GPS info, and put it in the queue ###
                        gpsStr = str(hours) + ',' + str(minutes) + ',' + str(seconds) + ',' + str(
                            lat) + ',' + str(lon) + ',' + str(alt) + ',' + str(sat) + '\n'
                        self.gpsQ.put(gpsStr)

                        if self.loggingGPS:
                            try:
                                f = open(folder + "gpslog.txt", "a")
                                f.write(gpsStr)
                                f.close()
                            except Exception as e:
                                print("Error logging GPS")
                                self.exceptionsQ.put(str(e))

                    except Exception as e:
                        self.exceptionsQ.put(str(e))

        ### Catches unexpected errors ###
        except Exception as e:
            self.exceptionsQ.put(str(e))
            self.resetFlagQ.put('gpsThread dead')


class TakePicture(threading.Thread):
    # Thread to take two pictures, one at full resolution, the other at the selected resolution

    def __init__(self, threadID, cameraSettings, folder, imagenumber, picQ):  # Constructor
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.cameraSettings = cameraSettings
        self.folder = folder
        self.imagenumber = imagenumber
        self.q = picQ

    def run(self):

        ### Open the camera ###
        try:
            camera = picamera.PiCamera()
        except:
            # If the camera fails to open, make sure the loop gets notified
            self.q.put('No Cam')
            return

        try:
            settings = self.cameraSettings.getSettings()
            width = settings[0]
            height = settings[1]
            sharpness = settings[2]
            brightness = settings[3]
            contrast = settings[4]
            saturation = settings[5]
            iso = settings[6]
            # Setup the camera with the settings read previously
            camera.sharpness = sharpness
            camera.brightness = brightness
            camera.contrast = contrast
            camera.saturation = saturation
            camera.iso = iso
            camera.image_effect = 'denoise'
            # Default max resolution photo
            camera.resolution = (2592, 1944)
            extension = '.png'
            camera.hflip = self.cameraSettings.getHFlip()
            camera.vflip = self.cameraSettings.getVFlip()
            # time.sleep(2)
            # Take the higher resolution picture
            time.sleep(1.5)
            camera.capture(self.folder + "%s%04d%s" %
                           ("image", self.imagenumber, "_a" + extension))
            print("(2592,1944) photo saved")
            # Save the pictures to imagedata.txt
            fh = open(self.folder + "imagedata.txt", "a+")
            fh.write("%s%04d%s @ time(%s) settings(w=%d,h=%d,sh=%d,b=%d,c=%d,sa=%d,i=%d)\n" % ("image",
                                                                                               self.imagenumber,
                                                                                               "_a" + extension, str(
                datetime.datetime.now().strftime
                ("%m/%d/%Y %H:%M:%S")), 2592, 1944, sharpness, brightness, contrast, saturation, iso))
            # Switch the resolution to the one set by the ground station
            camera.resolution = (width, height)
            extension = '.jpg'
            # Take the lower resolution picture
            time.sleep(1.5)
            camera.capture(self.folder + "%s%04d%s" % ("image", self.imagenumber, "_b" + extension))
            print('(', width, ',', height, ') photo saved')
            # Save the pictures to imagedata.txt
            fh.write("%s%04d%s, @ time(%s) settings(w=%d,h=%d,sh=%d,b=%d,c=%d,sa=%d,i=%d)\n" % ("image",
                                                                                                self.imagenumber,
                                                                                                "_b" + extension, str(
                datetime.datetime.now().strftime
                ("%m/%d/%Y %H:%M:%S")), width, height, sharpness, brightness, contrast, saturation, iso))
            print("Log file updated")
            self.q.put('done')

        # If there's any errors while taking the picture, reset the checkpoint
        except Exception as e:
            print(str(e))
            self.q.put('checkpoint')

        finally:
            try:
                camera.close()
                fh.close()
            except:
                pass


class Unbuffered:
    # Helps eliminate the serial buffer, also logs all print statements to the logfile

    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.stream.flush()
        logfile.write(data)
        logfile.flush()

    def flush(self):
        pass


class CameraSettings:
    # A class to handle camera settings

    def __init__(self, width, height, sharpness, brightness, contrast, saturation, iso):
        self.width = width
        self.height = height
        self.resolution = (width, height)
        self.sharpness = sharpness
        self.brightness = brightness
        self.contrast = contrast
        self.saturation = saturation
        self.iso = iso
        self.hflip = True
        self.vflip = True

    def getSettings(self):
        return [self.width, self.height, self.sharpness, self.brightness, self.contrast, self.saturation, self.iso]

    def getSettingsString(self):
        return str(self.width) + ',' + str(self.height) + ',' + str(self.sharpness) + ',' + str(
            self.brightness) + ',' + str(self.contrast) + ',' + str(self.saturation) + ',' + str(self.iso)

    def setCameraAnnotation(self, annotation):
        self.annotation = annotation

    def getCameraAnnotation(self):
        return self.annotation

    def getHFlip(self):
        return self.hflip

    def getVFlip(self):
        return self.vflip

    def toggleHorizontalFlip(self):
        if (self.hflip == False):
            self.hflip = True
        else:
            self.hflip = False
        return self.hflip

    def toggleVerticalFlip(self):
        if (self.vflip == False):
            self.vflip = True
        else:
            self.vflip = False
        return self.vflip

    def newSettings(self, settings):
        self.width = int(settings[0])
        self.height = int(settings[1])
        self.sharpness = int(settings[2])
        self.brightness = int(settings[3])
        self.contrast = int(settings[4])
        self.saturation = int(settings[5])
        self.iso = int(settings[6])
        self.resolution = (self.width, self.height)


class main:
    # The main program class
    def __init__(self):
        global folder, loggingGPS
        self.folder = folder

        # Get a list of the usb devices connected and assign them properly
        ports = serial.tools.list_ports.comports()
        serialConverters = []
        for each in ports:
            print(each.vid, each.pid, each.hwid, each.device)
            if each.vid == 1659 and each.pid == 8963:
                serialConverters.append(each)

        # The USB-serial converters don't have unique IDs, so they need to be checked
        for each in serialConverters:
            gpsTest = serial.Serial(port=each.device, baudrate=9600, timeout=3)
            try:
                sample = gpsTest.readline()
                sample = gpsTest.readline()  # Get 2 lines to make sure it's a full line
                sample = sample.decode('utf-8')
                if sample[0:2] == "$G":
                    self.gpsPort = self.gpsPort
                    print('GPS on ' + str(each.device))
                else:
                    self.rfdPort = self.rfdPort
                    print('RFD on ' + str(each.device))
            except Exception as e:
                print(str(e))

        ### Serial Port Initializations ###
        # RFD900 Serial Variables
        self.rfdBaud = 57600  # Make sure this matches the RFDs and port settings. You can check using SiLK and device manager
        self.rfdTimeout = 5

        # GPS Serial Variables
        self.gpsBaud = 9600
        self.gpsTimeout = 3

        # Create the imagedata.txt file
        fh = open(self.folder + "imagedata.txt", "w")
        fh.write("")
        fh.close()

        # Create the piruntimedata.txt file
        logfile = open(self.folder + "piruntimedata.txt", "w")
        logfile.close()
        logfile = open(self.folder + "piruntimedata.txt", "a")

        ### Picture Variables ###
        self.wordlength = 10000
        self.imagenumber = 0
        self.recentimg = ""
        self.pic_interval = 60
        self.cameraSettings = CameraSettings(650, 450, 0, 50, 0, 0, 400)
        self.reset_cam()
        self.takingPicture = False

        # Create the camerasettings.txt file and writes default settings to it
        pic = open(self.folder + "camerasettings.txt", "w")
        x = 0
        temp = CameraSettings(650, 450, 0, 50, 0, 0, 400)
        settings = temp.getSettings()
        while (x < 7):
            pic.write(str(settings[x]) + '\n')
            x += 1
        pic.close()

        # Make sure servo is set to neutral at 90 degrees upon startup.
        # 90 == 1700, 45 == 1500, and 135 == 1900
        self.pi = pigpio.pi()
        self.pi.set_mode(18,pigpio.OUTPUT)
        self.pi.set_servo_pulsewidth(18,1700)
        time.sleep(0.5)
        self.pi.set_servo_pulsewidth(18,0)

        # Create queues to share info with the threads
        self.gpsQ = queue.LifoQueue()
        self.gpsExceptionsQ = queue.Queue()
        self.gpsResetQ = queue.Queue()
        self.picQ = queue.Queue()

        ### Try to create the various serial objects; if they fail to be created, set them as disabled ###
        # RFD 900
        try:
            self.ser = rfdPort = serial.Serial(
                port="/dev/ttyAMA0", baudrate=57600, timeout=5)
            self.rfdEnabled = True
        except:
            self.rfdEnabled = False
            print('RFD disabled')

        # Camera
        try:
            camera = picamera.PiCamera()
            camera.close()
            self.cameraEnabled = True
        except:
            self.cameraEnabled = False
            if(self.rfdEnabled):
               self.ser.write(b'Alert: Camera is disabled\n')
            print('Camera disabled')

        # GPS
        try:
            self.gps = gpsPort = serial.Serial(
                port='/dev/ttyUSB0', baudrate=9600, timeout=3)
            self.gpsEnabled = True
        except:
            self.gpsEnabled = False
            if(self.rfdEnabled):
                self.ser.write(b'Alert: GPS is disabled\n')
            print('GPS disabled')

        ### Start the appropriate side threads ###
        # GPS
        if (self.gpsEnabled):
            self.startGPSThread()

        # Get Started
        self.starttime = time.time()
        print("Started at @ ", datetime.datetime.now())
        self.checkpoint = time.time()

    def getGPSCom(self):
        return [self.gpsPort, self.gpsBaud, self.gpsTimeout]

    def getRFDCom(self):
        return [self.rfdPort, self.rfdBaud, self.rfdTimeout]

    def reset_cam(self):
        # Resets the camera to the default settings
        self.cameraSettings = CameraSettings(650, 450, 0, 50, 0, 0, 400)

    def image_to_b64(self, path):
        # Converts an image to 64 bit encoding
        with open(path, "rb") as imageFile:
            return base64.b64encode(imageFile.read())

    def b64_to_image(self, data, savepath):
        # Converts a 64 bit encoding to an image
        fl = open(savepath, "wb")
        fl.write(data.decode('base64'))
        fl.close()

    def gen_checksum(self, data, pos):
        # Creates a checksum based on data
        return hashlib.md5(data[pos:pos + self.wordlength]).hexdigest()

    def sendword(self, data, pos):
        # Sends the appropriately sized piece of the total picture encoding
        if (pos + self.wordlength < len(data)):  # Take a piece of size self.wordlength from the whole, and send it
            self.ser.write(data[pos:pos + self.wordlength])
            print(data[pos:pos + self.wordlength])
            return
        else:  # If the self.wordlength is greater than the amount remaining, send everything left
            self.ser.write(data[pos:pos + len(data)])
            print(data[pos:pos + len(data)])
            return

    def sync(self):
        # Synchronizes the data stream between the Pi and the ground station
        synccheck = b''
        synctry = 5
        syncterm = time.time() + 10
        while ((synccheck != b'S') & (syncterm > time.time())):
            self.ser.write(b"sync")
            synccheck = self.ser.read()
            if (synctry == 0):
                if (synccheck == b''):
                    print("SyncError")
                    break
            synctry -= 1
        time.sleep(0.5)

        # Flush buffers to be ready
        self.ser.flushInput()
        self.ser.flushOutput()
        return

    def send_image(self, exportpath):
        # Sends the image through the RFD in increments of size self.wordlength
        print("Send Image Function")
        timecheck = time.time()
        done = False
        cur = 0
        trycnt = 0
        # Determine where the encoded image is
        outbound = self.image_to_b64(exportpath)
        size = len(outbound)
        print(size, ": Image Size")
        print("photo request received")
        # Send the total size so the ground station knows how big it will be
        self.ser.write(str(size).encode('utf-8'))
        print(str(size) + '\n')
        # successcount = 0
        while (cur < len(outbound)):
            # Print out how much picture is remaining in kilobytes
            print("Send Position:", cur, " // Remaining:", int((size - cur) / 1024), "kB")
            # Create the checksum to send for the ground station to compare to
            checkours = self.gen_checksum(outbound, cur)
            self.ser.write(checkours.encode('utf-8'))
            # Send a piece of size self.wordlength
            self.sendword(outbound, cur)
            time.sleep(0.1)
            checkOK = self.ser.read()
            # print('checkOK: ', checkOK)
            # This is based on whether or not the word was successfully received based on the checksums
            if (checkOK == b'Y'):
                cur = cur + self.wordlength
                trycnt = 0
                self.wordlength = 10000
            else:
                # There are 10 tries to get the word through, each time you fail, drop the self.wordlength by 1000
                if (trycnt < 10):
                    if (self.wordlength >= 1000):
                        self.wordlength -= 1000
                        self.sync()
                        trycnt += 1
                        print("try number:", trycnt)
                        print("resending last @", cur)
                        print("self.wordlength", self.wordlength)
                else:
                    print("error out")
                    cur = len(outbound)
        print("Image Send Complete")
        print("Send Time =", (time.time() - timecheck))
        return

    def mostRecentImage(self):
        # Command 1: Send most recent image
        self.ser.write(b'A')  # Send the acknowledge
        try:
            print("Send Image Command Received")
            print("Sending:", self.recentimg)
            self.ser.write(self.recentimg.encode('utf-8'))
            self.send_image(self.folder + self.recentimg)
            # Reset the self.wordlength in case it was changed while sending
            self.wordlength = 10000  #######################################
        except Exception as e:
            print("Send Recent Image Error:", str(e))

    def sendImageData(self):
        # Command 2: Sends imagedata.txt
        self.ser.write(b'A')
        try:
            print("data list request recieved")
            file = open(self.folder + "imagedata.txt", "r")
            print("Sending imagedata.txt")
            for line in file:
                self.ser.write(line.encode('utf-8'))
            file.close()
            time.sleep(1)
        except:
            print("Error with imagedata.txt read or send")

    def requestedImage(self):
        # Command 3: Sends the requested image
        self.ser.write(b'A')
        try:
            print("Specific Photo Request Received")
            image_to_send = b''
            while (image_to_send == b''):
                image_to_send = self.ser.readline().decode('utf-8')
                print("Image to send:", image_to_send)
            print("Requested image: ", str(image_to_send))
            self.ser.reset_input_buffer()
            self.send_image(self.folder + str(image_to_send))
            self.wordlength = 10000
        except Exception as e:
            print("Error sending requestedImage")
            print(str(e))

    def sendCameraSettings(self):
        # Command 4: Sends the camera settings
        self.ser.write(b'A')
        try:
            print("Attempting to send camera settings")
            file = open(folder + "camerasettings.txt", "r")
            temp = file.read()
            while (temp != ""):
                self.ser.write(temp.encode('utf-8'))
                temp = file.read()
            file.close()
            print("Camera Settings Sent")
        except Exception as e:
            print(str(e))

    def getCameraSettings(self):
        # Command 5: Updates the camera settings
        self.ser.write(b'A')
        temp = b'Y'
        try:
            print("Attempting to update camera settings")
            self.ser.reset_input_buffer()
            file = open(folder + "camerasettings.txt", "w")
            while (temp != b''):
                temp = self.ser.readline()
                file.write(temp.decode('utf-8'))
            file.close()
            with open(folder + "camerasettings.txt", 'r') as filehandle:
                settings = [current_place.rstrip() for current_place in filehandle.readlines()]
            file.close()
            self.cameraSettings = CameraSettings(int(settings[0]), int(settings[1]), int(settings[2]), int(settings[3]),
                                                 int(settings[4]), int(settings[5]), int(settings[6]))
            print("New Camera Settings Received")
            self.ser.write(b'A')
            checkpoint = time.time()
        except Exception as e:
            print("Error Retrieving Camera Settings")
            print(str(e))
            self.reset_cam()

    def timeSync(self):
        # Command T: Takes the current time from the ground station and applies it to Pi
        self.ser.write(b'T')
        try:
            print("Time Sync Request Received")
            timeval = self.ser.readline(19)
            timeval = timeval.decode('utf-8')
            command = "sudo date -s " + "'" + timeval
            command = command + "'"
            os.system(command)
            self.ser.write(b'T')
            for x in timeval:
                self.ser.write(x.encode('utf-8'))
        except:
            print("error with time sync")

    def pingTest(self):
        # Command P: Connection test, test ping time
        self.ser.write(b'P')
        print("Ping Request Received")
        try:
            termtime = time.time() + 10
            pingread = self.ser.read()
            # Look for the stop character D, no new info, or too much time passing
            while ((pingread !=b'D') & (pingread != b"") & (termtime > time.time())):
                if (pingread == b'P'):  # Whenever you get the P, send one back and get ready for another
                    print("Ping Received")
                    self.ser.reset_input_buffer()
                    self.ser.write(b'P')
                else:  # If you don't get the P, send back an A instead
                    print("pingread = ", pingread)
                    self.ser.reset_input_buffer()
                    self.ser.write(b'A')
                pingread = self.ser.read()  # Read the next character
                sys.stdin.flush()
        except:
            print("Ping Runtime Error")

    def sendgpslog(self):
        # Command G: Sends the gpslog.txt
        self.ser.write(b'A')
        lines = 0
        try:
            print("Attempting to send gpslog.txt")
            # Open the gpslog file
            file = open(self.folder + "gpslog.txt", "r")
            for line in file:
               lines += 1
            file.close()
            file = open(self.folder + "gpslog.txt", "r")
            if (lines < 10):         # If we have less than less than 10 gps data log enteries
                temp = file.readline()
                while (temp != ""):  # Send everything in the file until it's empty
                    self.ser.write(temp.encode('utf-8'))
                    temp = file.readline()
            else:                    # Sends the 10 most recent gps data logs to the ground station
                count = lines - 10   # We do not want to send the whole file because it gets large fast
                line = file.readlines()
                while(count < lines):
                    temp = line[count]
                    self.ser.write(temp.encode('utf-8'))
                    count += 1
            file.close()
            print("gpslog.txt sent")
        except:
            print("error sending gpslog.txt")

    def horizontalFlip(self):
        # Flips the pictures horizontally (Not currently being used)
        self.ser.write(b'A')
        try:
            self.cameraSettings.toggleHorizontalFlip()
            print("Camera Flipped Horizontally")
        except:
            print("Error flipping image horizontally")

    def verticalFlip(self):
        # Flips the pictures vertically (Not currently being used)
        self.ser.write(b'A')
        try:
            self.cameraSettings.toggleVerticalFlip()
            print("Camera Flipped Vertically")
        except:
            print("Error flipping image vertically")

    def sendDeviceStatus(self):
        # Command D: Returns the status of the serial devices to the ground station
        self.ser.write(b'A')
        try:
            status = 'Camera: ' + \
                     str(self.cameraEnabled) + ', GPS: ' + str(self.gpsEnabled)
            self.ser.write(status.encode('utf-8'))
            print('Status Sent')
            print(self.cameraEnabled)
            print(self.gpsEnabled)
        except Exception as e:
            print(str(e))

    def startGPSThread(self):
        self.gpsThread = GPSThread(
            "gpsThread", self.gps, self.gpsQ, self.gpsExceptionsQ, self.gpsResetQ, loggingGPS)
        self.gpsThread.daemon = True
        self.gpsThread.start()

    def rebootPi(self):
        # Command R: Reboots the Pi if needed
        self.ser.write(b'A')
        try:
            os.system('sudo reboot now')
        except:
            print("Something went wrong and we cannot reboot")

    def shut_down(self):
        # Command Q: Shutdown the Pi once the payload is recovered before the batteries die to prevent SD Card Corruption
        self.ser.write(b'A')
        try:
            os.system('sudo shutdown now')
        except:
            print("Something went wrong and we cannot shutdown")

    def set_camera_angle(self):
        # Command H: Cahnge the angle of the PiCamera. Can go between 45 and 135 degree is 90 being neutral
        self.ser.write(b'A')
        print("Receoved Command to update camera servo angle")
        temp = b'Y'
        angle = ''
        while (temp != b''):
            temp = self.ser.read()
            angle = angle + temp.decode('utf-8')
        try:
            print("Setting to: ",self.pi.set_servo_pulsewidth(18, angle))
            print("Set to: ", self.pi.get_servo_pulsewidth(18))
            time.sleep(1)
            self.pi.set_servo_pulsewidth(18, 0)
            time.sleep(0.5)
        except Exception as e:
             print(str(e))
        self.ser.write(b'A')

    def checkSideThreads(self):
        # Check to make sure the side threads are still running

        # If the gps thread needs to be reset, do it
        if (self.gpsEnabled):
            if (not self.gpsResetQ.empty()):
                try:
                    self.gps.close()  # Try to close the gps
                except:
                    pass
                try:
                    self.gps = serial.Serial(
                        port=self.gpsPort, baudrate=self.gpsBaud, timeout=self.gpsTimeout)  # Reopen the GPS
                    self.startGPSThread()  # Restart the thread
                    # Clear the gps reset Q
                    while (not self.gpsResetQ.empty()):
                        self.gpsResetQ.get()
                except:
                    print("except")
                    self.gpsEnabled = False  # If this fails, disable the gps
                    if (self.rfdEnabled):
                        self.ser.write(b'Alert: GPS is disabled')
                    print("GPS is now Disabled")

    def loop(self):
        # The main loop for the program
        try:
            ### Receive a command from the ground station and process it ###
            if (self.rfdEnabled):
                # Print out how long this has been running
                print("RT: " + str(int(time.time() - self.starttime)) +
                      " Watching Serial")
                timeCheck = time.time()
                command = b''
                done = False
                while ((not done) and (time.time() - timeCheck) < 1):  # 3
                    # Read from the RFD, if you fail to read, disabled the RFD and break the loop
                    newChar =b''
                    try:
                        newChar = self.ser.read()
                        print("Incoming Char:", newChar)
                    except Exception as e:
                        print(str(e))
                        self.rfdEnabled = False
                        done = True
                    # If the Character is !, this is a command EOL character, so end the loop
                    if (newChar != b"!"):
                        command += newChar
                        done = True
                    # IF the character is anything else (not null(, add it on, and reset the kill timer
                    elif (newChar != b""):
                        command += newChar
                        timeCheck = time.time()

                if (command != ''):
                    print("Command: ", command)

                # Check to see if the command was one for the raspberry pi and run if it is
                try:
                    if (command == b'1'):
                        self.mostRecentImage()
                    elif (command == b'2'):
                        self.sendImageData()
                    elif (command == b'3'):
                        self.requestedImage()
                    elif (command == b'4'):
                        self.sendCameraSettings()
                    elif (command == b'5'):
                        self.getCameraSettings()
                    elif (command == b'P'):
                        self.pingTest()
                    elif (command == b'G'):
                        self.sendgpslog()
                    elif (command == b'T'):
                        self.timeSync()
                    #elif (command == b'9'):  # Not currently used by Ground Station
                    #    self.horizontalFlip()
                    #    self.ser.reset_input_buffer()
                    #elif (command == b'0'):  # Not currently used by Ground Station
                    #    self.verticalFlip()
                    #    self.ser.reset_input_buffer()
                    elif (command == b'P'):
                        self.sendPing()
                    elif (command == b'S'):
                        self.sync()
                    elif (command == b'D'):
                        self.sendDeviceStatus()
                    elif (command == b'H'):
                        self.set_camera_angle()
                    elif (command == b'R'):
                        command = self.ser.read()
                        if (command == b'R'):
                            self.rebootPi()
                        else:
                            pass
                    elif (command == b'Q'):
                        command == self.ser.read()
                        if (command == b'Q'):
                            self.shut_down()
                        else:
                            pass
                except:
                    self.rfdEnabled = False  # The only thing not exception handled in the command functions is the
                    # acknowledge send, so if this block is triggered, the RFD write failed

            # Make sure the side threads are still going strong
            self.checkSideThreads()

            ### Periodically take a picture ###
            if (self.cameraEnabled):
                if (self.checkpoint < time.time() and not self.takingPicture):  # Take a picture periodically
                    try:
                        camera = picamera.PiCamera()
                        camera.close()
                    except:
                        self.cameraEnabled = False
                        if (self.rfdEnabled):
                            self.ser.write(b'Alert: Camera is disabled\n')
                        print('Camera disabled')
                    if self.cameraEnabled:
                        print("Taking Picture")
                        self.takingPicture = True
                        self.picThread = TakePicture(
                            "Picture Thread", self.cameraSettings, self.folder, self.imagenumber, self.picQ)
                        self.picThread.daemon = True
                        self.picThread.start()

            ### Check for picture stuff ###
            if (self.cameraEnabled):
                if (not self.picQ.empty()):
                    # Command to reset the recentimg and increment the pic number (pic successfully taken)
                    if (self.picQ.get() == 'done'):
                        self.recentimg = "%s%04d%s" % (
                            "image", self.imagenumber, "_b.jpg")
                        self.imagenumber += 1
                        self.takingPicture = False
                        self.checkpoint = time.time() + self.pic_interval
                    # Command to reset the camera
                    elif (self.picQ.get() == 'reset'):
                        self.takingPicture = False
                        self.reset_cam()
                    # Command to reset the checkpoint
                    elif (self.picQ.get() == 'checkpoint'):
                        self.takingPicture = False
                        self.checkpoint = time.time() + self.pic_interval
                    # Command to disable the camera
                    elif (self.picQ.get() == 'No Cam'):
                        self.cameraEnabled = False
                    else:
                        # Clear the queue of any unexpected messages
                        while (not self.picQ.empty()):
                            print(self.picQ.get())

            if (self.rfdEnabled):
                # Clear the input buffer so we're ready for a new command to be received
                self.ser.reset_input_buffer()

            ### Print out any exceptions that the threads have experienced ###
            if (self.gpsEnabled):
                while (not self.gpsExceptionsQ.empty()):
                    print(self.gpsExceptionsQ.get())

            # Camera Check
            if (not self.cameraEnabled):
                try:
                    camera = picamera.PiCamera()
                    camera.close()
                    self.cameraEnabled = True
                    print('Camera is now Enabled')
                    if (self.rfdEnabled):
                        self.ser.write(b'Camera is now Enabled')
                except:
                    pass

            # RFD and GPS Check
            if (not self.gpsEnabled) or (not self.rfdEnabled):
                ports = serial.tools.list_ports.comports()
                for each in ports:
                    if each.vid == 1659 and each.pid == 8963:
                        if each.device != self.rfdPort:
                            gpsTest = serial.Serial(
                                port=each.device, baudrate=9600, timeout=1)
                            try:
                                sample = gpsTest.readline()
                                sample = gpsTest.readline()  # Get 2 lines to make sure it's a full line
                                sample = sample.decode('utf-8')
                                if sample[0:2] == "$G":
                                    self.gpsPort = each.device
                                    self.gps = serial.Serial(
                                        port=self.gpsPort, baudrate=self.gpsBaud, timeout=self.gpsTimeout)
                                    self.gpsEnabled = True
                                    # This will cause the thread to be restarted in the the checkSideThreads call next loop
                                    self.gpsResetQ.put('reset')
                                    # Close the GPS so it can be opened again later
                                    self.gps.close()
                                    print('GPS is now Enabled')
                                    if (self.rfdEnabled):
                                        self.ser.write(b'GPS is now Enabled')
                                else:
                                    if (not self.rfdEnabled):
                                        self.rfdPort = each.device
                                        print('RFD is now Enabled')
                            except Exception as e:
                                print(str(e))

        except KeyboardInterrupt:  # For debugging pruposes, close the RFD port and quit if you get a keyboard interrupt
            self.ser.close()
            quit()

        except Exception as e:  # Print any exceptions from the main loop
            print(str(e))


if __name__ == "__main__":
    ### Check for, and create the folder for this flight ###
    folder = "/home/pi/RFD_Pics_Logs/%s/" % strftime("%m%d%Y_%H%M%S")
    dir = os.path.dirname(folder)
    if (not os.path.exists(dir)):
        os.mkdir(dir)

    ### Create the logfile ###
    try:
        logfile = open(folder + "piruntimedata.txt", "w")
        logfile.close()
        logfile = open(folder + "piruntimedata.txt", "a")
        loggingRuntime = True
    except:
        loggingRuntime = False
        print("Failed to create piruntimedata.txt")

    # All print statements are written to the logfile
    sys.stdout = Unbuffered(sys.stdout)

    try:
        gpsLog = open(folder + "gpslog.txt", "a")
        gpsLog.close()
        loggingGPS = True
    except:
        loggingGPS = False
        print("Failed to create gpslog.txt")

    mainLoop = main()
    while True:
        mainLoop.loop()
