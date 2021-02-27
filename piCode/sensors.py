import sys
import datetime
import time


def getTime():
    return datetime.datetime.now()


def getPressure():
    # read pressure
    # calculate altitude
    # return pressure/altitude


def getTemp():
    # read temp
    # return temp


def getVoltage():
    # read somehow from piplate (from digital in probably)
    # return value


def getSensorReading():
    # basically same as voltage
    # read from digital
    # return signal (probably just 0)




def sendData():
    # collect all readings from sensors
    # do magic with rfd
    # send power to pins to send or something



def writeToFile():
    # collect all readings
    # write to csv file


def cutDown():
    # BEYBLADE TIME






# interrupts for request data, cutdown, sensor input
# timed read, toAltitude
# user power off, user power on

# structure everything as interrupt based sys
