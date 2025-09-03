import time
import ble_receiver
from accelerometer import read_acc, start_sensor_thread, stop_sensor_thread, reset_angle
from magnetic_hall import read_hall_sensor
from data_sender import DataSender

def main():
    # start BLE 
    ble_receiver.init_ble()
    print("Waiting for BLE devices to connect.")
    time.sleep(30)

    # start Accelorometer
    print("Starting accelerometer sensor.")
    start_sensor_thread()
    
    time.sleep(2)
    reset_angle()

    # azure
    connection_string = (
        "HostName=DigitalTwinLea.azure-devices.net;"
        "DeviceId=RaspberryPi;"
        "SharedAccessKey=********************"
    )
    sender = DataSender(connection_string)

    try:
        while True:
            ########################### local sensors #########################################
            sensor_data = read_acc()
            if sensor_data:
                angle = sensor_data["angle"]
                gyro  = sensor_data["gyro"]
                print(f"  Angle: {angle:.2f}°, Gyro: {gyro:.2f}°/s")
            else:
                angle = gyro = None

            hall_val = read_hall_sensor()
            magnet = bool(hall_val)
            print(f" Hall Sensor: {'Detected' if magnet else 'None'}")

            ########################### BLE received data #########################################
            remote_data = {
                "device_1": {
                    "temperature": ble_receiver.device_1_temperature,
                    "humidity":    ble_receiver.device_1_humidity,
                    "light":       ble_receiver.device_1_light,
                    "motion":      ble_receiver.device_1_motion,
                    "co2":         ble_receiver.device_1_co2,
                    "timestamp":   ble_receiver.device_1_timestamp
                },
                "device_2": {
                    "temperature": ble_receiver.device_2_temperature,
                    "humidity":    ble_receiver.device_2_humidity,
                    "light":       ble_receiver.device_2_light,
                    "motion":      ble_receiver.device_2_motion,
                    "co2":         ble_receiver.device_2_co2,
                    "timestamp":   ble_receiver.device_2_timestamp
                }
            }
            print("Remote data:", remote_data)

            ########################### Timestamp and Payload #########################################
            ts = time.time()
            utc = time.gmtime(ts)
            ms  = int((ts - int(ts)) * 1000)
            door_timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", utc) + f".{ms:03d}Z"
            local_data = {"door_timestamp": door_timestamp,
                          "angle": angle,
                          "gyro": gyro,
                          "magnet": magnet}

            payload = {
                "local_data":  local_data,
                "remote_data": remote_data
            }

            print("Publishing to Azure.")
            print(payload)
            sender.send_data(payload)

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("Stopping program")
    finally:
        stop_sensor_thread()
        ble_receiver.stop_ble()
        sender.disconnect()

if __name__ == "__main__":
    main()