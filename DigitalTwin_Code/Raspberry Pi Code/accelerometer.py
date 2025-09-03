import smbus
import time
import threading

GYRO_ZOUT_H = 0x47

bus = None
mpu_available = False

def init_mpu6050():
    global bus, mpu_available
    try:
        bus = smbus.SMBus(1)
        bus.write_byte_data(0x68, 0x6B, 0)
        bus.read_byte_data(0x68, 0x75)
        mpu_available = True
        print("MPU6050 initialized successfully")
        return True
    except Exception as e:
        print(f"Failed to initialize MPU6050: {e}")
        mpu_available = False
        return False

sensor_data = {
    "gyro": 0.0,
    "angle": 0.0
}

gyro_z_offset = 0.0
angle = 0.0
last_time = time.time()
thread_running = False
sensor_thread = None

def read_word(reg):
      
    try:
        high = bus.read_byte_data(0x68, reg)
        low = bus.read_byte_data(0x68, reg + 1)
        value = (high << 8) | low
        if value >= 32768:
            value -= 65536
        return value
    except Exception as e:
        print(f"Error reading from MPU6050: {e}")
        return 0

def calibrate_gyro_z_offset(samples=1000):
    global gyro_z_offset
        
    print("Calibrating gyroscope Z-axis offset. Keep sensor still.")
    gyro_z_sum = 0.0
    for _ in range(samples):
        z_gyro = read_word(GYRO_ZOUT_H) / 131.0  # Convert raw to degrees
        gyro_z_sum += z_gyro
        time.sleep(0.000001) # LESS SLEEP MORE ACCURATE
    gyro_z_offset = gyro_z_sum / samples
    print(f"Gyro Z Offset: {gyro_z_offset}")

def update_sensor_data():
    global angle, last_time, sensor_data, gyro_z_offset, thread_running
    last_time = time.time()  # Reset the timer when thread starts
    
    while thread_running:
        # Gyro Z raw data converted to degrees - offset
        z_gyro = (read_word(GYRO_ZOUT_H) / 131.0) - gyro_z_offset

        # Calculate time difference for integration
        current_time = time.time()
        dt = current_time - last_time
        last_time = current_time

        angle += z_gyro * dt
        angle_mod = (angle + 10 % 360) -11.1  
        # Calibrated numbers. Depends on the initial possition and angle of the sensor.

        sensor_data["gyro"] = z_gyro
        sensor_data["angle"] = angle_mod

def start_sensor_thread():
    global thread_running, sensor_thread, angle, last_time
    
    if thread_running:
        print("Sensor thread already running")
        return
    
    # Initialize MPU6050
    if not init_mpu6050():
        print("MPU6050 not found")
    
    # Reset angle
    angle = 0.0
    last_time = time.time()
    
    calibrate_gyro_z_offset()
    thread_running = True
    sensor_thread = threading.Thread(target=update_sensor_data, daemon=True)
    sensor_thread.start()
    print("Sensor thread started")

def stop_sensor_thread():
    global thread_running
    thread_running = False
    print("Sensor thread stopped")

def reset_angle():
    global angle
    angle = 0.0
    print("Angle reset to zero")

def read_acc():
    if not thread_running:
        print("Warning: Sensor thread not running. Call start_sensor_thread() first.")
        return {"gyro": 0.0, "angle": 0.0}
    
    return sensor_data.copy()

if __name__ == "__main__":
    start_sensor_thread()
    try:
        while True:
            data = read_acc()
            print(f"Gyro: {data['gyro']:.2f}°/s, Angle: {data['angle']:.2f}° (MPU Available: {mpu_available})")
            time.sleep(0.1)  ## less for more accuracy
    except KeyboardInterrupt:
        print("Exiting...")
        stop_sensor_thread()