import RPi.GPIO as GPIO
import time

HALL_SENSOR_PIN = 16 

GPIO.setmode(GPIO.BCM)
GPIO.setup(HALL_SENSOR_PIN, GPIO.IN)

def read_hall_sensor():
    # true = magnet is found
    return GPIO.input(HALL_SENSOR_PIN) == GPIO.LOW  


if __name__ == "__main__":
    try:
        while True:
            if read_hall_sensor():
                print("Magnet detected")
            else:
                print("No magnet")
            time.sleep(0.5)
    except KeyboardInterrupt:
        GPIO.cleanup()

