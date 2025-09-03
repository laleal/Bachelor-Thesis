import boto3
import os
import time
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

timestream = boto3.client('timestream-write', region_name='eu-central-1')

def lambda_handler(event, context):
    
    database = os.environ.get('TIMESTREAM_DATABASE_NAME', 'DoorSensorData')
    table = os.environ.get('TIMESTREAM_TABLE_NAME', 'SensorReadings')
    
    updates = get_all_updates(event)   
    records = prepare_records(updates)
    write_to_timestream(database, table, records)
    
    return {"message": f"Successfully processed {len(updates)} sensor updates"}


# function to get the data from input
def get_all_updates(event):
    
    updates = []
    
    door_info = event.get('doorInfo', {})
    if door_info:
        updates.extend(door_info.get('doorUpdates', []))
     
    rooms_info = event.get('roomsInfo', {})
    if rooms_info:
        updates.extend(rooms_info.get('roomUpdates', []))
    
    anomalies = event.get('anomalies', {})
    if anomalies:
        updates.extend(anomalies.get('anomalyUpdates', []))
    
    return updates

# preparing the data (timestream need special time format)
def prepare_records(updates):
    
    records = []
    current_time = int(time.time() * 1000)
    
    for update in updates:
        if not isinstance(update, dict):
            continue
            
        entity_id = update.get('entityId')
        component = update.get('componentName')
        property_name = update.get('property')
        value = update.get('value')
        
        
        # figure out the data type
        value_type = update.get('valueType', 'stringValue')
        if value_type == 'doubleValue':
            measure_value = str(float(value))
            measure_type = 'DOUBLE'
        elif value_type == 'booleanValue':
            measure_value = str(bool(value))
            measure_type = 'VARCHAR'
        else:
            measure_value = str(value)
            measure_type = 'VARCHAR'
        
        record = {
            'Dimensions': [
                {'Name': 'entityId', 'Value': entity_id},
                {'Name': 'componentName', 'Value': component}
            ],
            'MeasureName': property_name,
            'MeasureValue': measure_value,
            'MeasureValueType': measure_type,
            'Time': str(update.get('timestamp', current_time)),
            'TimeUnit': 'MILLISECONDS'
        }
        
        records.append(record)
    
    return records

def write_to_timestream(database, table, records):
    
    batch_size = 100
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        
        try:
            timestream.write_records(
                DatabaseName=database,
                TableName=table,
                Records=batch
            )
            logger.info(f"{len(batch)} records sent to timesream")
            
        except Exception as e:
            logger.error(f"Failed: {str(e)}")
