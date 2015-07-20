import time
import os
import RPi.GPIO as GPIO
import blotre
import spectra

SPICLK = 18
SPIMISO = 23
SPIMOSI = 24
SPICS = 25

# Range of sensor reading, from just watered to dry soil
MOISTURE_SENSOR_MAX = 825
MOISTURE_SENSOR_MIN = 0

MOISTURE_SCALE = spectra.scale(["brown", "green"])



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

def update_plant_status(client, status):
    return client.create_stream({
        'name': "Living Room Plant",
        'uri': rootStream.uri + '/living+room+plant',
        'status': {
            'color': status
        }
    })


# set up the SPI interface pins                                                                                                                                
GPIO.setup(SPIMOSI, GPIO.OUT)
GPIO.setup(SPIMISO, GPIO.IN)
GPIO.setup(SPICLK, GPIO.OUT)
GPIO.setup(SPICS, GPIO.OUT)

# 10k trim pot connected to adc #0                                                                                                                             
potentiometer_adc = 0



client = blotre.create_disposable_app({
    'name': "Plant're",
    'blurb': "Blot're you a plant."
})

last_read = 0                                                                                     
tolerance = 5

while True:
    sample = readadc(potentiometer_adc, SPICLK, SPIMOSI, SPIMISO, SPICS)
    print sample
    
    
    if abs(last_read - sample) > tolerance:
        percent = float(min(reading, MOISTURE_SENSOR_MAX) / max(reading, MOISTURE_SENSOR_MIN)) / MOISTURE_SENSOR_MAX
        print percent
        update_plant_status(MOISTURE_SCALE(percent))
    last_read = sample
    time.sleep(1)



