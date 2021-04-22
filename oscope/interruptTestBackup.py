import RPi.GPIO as GPIO
import piplates.DAQC2plate as DAQC2


GPIO.setmode(GPIO.BCM)

GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


DAQC2.startOSC(0)           #enable oscope
DAQC2.setOSCchannel(0,1,0)  #use channel 1

## Set up trigger:
##    Use channel 1
##    Normal trigger mode (don't collect data until trigger conditions are met)
##    Trigger on rising edge of waveform
##    Trigger at 0.0 volts
DAQC2.setOSCtrigger(0,1,'auto', 'rising', 2048)

## setup sample rate for 10,000 samples per second
DAQC2.setOSCsweep(0,6)
DAQC2.intEnable(0)          #enable interrupts
DAQC2.runOSC(0)             #start oscope


def oscope(channel):
	print("We in da oscope function")
	dataReady=0
	while(dataReady==0):
    		if(DAQC2.GPIO.input(22)==0):
        		dataReady=1
        		DAQC2.getINTflags(0) #clear interrupt flags

	DAQC2.getOSCtraces(0)

	### print out first 1000 converted values and not the conversion from A2D integer data to measured voltage
	for i in range(1000):
	    print((DAQC2.trace1[i]-2048)*12.0/2048)

	DAQC2.stopOSC(0)
	
# try:
#	GPIO.wait_for_edge(24, GPIO.RISING)
#	print("\n An edge was detected! ")
#	oscope(0)
#except KeyboardInterrupt:
#	GPIO.cleanup()


GPIO.add_event_detect(24, GPIO.RISING, callback=oscope(0))

while 1:
	x = 0
	if KeyboardInterrupt:
		GPIO.cleanup()

GPIO.cleanup()



   
