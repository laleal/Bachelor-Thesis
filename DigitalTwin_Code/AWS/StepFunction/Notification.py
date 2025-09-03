import boto3
import os
import json
import logging
from datetime import datetime
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sns = boto3.client('sns', region_name='eu-north-1')
s3 = boto3.client('s3', region_name='eu-north-1')

def load_reported_anomalies(bucket, key):
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        data = response['Body'].read().decode('utf-8')
        return json.loads(data)
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logger.info("No existing anomaly state file found in S3")
            return {}
        else:
            raise

def save_reported_anomalies(bucket, key, data):
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data, indent=2),
        ContentType='application/json'
    )

def lambda_handler(event, context):
    try:
        sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')
        s3_bucket = 'bucket-for-lambda-function1'  # Hardcoded bucket name
        s3_key = 'anomaly-state/reported_anomalies.json'

        if not sns_topic_arn:
            return {'status': 'error', 'message': 'SNS_TOPIC_ARN not set'}
        if not s3_bucket:
            return {'status': 'error', 'message': 'S3_BUCKET_NAME not set'}

        anomalies = []
        if 'anomalies' in event:
            if isinstance(event['anomalies'], dict) and 'anomalies' in event['anomalies']:
                anomalies = event['anomalies']['anomalies']
            elif isinstance(event['anomalies'], list):
                anomalies = event['anomalies']

        if not anomalies:
            logger.info("No anomalies to notify about")
            return {'status': 'success', 'message': 'No anomalies to notify about'}

        # load anomalies that already happeded
        reported_anomalies = load_reported_anomalies(s3_bucket, s3_key)

        new_anomalies = []
        current_keys = set()

        for anomaly in anomalies:
            entity = anomaly.get('entity', 'Unknown')
            anomaly_type = anomaly.get('type', 'Unknown')
            key = f"{entity}_{anomaly_type}"
            current_keys.add(key)

            if key not in reported_anomalies:
                new_anomalies.append(anomaly)
                reported_anomalies[key] = True
            else:
                logger.info(f"Skipping already reported anomaly: {key}")

        # remove anomalies from list once they don't happen anymore
        for key in list(reported_anomalies.keys()):
            if key not in current_keys:
                del reported_anomalies[key]
                logger.info(f"Anomaly resolved: {key}")

        if not new_anomalies:
            logger.info("No new anomalies to notify about")
            save_reported_anomalies(s3_bucket, s3_key, reported_anomalies)
            return {'status': 'success', 'message': 'No new anomalies to notify about'}

        # create SNS message
        subject = f"IoT TwinMaker Anomaly Alert: {len(new_anomalies)} new anomalies detected"
        message_parts = ["The following new anomalies were detected:"]

        for anomaly in new_anomalies:
            entity = anomaly.get('entity', 'Unknown')
            anomaly_type = anomaly.get('type', 'Unknown')
            details = anomaly.get('details', {})
            timestamp = details.get('timestamp', 'Unknown time')
            value = details.get('value', 'No value')

            if anomaly_type == 'door_slam':
                message_parts.append(f"- Door slam detected on {entity} with gyro value {value} at {timestamp}")
            elif anomaly_type == 'sensor_conflict':
                if isinstance(value, dict):
                    magnet = value.get('magnet', 'unknown')
                    angle = value.get('angle', 'unknown')
                    message_parts.append(f"- Sensor conflict on {entity}: magnet={magnet}, angle={angle} at {timestamp}")
                else:
                    message_parts.append(f"- Sensor conflict on {entity}: {value} at {timestamp}")
            elif anomaly_type == 'co2_spike':
                message_parts.append(f"- CO2 spike in {entity}: {value} ppm at {timestamp}")
            else:
                message_parts.append(f"- Unknown anomaly type {anomaly_type} on {entity}: {value} at {timestamp}")

        message = "\n".join(message_parts)
        logger.info(f"Sending message:\n{message}")

        response = sns.publish(
            TopicArn=sns_topic_arn,
            Message=message,
            Subject=subject
        )

        # save updated anomaly list to s3
        save_reported_anomalies(s3_bucket, s3_key, reported_anomalies)

        return {
            'status': 'success',
            'message': f"Notified about {len(new_anomalies)} new anomalies",
            'snsMessageId': response.get('MessageId'),
            'anomaliesNotified': len(new_anomalies),
            'totalAnomalies': len(anomalies),
            's3Key': s3_key
        }

    except Exception as e:
        import traceback
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
        return {'status': 'error', 'message': str(e)}
