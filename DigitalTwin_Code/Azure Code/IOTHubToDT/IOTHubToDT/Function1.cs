using System;
using System.Collections.Concurrent;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using Azure;
using Azure.DigitalTwins.Core;
using Azure.Identity;
using Azure.Messaging.EventGrid;
using Microsoft.Azure.WebJobs;
using Microsoft.Azure.WebJobs.Extensions.EventGrid;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace DoorFunction
{
    public static class MyEventGridFunction
    {
        private static readonly string adtInstanceUrl = Environment.GetEnvironmentVariable("ADT_SERVICE_URL");
        private static readonly HttpClient httpClient = new HttpClient();
        private static ConcurrentDictionary<string, DateTime> lastMotionTimestamps = new ConcurrentDictionary<string, DateTime>();
        private static DateTime lastDoorClosedTimestamp = DateTime.MinValue;
        private static string doorState = "unknown";

        [FunctionName("IOTHubToDT")]
        public static async Task RunAsync([EventGridTrigger] EventGridEvent eventGridEvent, ILogger log)
        {
            if (adtInstanceUrl == null)
            {
                log.LogError("ADT_SERVICE_URL environment variable not set");
                return;
            }

            var client = new DigitalTwinsClient(new Uri(adtInstanceUrl), new DefaultAzureCredential());
            log.LogInformation("Processing IoT data from gateway");

            if (eventGridEvent?.Data == null)
            {
                log.LogWarning("No data received from IoT Hub");
                return;
            }

            try
            {
                // decode the base64 payload from event grid
                JObject dataObject = JObject.Parse(eventGridEvent.Data.ToString());
                if (dataObject["body"] == null)
                {
                    log.LogWarning("No payload body found");
                    return;
                }

                string base64Body = dataObject["body"].ToString();
                string rawJson = Encoding.UTF8.GetString(Convert.FromBase64String(base64Body));

                // deserialize the sensor data
                var payload = JsonConvert.DeserializeObject<Payload>(rawJson);
                if (payload == null)
                {
                    log.LogError("Failed to parse sensor payload");
                    return;
                }

                // ------------------------- Process Door First -----------------------------//
                string newDoorState = ComputeDoorState(payload.local_data);
                await UpdateDoorTwinAsync(client, newDoorState, payload.local_data, log);

                // ------------------------- Process Rooms -----------------------------//
                await UpdateRoomTwinAsync(client, "Room1", payload.remote_data.device_1, log);
                await UpdateRoomTwinAsync(client, "Room2", payload.remote_data.device_2, log);
            }
            catch (Exception ex)
            {
                log.LogError(ex, "Error processing sensor data");
            }
        }

        // ------------------------- Function to update Door Twin -----------------------------//
        private static async Task UpdateDoorTwinAsync(DigitalTwinsClient client, string newDoorState, LocalData doorData, ILogger log)
        {
            var patch = new JsonPatchDocument();
            patch.AppendReplace("/angle", doorData.angle);
            patch.AppendReplace("/gyro", doorData.gyro);
            patch.AppendReplace("/magnet", doorData.magnet);
            patch.AppendReplace("/doorState", newDoorState);

            // Track door state changes for room occupancy logic
            if (newDoorState == "closed" && doorState != "closed")
            {
                lastDoorClosedTimestamp = DateTime.UtcNow;
                log.LogInformation("Door closed");
            }

            doorState = newDoorState;
            await client.UpdateDigitalTwinAsync("Door", patch);
            log.LogInformation($"Updated Door: {newDoorState}");
        }

        // ------------------------- Function to update ROOM & Occupancy STATE Logic -----------------------------//
        private static async Task UpdateRoomTwinAsync(DigitalTwinsClient client, string roomId, DeviceData deviceData, ILogger log)
        {
            var patch = new JsonPatchDocument();
            DateTime now = DateTime.UtcNow;

            // update all the sensor values
            patch.AppendReplace("/temperature", deviceData.temperature);
            patch.AppendReplace("/humidity", deviceData.humidity);
            patch.AppendReplace("/light", deviceData.light);
            patch.AppendReplace("/co2", deviceData.co2);

            // if motion detected, update the timestamp
            if (deviceData.motion)
            {
                lastMotionTimestamps[roomId] = now;
            }

            // check if room is occupied
            string occupancyState = CalculateOccupancy(roomId, now);
            patch.AppendReplace("/occupancy", occupancyState);

            await client.UpdateDigitalTwinAsync(roomId, patch);
            log.LogInformation($"Updated {roomId}: occupancy = {occupancyState}");
        }

        private static string CalculateOccupancy(string roomId, DateTime now)
        {
            if (!lastMotionTimestamps.TryGetValue(roomId, out DateTime lastMotion))
            {
                return "not_occupied";
            }

            double secondsSinceMotion = (now - lastMotion).TotalSeconds;

            if (roomId == "Room1")
            {
                // room1 has different timeout rules depending on door state
                if (doorState == "closed" && lastMotion > lastDoorClosedTimestamp)
                {
                    return secondsSinceMotion <= 30 ? "occupied" : "not_occupied";
                }
                else
                {
                    return secondsSinceMotion <= 10 ? "occupied" : "not_occupied";
                }
            }
            else
            {
                // room2 is a hallway so just use 10 seconds
                return secondsSinceMotion <= 10 ? "occupied" : "not_occupied";
            }
        }

        // ------------------------- Function to compute Door STATE Logic -----------------------------//
        // LOGIC for Door State:
        // 1) If magnet == true => doorState = "closed"
        // 2) Else if angle > 30 => doorState = "open"
        // 3) Else => doorState = "partially_open"
        private static string ComputeDoorState(LocalData doorData)
        {
            // if magnet detected or angle is small, door is closed
            if (doorData.magnet || (doorData.angle >= -5 && doorData.angle <= 5)) 
                // also added the angle because magnet sensor sometimes breaks (gets to permanently magnetized)
            {
                return "closed";
            }

            // if angle is bigger than 30 door is open (door can open in both directions
            if (doorData.angle > 30 || doorData.angle < -30)
            {
                return "open";
            }

            return "partially_open";
        }
    }

    public class Payload
    {
        public LocalData local_data { get; set; }
        public RemoteData remote_data { get; set; }
    }

    public class LocalData
    {
        public double angle { get; set; }
        public double gyro { get; set; }
        public bool magnet { get; set; }
    }

    public class RemoteData
    {
        public DeviceData device_1 { get; set; }
        public DeviceData device_2 { get; set; }
    }

    public class DeviceData
    {
        public double temperature { get; set; }
        public double humidity { get; set; }
        public double light { get; set; }
        public bool motion { get; set; }
        public double co2 { get; set; }
    }
}