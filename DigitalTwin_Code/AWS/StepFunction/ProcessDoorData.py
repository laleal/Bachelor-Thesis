import json
import logging
import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("Processing door sensor data")

    # get the door sensor readings
    angle = event.get('angle', 0)
    gyro = event.get('gyro', 0)
    magnet = event.get('magnet', False)
    door_timestamp = event.get('door_timestamp', datetime.datetime.utcnow().isoformat())

    # figure out what state the door is in
    if magnet or (-5 <= angle <= 5):
        state = 'closed'
    elif angle > 30 or angle < -30:
        state = 'open'
    else:
        state = 'partially_open'
    
    logger.info(f"Door is {state} (angle={angle}, magnet={magnet})")

    door_updates = [
        {
            "entityId": "Door",
            "componentName": "DoorComponents",
            "property": "doorState",
            "value": state,
            "valueType": "stringValue"
        },
        {
            "entityId": "Door", 
            "componentName": "DoorComponents",
            "property": "angle",
            "value": angle,
            "valueType": "doubleValue"
        },
        {
            "entityId": "Door",
            "componentName": "DoorComponents", 
            "property": "gyro",
            "value": gyro,
            "valueType": "doubleValue"
        },
        {
            "entityId": "Door",
            "componentName": "DoorComponents",
            "property": "magnet", 
            "value": magnet,
            "valueType": "booleanValue"
        },
        {
            "entityId": "Door",
            "componentName": "DoorComponents",
            "property": "doorTimestamp",
            "value": door_timestamp,
            "valueType": "stringValue"
        }
    ]

    # return the results for the step function
    response = {
        'doorState': state,
        'lastDoorClosedTimestamp': door_timestamp if state == 'closed' else None,
        'doorUpdates': door_updates
    }

    logger.info(f"Door processing done: {state}")
    return response