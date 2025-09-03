using System;
using System.IO;
using System.Net;
using System.Threading.Tasks;
using System.Text.Json;
using System.Collections.Generic;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Http;
using Microsoft.Extensions.Logging;
using Azure.DigitalTwins.Core;
using Azure.Identity;
using Azure;

namespace DoorFunction
{
    public class AsaToAdtFunction
    {
        private readonly ILogger _logger;
        private readonly DigitalTwinsClient _adtClient;

        public AsaToAdtFunction(ILoggerFactory loggerFactory)
        {
            _logger = loggerFactory.CreateLogger<AsaToAdtFunction>();

            var adtInstanceUrl = Environment.GetEnvironmentVariable("ADT_SERVICE_URL");
            if (string.IsNullOrEmpty(adtInstanceUrl))
            {
                throw new Exception("ADT_SERVICE_URL environment variable is missing");
            }

            var credential = new DefaultAzureCredential();
            _adtClient = new DigitalTwinsClient(new Uri(adtInstanceUrl), credential);
        }

        [Function("AsaToADTFunction")]
        public async Task<HttpResponseData> ProcessAnomalies(
            [HttpTrigger(AuthorizationLevel.Function, "post")] HttpRequestData req)
        {
            _logger.LogInformation("Processing anomaly data from Stream Analytics");

            try
            {
                // parse the incoming anomaly data
                var requestBody = await new StreamReader(req.Body).ReadToEndAsync();
                var anomalies = JsonSerializer.Deserialize<List<AnomalyPayload>>(requestBody);

                // process all the anomaly that were found
                foreach (var anomaly in anomalies ?? new List<AnomalyPayload>())
                {
                    await ProcessSingleAnomaly(anomaly);
                }

                var response = CreateResponse(req, HttpStatusCode.OK,
                    $"Updated {anomalies?.Count ?? 0} twins with anomaly data");
                return response;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Something went wrong updating the twins");
                return CreateResponse(req, HttpStatusCode.InternalServerError,
                    "Couldn't update the digital twins");
            }
        }

        private async Task ProcessSingleAnomaly(AnomalyPayload anomaly)
        {
            // get current state of the digital twin
            var twinResponse = await _adtClient.GetDigitalTwinAsync<JsonElement>(anomaly.TwinId);
            var currentTwin = twinResponse.Value;

            // check if twin already has the right anomaly state (so we don't trigger another email)
            if (ShouldUpdateTwin(currentTwin, anomaly))
            {
                await UpdateTwinProperty(anomaly);
                _logger.LogInformation("Updated {TwinId}: {Property} = {Value}",
                    anomaly.TwinId, anomaly.Property, anomaly.Value);
            }
        }

        private bool ShouldUpdateTwin(JsonElement currentTwin, AnomalyPayload anomaly)
        {
            if (!currentTwin.TryGetProperty(anomaly.Property, out var currentValue))
            {
                return true;
            }

            return currentValue.GetString() != anomaly.Value;
        }
        

        private async Task UpdateTwinProperty(AnomalyPayload anomaly)
        {
            var patchDocument = new Azure.JsonPatchDocument();
            patchDocument.AppendReplace($"/{anomaly.Property}", anomaly.Value);

            await _adtClient.UpdateDigitalTwinAsync(anomaly.TwinId, patchDocument);
        }

        private HttpResponseData CreateResponse(HttpRequestData req, HttpStatusCode statusCode, string message)
        {
            var response = req.CreateResponse(statusCode);
            response.WriteString(message);
            return response;
        }
    }

    // Data model for anomaly data passed by ASA
    public class AnomalyPayload
    {
        public string TwinId { get; set; } = string.Empty;
        public string Property { get; set; } = string.Empty;
        public string Value { get; set; } = string.Empty;

    }