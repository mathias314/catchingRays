// todo: see if code works with an uno instead of mega
// todo: see if file name/type can change from test.txt

#include <Wire.h>
#include <MS5xxx.h>
#include <SPI.h>
#include <SD.h>

MS5xxx altimeter(&Wire);

#include <SparkFun_I2C_GPS_Arduino_Library.h> //Use Library Manager or download here: https://github.com/sparkfun/SparkFun_I2C_GPS_Arduino_Library
I2CGPS myI2CGPS; //Hook object to the library
#include <TinyGPS++.h> //From: https://github.com/mikalhart/TinyGPSPlus
TinyGPSPlus gps; //Declare gps object

File dataFile;

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  while (!Serial) {
    ; // wait for serial port to connect. Needed for native USB port only
  }

  if (myI2CGPS.begin() == false)
  {
    Serial.println("Module failed to respond. Please check wiring.");
    while (1); //Freeze!
  }
  Serial.println("GPS module found!");

  if(altimeter.connect()>0) {
    Serial.println("Error connecting...");
    delay(500);
    setup();
  }
  Serial.println("connected to altimeter");


  Serial.print("Initializing SD card...");

  if (!SD.begin(4)) {
    Serial.println("initialization failed!");
    while (1);
  }

    
  Serial.println("SD card initialization done.");

}


void loop() {
  // put your main code here, to run repeatedly:

  dataFile = SD.open("test.txt", FILE_WRITE);
  
  altimeter.ReadProm();
  altimeter.Readout();
  
  if(dataFile && myI2CGPS.available())
  {
    gps.encode(myI2CGPS.read()); //Feed the GPS parser

    Serial.print("Temperature C: ");
    Serial.println(altimeter.GetTemp() / 100);
    Serial.print("Pressure [Pa]: ");
    Serial.println(altimeter.GetPres());
  
    dataFile.print(altimeter.GetTemp() / 100);
    dataFile.print(',');
    dataFile.print(altimeter.GetPres());
    dataFile.print(',');
    dataFile.print(gps.date.month());
    dataFile.print(',');
    dataFile.print(gps.date.day());
    dataFile.print(',');
    dataFile.print(gps.date.year());
    dataFile.print(',');

    if (gps.time.hour() < 10) dataFile.print(F("0"));
    dataFile.print(gps.time.hour());
    dataFile.print(F(":"));
    if (gps.time.minute() < 10) dataFile.print(F("0"));
    dataFile.print(gps.time.minute());
    dataFile.print(F(":"));
    if (gps.time.second() < 10) dataFile.print(F("0"));
    dataFile.print(gps.time.second());

    dataFile.print(',');

    dataFile.print(gps.location.lat(), 6);
    dataFile.print(',');
    dataFile.print(gps.location.lng(), 6);
    dataFile.print(',');
    dataFile.print(gps.altitude.meters());
    dataFile.print(',');
    dataFile.print(gps.satellites.value());
    dataFile.print(',');

    dataFile.print('\n');
  }
  else
  {
    Serial.println("data file not open or no gps:(");
  }

   dataFile.close();

  delay(1000);
}
