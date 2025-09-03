WITH
  raw_readings AS (
    SELECT
      System.Timestamp AS ts,
      remote_data.device_1.co2 AS co2_1,
      remote_data.device_2.co2 AS co2_2,
      local_data.angle AS door_angle,
      local_data.magnet AS door_magnet,
      local_data.gyro AS door_gyro
    FROM DigitalTwinLea
  ),

  anomaly_detections AS (
    SELECT
      rr.ts,
      rr.door_angle,
      rr.door_magnet,
      rr.door_gyro,

      AnomalyDetection_SpikeAndDip(
        CAST(rr.co2_1 AS FLOAT), 99, 120, 'spikesanddips'
      ) OVER (LIMIT DURATION(second, 1000)) AS anom_co2_room1,

      AnomalyDetection_SpikeAndDip(
        CAST(rr.co2_2 AS FLOAT), 99, 120, 'spikesanddips'
      ) OVER (LIMIT DURATION(second, 1000)) AS anom_co2_room2

    FROM raw_readings rr
  ),

  threshold_checks AS (
    SELECT
    'Door' AS twinID,
      CAST(GetRecordPropertyValue(anom_co2_room1, 'IsAnomaly') AS BIGINT) AS is_co2_room1,
      CAST(GetRecordPropertyValue(anom_co2_room2, 'IsAnomaly') AS BIGINT) AS is_co2_room2,
CASE
  WHEN (door_magnet = 1 AND door_angle > 5)
    OR (door_magnet = 1 AND door_angle < -5) 
    OR (door_magnet = 0 AND door_angle BETWEEN -1 AND 1)
  THEN 1 ELSE 0
END AS is_conflict_anomaly,
      CASE
        WHEN door_gyro > 65 THEN 1
        ELSE 0
      END AS is_slam_anomaly
    FROM anomaly_detections
  )

-- combine output for AsaToADTFunction
SELECT unioned.twinId,
       unioned.property,
       unioned.value
INTO AsaToADTFunction
FROM
(
    -- TwinId for CO₂ anomalies
    SELECT
        'Room1' AS twinID,
        'airQualityState' AS property,
        'too_high' AS value
    FROM threshold_checks
    WHERE is_co2_room1 = 1

    UNION ALL

    -- TwinId for CO₂ anomaly
    SELECT
        'Room2' AS twinID,
        'airQualityState' AS property,
        'too_high' AS value
    FROM threshold_checks
    WHERE is_co2_room2 = 1

    UNION ALL

    -- Door conflict anomaly
    SELECT
        'Door' AS twinID,
        'conflictAnomaly' AS property,
        'conflict' AS value
    FROM threshold_checks
    WHERE is_conflict_anomaly = 1

    UNION ALL

    -- Door slam anomaly
    SELECT
        'Door' AS twinID,
        'slammedAnomaly' AS property,
        'slammed' AS value
    FROM threshold_checks
    WHERE is_slam_anomaly = 1
) AS unioned;
