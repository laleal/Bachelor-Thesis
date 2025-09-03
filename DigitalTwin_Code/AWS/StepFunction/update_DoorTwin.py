import boto3
import os
import math
from datetime import datetime

iottwinmaker = boto3.client('iottwinmaker', region_name='eu-central-1')

def parse_timestamp(timestamp_string):
    try:
        if timestamp_string.endswith('Z'):
            timestamp_string = timestamp_string[:-1]
        return datetime.fromisoformat(timestamp_string)
    except:
        return None

# functio to check if twin should be updated
# because the stepfunction sometimes is a bit faster or a bit slower so the data arrives at the twin out of order
# we have to check the timestamp to see if this data is newer than the data in the twinmaker
def should_update(workspace_id, entity_id, component_name, new_timestamp_str, timestamp_property):
    if not new_timestamp_str:
        return True

    new_timestamp = parse_timestamp(new_timestamp_str)
    if not new_timestamp:
        return False

    try:
        response = iottwinmaker.get_entity(workspaceId=workspace_id, entityId=entity_id)
        existing_property = (
            response.get("components", {})
            .get(component_name, {})
            .get("properties", {})
            .get(timestamp_property, {})
        )
        current_timestamp_str = existing_property.get("value", {}).get("stringValue")

        if current_timestamp_str:
            current_timestamp = parse_timestamp(current_timestamp_str)
            if current_timestamp and new_timestamp <= current_timestamp:
                return False

        return True

    except:
        return True  # Allow update

def update_entity(workspace_id, entity_id, updates):
    try:
        iottwinmaker.update_entity(
            workspaceId=workspace_id,
            entityId=entity_id,
            componentUpdates=updates
        )
    except:
        print(f"Failed to update entity: {entity_id}")

def lambda_handler(event, context):
    workspace_id = os.environ.get("TWINMAKER_WORKSPACE_ID", "door")



    ################################   For 3D scene - Plate_001 angle rotation   ####################################
    rotation_angle = None
    door_timestamp = None

    for update in event.get("doorInfo", {}).get("doorUpdates", []):
        if update.get("property") == "angle":
            rotation_angle = update.get("value")
        elif update.get("property") == "doorTimestamp":
            door_timestamp = update.get("value")

    if rotation_angle is not None and door_timestamp:
        if should_update(workspace_id, "Door", "DoorComponents", door_timestamp, "doorTimestamp"):
            angle_in_radians = float(rotation_angle) * math.pi / 180
            update_entity(
                workspace_id,
                "5dbaf7df-ea98-4bf7-8f8d-96afd0a390b0",  # plate_001
                {
                    "Node": {
                        "componentTypeId": "com.amazon.iottwinmaker.3d.node",
                        "updateType": "UPDATE",
                        "propertyUpdates": {
                            "transform_rotation": {
                                "value": {
                                    "listValue": [
                                        {"doubleValue": -math.pi / 2},
                                        {"doubleValue": 0.0},
                                        {"doubleValue": angle_in_radians}
                                    ]
                                }
                            }
                        }
                    }
                }
            )


    ################################   Door updates   ####################################################
    if door_timestamp and should_update(workspace_id, "Door", "DoorComponents", door_timestamp, "doorTimestamp"):
        property_updates = {"DoorComponents": {"updateType": "UPDATE", "propertyUpdates": {}}}

        for update in event.get("doorInfo", {}).get("doorUpdates", []):
            property_name = update.get("property")
            value = update.get("value")
            value_type = update.get("valueType", "stringValue")

            if value_type == "doubleValue":
                property_updates["DoorComponents"]["propertyUpdates"][property_name] = {"value": {"doubleValue": float(value)}}
            elif value_type == "booleanValue":
                property_updates["DoorComponents"]["propertyUpdates"][property_name] = {"value": {"booleanValue": bool(value)}}
            else:
                property_updates["DoorComponents"]["propertyUpdates"][property_name] = {"value": {"stringValue": str(value)}}

        update_entity(workspace_id, "Door", property_updates)



    ################################   Room1 and Room2 updates (3D scene lights)  ####################################################
    for room_id, light_entity_id in [("Room1", "138bc7e7-4f77-49a4-9a1a-0e4e678aaade"), ("Room2", "a990152b-203a-4bdb-a6c9-4b43bf8d6f78")]:
        room_timestamp = None
        light_value = None
        property_updates = {"RoomComponents": {"updateType": "UPDATE", "propertyUpdates": {}}}

        for update in event.get("roomsInfo", {}).get("roomUpdates", []):
            if update.get("entityId") != room_id:
                continue

            property_name = update.get("property")
            value = update.get("value")
            value_type = update.get("valueType", "stringValue")

            if property_name == "roomTimestamp":
                room_timestamp = value
            if property_name == "light":
                light_value = value

            if value_type == "doubleValue":
                property_updates["RoomComponents"]["propertyUpdates"][property_name] = {"value": {"doubleValue": float(value)}}
            elif value_type == "booleanValue":
                property_updates["RoomComponents"]["propertyUpdates"][property_name] = {"value": {"booleanValue": bool(value)}}
            else:
                property_updates["RoomComponents"]["propertyUpdates"][property_name] = {"value": {"stringValue": str(value)}}

        if room_timestamp and should_update(workspace_id, room_id, "RoomComponents", room_timestamp, "roomTimestamp"):
            update_entity(workspace_id, room_id, property_updates)

        ############## 3D Scne lights ##############
        if light_value is not None:
            try:
                raw_light = float(light_value)
                if raw_light < 50:
                    normalized = raw_light / 50.0
                elif raw_light < 300:
                    normalized = raw_light / 300.0
                else:
                    normalized = min(raw_light / 300.0, 1.0)

                normalized = max(normalized, 0.1) 

                update_entity(
                    workspace_id,
                    light_entity_id,
                    {
                        "Light": {
                            "updateType": "UPDATE",
                            "propertyUpdates": {
                                "lightSettings_intensity": {
                                    "value": {"doubleValue": normalized}
                                }
                            }
                        }
                    }
                )
            except Exception as e:
                print(f"Could not update 3D light for {room_id}: {e}")

    ##############################################   Anomaly Updates (should always update NO timestamp check) #####################################
    for anomaly in event.get("anomalies", {}).get("anomalyUpdates", []):
        entity_id = anomaly.get("entityId")
        component_name = anomaly.get("componentName", "AnomalyComponents")
        property_name = anomaly.get("property")
        value = anomaly.get("value")
        value_type = anomaly.get("valueType", "stringValue")

        if not entity_id or not property_name:
            continue



        update_entity(
            workspace_id,
            entity_id,
            {
                component_name: {
                    "updateType": "UPDATE",
                    "propertyUpdates": {
                        property_name: {
                            "value": (
                                {value_type: value}
                                if value_type != "stringValue"
                                else {"stringValue": str(value)}
                            )
                        }
                    }
                }
            }
        )

    # pass all the data for Timestream function
    return {
        "status": "done",
        "doorInfo": event.get("doorInfo", {}),
        "roomsInfo": event.get("roomsInfo", {}),
        "anomalies": event.get("anomalies", {}),
        "timestreamReady": True
    }