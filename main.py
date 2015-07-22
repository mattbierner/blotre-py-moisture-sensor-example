#!/usr/bin/env python
import time
import logging
import logging.handlers
import os
import RPi.GPIO as GPIO
import blotre
import spectra

LOG_FILENAME = "/tmp/blotre-moisutre.log"
LOG_LEVEL = logging.INFO  # Could be e.g. "DEBUG" or "WARNING"

SPICLK = 18
SPIMISO = 23
SPIMOSI = 24
SPICS = 25

# Range of sensor reading, from just watered to dry soil
MOISTURE_SENSOR_MAX = 825
MOISTURE_SENSOR_MIN = 400

MOISTURE_SCALE = spectra.scale(["#654d00", "green"]).domain([MOISTURE_SENSOR_MIN, MOISTURE_SENSOR_MAX])

# How often should the sensor be checked? (in seconds)
INTERVAL = 60 * 5


GPIO.setmode(GPIO.BCM)

# read SPI data from MCP3008 chip, 8 possible adc's (0 thru 7)                                                                                                 
def readadc(adcnum, clockpin, mosipin, misopin, cspin):
    if (adcnum > 7) or (adcnum < 0):
        return -1
    GPIO.output(cspin, True)

    GPIO.output(clockpin, False)  # start clock low                                                                                                        
    GPIO.output(cspin, False)     # bring CS low                                                                                                           

    commandout = adcnum
    commandout |= 0x18  # start bit + single-ended bit                                                                                                     
    commandout <<= 3    # we only need to send 5 bits here                                                                                                 
    for i in range(5):
        if commandout & 0x80:
            GPIO.output(mosipin, True)
        else:
            GPIO.output(mosipin, False)
        commandout <<= 1
        GPIO.output(clockpin, True)
        GPIO.output(clockpin, False)

    adcout = 0
    # read in one empty bit, one null bit and 10 ADC bits                                                                                                  
    for i in range(12):
        GPIO.output(clockpin, True)
        GPIO.output(clockpin, False)
        adcout <<= 1
        if GPIO.input(misopin):
            adcout |= 0x1

    GPIO.output(cspin, True)

    adcout >>= 1       # first bit is 'null' so drop it                                                                                                    
    return adcout

def get_root_stream(client):
    return client.get_stream(client.creds['user']['rootStream'])

def update_plant_status(client, rootStream, status):
    return client.create_stream({
        'name': "Mr Tree",
        'uri': rootStream['uri'] + '/mr+tree',
        'status': {
            'color': status
        }
    })


def clamp(minVal, maxVal, val):
    return min(maxVal, max(minVal, val))



# set up the SPI interface pins                                                                                                                               
GPIO.setup(SPIMOSI, GPIO.OUT)
GPIO.setup(SPIMISO, GPIO.IN)
GPIO.setup(SPICLK, GPIO.OUT)
GPIO.setup(SPICS, GPIO.OUT)

# 10k trim pot connected to adc #0                                                                                                                            
potentiometer_adc = 0

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when="midnight", backupCount=3)
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Create the client app
os.chdir(os.path.dirname(os.path.realpath(__file__)))

client = blotre.create_disposable_app({
    'name': "Plant're",
    'blurb': "Blot're you a plant."
})
rootStream = get_root_stream(client)

# Start polling
last_read = 9999                                                                        
tolerance = 15

while True:
    sample = readadc(potentiometer_adc, SPICLK, SPIMOSI, SPIMISO, SPICS)
    print sample
    logger.info("Sample %s" % sample)
    if abs(last_read - sample) > tolerance:
        update_plant_status(client, rootStream,
            MOISTURE_SCALE(clamp(MOISTURE_SENSOR_MIN, MOISTURE_SENSOR_MAX, sample)).hexcode)
        last_read = sample
    time.sleep(INTERVAL)



