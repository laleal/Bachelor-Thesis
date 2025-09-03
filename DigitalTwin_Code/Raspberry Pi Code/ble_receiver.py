import json
import asyncio
import threading
from bleak import BleakScanner, BleakClient

device_1_temperature = None
device_1_humidity    = None
device_1_light       = None
device_1_motion      = None
device_1_co2         = None
device_1_timestamp   = None

device_2_temperature = None
device_2_humidity    = None
device_2_light       = None
device_2_motion      = None
device_2_co2         = None
device_2_timestamp   = None

SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
BLE_DEVICE_NAME_1 = "ESP32_BLE_Server_1"
BLE_DEVICE_NAME_2 = "ESP32_BLE_Server_2"
TIMEOUT = 15.0  # seconds

_clients = {}

def _notification_handler(device_name):
    def handler(sender, data):
        global device_1_temperature, device_1_humidity, device_1_light, device_1_motion, device_1_co2, device_1_timestamp
        global device_2_temperature, device_2_humidity, device_2_light, device_2_motion, device_2_co2, device_2_timestamp
        try:
            # parse json from ESP32
            payload = json.loads(data.decode())
            if device_name == BLE_DEVICE_NAME_1 and "temp_1" in payload:
                device_1_temperature = payload.get("temp_1")
                device_1_humidity    = payload.get("hum_1")
                device_1_light       = payload.get("light_1")
                device_1_motion      = payload.get("motion_1")
                device_1_co2         = payload.get("co2_1")
                device_1_timestamp   = payload.get("time_1")
                print("[BLE Receiver] Updated data for Device_1")
            elif device_name == BLE_DEVICE_NAME_2 and "temp_2" in payload:
                device_2_temperature = payload.get("temp_2")
                device_2_humidity    = payload.get("hum_2")
                device_2_light       = payload.get("light_2")
                device_2_motion      = payload.get("motion_2")
                device_2_co2         = payload.get("co2_2")
                device_2_timestamp   = payload.get("time_2")
                print("[BLE Receiver] Updated data for Device_2")
        except Exception as e:
            print(f"[BLE Receiver] Notification handling error for {device_name}: {e}")
    return handler

async def _ble_loop():
    global _clients
    # CONNECTING TO DEVICE 1 ------------------------------------------------
    print(f"[BLE Receiver] Scanning for '{BLE_DEVICE_NAME_1}'...")
    device1 = await BleakScanner.find_device_by_name(BLE_DEVICE_NAME_1, timeout=20.0)
    if device1 is None:
        print("[BLE Receiver] Device_1 not found!")
    else:
        client1 = BleakClient(device1)
        try:
            await client1.connect(timeout=TIMEOUT)
            await client1.start_notify(CHARACTERISTIC_UUID, _notification_handler(BLE_DEVICE_NAME_1))
            _clients[BLE_DEVICE_NAME_1] = client1
            print(f"[BLE Receiver] Connected to Device_1 at {device1.address}")
        except Exception as e:
            print(f"[BLE Receiver] Error connecting to Device_1: {e}")

    # CONNECTING TO DEVICE 2 ------------------------------------------------
    print(f"[BLE Receiver] Scanning for '{BLE_DEVICE_NAME_2}'...")
    device2 = await BleakScanner.find_device_by_name(BLE_DEVICE_NAME_2, timeout=20.0)
    if device2 is None:
        print("[BLE Receiver] Device_2 not found!")
    else:
        client2 = BleakClient(device2)
        try:
            await client2.connect(timeout=TIMEOUT)
            await client2.start_notify(CHARACTERISTIC_UUID, _notification_handler(BLE_DEVICE_NAME_2))
            _clients[BLE_DEVICE_NAME_2] = client2
            print(f"[BLE Receiver] Connected to Device_2 at {device2.address}")
        except Exception as e:
            print(f"[BLE Receiver] Error connecting to Device_2: {e}")

    while True:
        await asyncio.sleep(1)

_ble_thread = None

def init_ble():
    global _ble_thread
    print("BLE initializing...")
    _ble_thread = threading.Thread(target=run_ble, daemon=True)
    _ble_thread.start()

def run_ble():
    asyncio.run(_ble_loop())

def stop_ble():
    global _clients
    print("BLE stopping...")
    for client in _clients.values():
        try:
            if client.is_connected:
                asyncio.run(client.disconnect())
                print("Disconnected a client")
        except Exception as e:
            print(f"Error disconnecting client: {e}")