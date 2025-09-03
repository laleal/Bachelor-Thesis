import json
import logging
import datetime
import boto3
from datetime import timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

def load_motion_data():
    try:
        response = s3.get_object(Bucket='bucket-for-lambda-function1', Key='motion-data.json')
        data = json.loads(response['Body'].read())
        timestamps = {}
        for room, timestamp_str in data.items():
            timestamps[room] = datetime.datetime.fromisoformat(timestamp_str)
        return timestamps
    except:
        return {}

def save_motion_data(timestamps):
    data = {room: timestamp.isoformat() for room, timestamp in timestamps.items()}
    s3.put_object(
        Bucket='bucket-for-lambda-function1',
        Key='motion-data.json',
        Body=json.dumps(data)
    )

def lambda_handler(event, context):
    logger.info("Processing room sensor data")
    
    # load last timestamp from S3
    last_motion_timestamps = load_motion_data()
    
    # get door state info for occupancy logic
    door_info = event.get('doorInfo', {})
    door_state = door_info.get('doorState')
    last_door_closed_timestamp = door_info.get('lastDoorClosedTimestamp')
    
    if isinstance(last_door_closed_timestamp, str):
        last_door_closed_timestamp = datetime.datetime.fromisoformat(last_door_closed_timestamp.replace('Z', '+00:00'))
    
    now = datetime.datetime.now(timezone.utc)
    rooms_info = {}
    room_updates = []
    should_save = False

    # loop through both rooms
    for room_key in ['Room1', 'Room2']:
        idx = '1' if room_key == 'Room1' else '2'
        
        temp = event.get(f'device_{idx}_temperature')
        humidity = event.get(f'device_{idx}_humidity')
        light = event.get(f'device_{idx}_light')
        co2 = event.get(f'device_{idx}_co2')
        motion = event.get(f'device_{idx}_motion', False)
        timestamp_str = event.get(f'device_{idx}_timestamp')
        
        # update motion timestamp if detected -> for occupancy logic
        if motion:
            last_motion_timestamps[room_key] = now
            should_save = True
            logger.info(f"Motion in {room_key}")
        
        occupancy_state = calculate_occupancy(room_key, door_state, last_door_closed_timestamp, now, last_motion_timestamps)
        
        rooms_info[room_key] = {
            'temperature': temp,
            'humidity': humidity,
            'light': light,
            'co2': co2,
            'occupancy': occupancy_state
        }

        for prop, value, vtype in [
            ('temperature', temp, 'doubleValue'),
            ('humidity', humidity, 'doubleValue'),
            ('light', light, 'doubleValue'),
            ('co2', co2, 'doubleValue')
        ]:
            if value is not None:
                room_updates.append({
                    'entityId': room_key,
                    'componentName': 'RoomSensorComponent',
                    'property': prop,
                    'value': value,
                    'valueType': vtype
                })
                
        # add occupancy
        room_updates.append({
            'entityId': room_key,
            'componentName': 'RoomSensorComponent',
            'property': 'occupancy',
            'value': occupancy_state,
            'valueType': 'stringValue'
        })
        
        # add timestamp
        if timestamp_str:
            room_updates.append({
                'entityId': room_key,
                'componentName': 'RoomSensorComponent',
                'property': 'roomTimestamp',
                'value': timestamp_str,
                'valueType': 'stringValue'
            })

    # Save motion data back in S3 
    if should_save:
        save_motion_data(last_motion_timestamps)

    logger.info(f"Processed {len(room_updates)} room updates")
    return {
        'roomsInfo': rooms_info,
        'roomUpdates': room_updates
    }

def calculate_occupancy(room_key, door_state, last_door_closed_timestamp, now, last_motion_timestamps):
    if room_key not in last_motion_timestamps:
        return "not_occupied"
    
    last_motion = last_motion_timestamps[room_key]
    seconds_since_motion = (now - last_motion).total_seconds()
    
    if room_key == "Room1":
        # room1 (enclosed room)
        if (door_state == "closed" and 
            last_door_closed_timestamp is not None and 
            last_motion > last_door_closed_timestamp):
            # if motion after door closed then use 30 second timeout
            return "occupied" if seconds_since_motion <= 30 else "not_occupied"
        else:
            # if door open or no motion after close use 10 second timeout
            return "occupied" if seconds_since_motion <= 10 else "not_occupied"
    else:
        # room2 is hallway, always 10 seconds
        return "occupied" if seconds_since_motion <= 10 else "not_occupied"