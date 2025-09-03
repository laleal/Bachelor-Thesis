import json
import logging
import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("Checking for anomalies")

    # get data
    door_info = event.get('doorInfo', {})
    angle = door_info.get('angle', 0)
    gyro = door_info.get('gyro', 0)
    magnet = door_info.get('magnet', False)
    rooms_info = event.get('roomsInfo', {})
    room1_co2 = rooms_info.get('Room1', {}).get('co2', 0)
    room2_co2 = rooms_info.get('Room2', {}).get('co2', 0)

    anomaly_updates = []
    detected_anomalies = []

    # door slam detection
    if abs(gyro) > 65:
        anomaly_updates.append({
            "entityId": "Door",
            "componentName": "DoorComponents",
            "property": "slammedAnomaly",
            "value": "slammed",
            "valueType": "stringValue"
        })
        
        detected_anomalies.append({
            'entity': 'Door',
            'type': 'door_slam',
            'details': {
                'gyro': gyro,
                'timestamp': datetime.datetime.utcnow().isoformat()
            }
        })
        
        logger.info(f"Door slammed detected: gyro={gyro}")

    # sensor conflict detection (magnet and angle mismatch)
    conflict_detected = False
    if magnet and (angle > 5 or angle < -5):
        # magnet says closed but angle says open
        conflict_detected = True
    elif not magnet and (-1 <= angle <= 1):
        # magnet says open but angle says closed
        conflict_detected = True
        
    if conflict_detected:
        anomaly_updates.append({
            "entityId": "Door",
            "componentName": "DoorComponents",
            "property": "conflictAnomaly",
            "value": "conflict",
            "valueType": "stringValue"
        })
        
        detected_anomalies.append({
            'entity': 'Door',
            'type': 'sensor_conflict',
            'details': {
                'magnet': magnet,
                'angle': angle,
                'timestamp': datetime.datetime.utcnow().isoformat()
            }
        })
        
        logger.info(f"Sensor conflict detected: magnet={magnet}, angle={angle}")

    # co2 spike detection (simple threshold for now, azure uses ML) 
    # ---> Could have used Kinesis Analytics instead for something similar like azure
    if room1_co2 > 2000:
        anomaly_updates.append({
            "entityId": "Room1",
            "componentName": "RoomSensorComponent",
            "property": "airQualityState",
            "value": "too_high",
            "valueType": "stringValue"
        })
        
        detected_anomalies.append({
            'entity': 'Room1',
            'type': 'co2_spike',
            'details': {
                'co2': room1_co2,
                'timestamp': datetime.datetime.utcnow().isoformat()
            }
        })
        
        logger.info(f"CO2 spike in Room1: {room1_co2}")
    
    if room2_co2 > 2000:
        anomaly_updates.append({
            "entityId": "Room2",
            "componentName": "RoomSensorComponent", 
            "property": "airQualityState",
            "value": "too_high",
            "valueType": "stringValue"
        })
        
        detected_anomalies.append({
            'entity': 'Room2',
            'type': 'co2_spike',
            'details': {
                'co2': room2_co2,
                'timestamp': datetime.datetime.utcnow().isoformat()
            }
        })
        
        logger.info(f"CO2 spike in Room2: {room2_co2}")

    logger.info(f"Found {len(detected_anomalies)} anomalies")
    return {
        'anomalyUpdates': anomaly_updates,
        'anomalies': detected_anomalies
    }