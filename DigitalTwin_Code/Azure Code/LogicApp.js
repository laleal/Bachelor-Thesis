{
    "definition": {
        "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
        "contentVersion": "1.0.0.0",
        "triggers": {
            "When_a_resource_event_occurs": {
                "type": "ApiConnectionWebhook",
                "inputs": {
                    "host": {
                        "connection": {
                            "name": "@parameters('$connections')['azureeventgrid']['connectionId']"
                        }
                    },
                    "body": {
                        "properties": {
                            "topic": "/subscriptions/d6855903-63a0-4942-b3cb-b4c72f8efa31/resourceGroups/LeasProject/providers/Microsoft.EventGrid/topics/DTtoTeamsEventGrid",
                            "destination": {
                                "endpointType": "webhook",
                                "properties": {
                                    "endpointUrl": "@listCallbackUrl()"
                                }
                            },
                            "filter": {
                                "includedEventTypes": [
                                    "Microsoft.DigitalTwins.Twin.Update"
                                ]
                            }
                        }
                    },
                    "path": "/subscriptions/@{encodeURIComponent('d6855903-63a0-4942-b3cb-b4c72f8efa31')}/providers/@{encodeURIComponent('Microsoft.EventGrid.Topics')}/resource/eventSubscriptions",
                    "queries": {
                        "x-ms-api-version": "2017-09-15-preview"
                    }
                }
            }
        },
        "actions": {
            "Check_Door_Slammed": {
                "actions": {
                    "Send_an_email_(V2)_Door_Slammed": {
                        "type": "ApiConnection",
                        "inputs": {
                            "host": {
                                "connection": {
                                    "name": "@parameters('$connections')['office365']['connectionId']"
                                }
                            },
                            "method": "post",
                            "body": {
                                "To": "email@adress.com",
                                "Subject": "Digital Twin Alert - Door Slammed",
                                "Body": "<p>Alert: Digital twin door slammed anomaly has been detected!</p><p>Twin ID: @{coalesce(first(triggerBody())?['subject'], '')}</p><p>Issue: Door slammed anomaly</p>",
                                "Importance": "High"
                            },
                            "path": "/v2/Mail"
                        }
                    }
                },
                "runAfter": {},
                "else": {
                    "actions": {}
                },
                "expression": {
                    "and": [
                        {
                            "contains": [
                                "@toLower(coalesce(first(triggerBody())?['subject'], ''))",
                                "door"
                            ]
                        },
                        {
                            "equals": [
                                "@first(first(triggerBody())?['data']?['data']?['patch'])?['path']",
                                "/slammedAnomaly"
                            ]
                        },
                        {
                            "equals": [
                                "@toLower(string(first(first(triggerBody())?['data']?['data']?['patch'])?['value']))",
                                "slammed"
                            ]
                        }
                    ]
                },
                "type": "If"
            },
            "Check_Door_Conflict": {
                "actions": {
                    "Send_an_email_(V2)_Door_Conflict": {
                        "type": "ApiConnection",
                        "inputs": {
                            "host": {
                                "connection": {
                                    "name": "@parameters('$connections')['office365']['connectionId']"
                                }
                            },
                            "method": "post",
                            "body": {
                                "To": "email@address.com",
                                "Subject": "Digital Twin Alert - Door Conflict",
                                "Body": "<p>Alert: Digital twin door conflict anomaly has been detected!</p><p>Twin ID: @{coalesce(first(triggerBody())?['subject'], '')}</p><p>Issue: Door conflict anomaly</p>",
                                "Importance": "Normal"
                            },
                            "path": "/v2/Mail"
                        }
                    }
                },
                "runAfter": {},
                "else": {
                    "actions": {}
                },
                "expression": {
                    "and": [
                        {
                            "contains": [
                                "@toLower(coalesce(first(triggerBody())?['subject'], ''))",
                                "door"
                            ]
                        },
                        {
                            "equals": [
                                "@first(first(triggerBody())?['data']?['data']?['patch'])?['path']",
                                "/conflictAnomaly"
                            ]
                        },
                        {
                            "equals": [
                                "@toLower(string(first(first(triggerBody())?['data']?['data']?['patch'])?['value']))",
                                "conflict"
                            ]
                        }
                    ]
                },
                "type": "If"
            },
            "Check_Room_Anomaly": {
                "actions": {
                    "Send_an_email_(V2)_Room_Anomaly": {
                        "type": "ApiConnection",
                        "inputs": {
                            "host": {
                                "connection": {
                                    "name": "@parameters('$connections')['office365']['connectionId']"
                                }
                            },
                            "method": "post",
                            "body": {
                                "To": "email@address.com",
                                "Subject": "Digital Twin Alert - Air Quality Anomaly",
                                "Body": "<p>Alert: Digital twin room anomaly (air quality) has been detected!</p><p>Twin ID: @{coalesce(first(triggerBody())?['subject'], '')}</p><p>Issue: Air quality too high</p>",
                                "Importance": "High"
                            },
                            "path": "/v2/Mail"
                        }
                    }
                },
                "runAfter": {},
                "else": {
                    "actions": {}
                },
                "expression": {
                    "and": [
                        {
                            "or": [
                                {
                                    "contains": [
                                        "@toLower(coalesce(first(triggerBody())?['subject'], ''))",
                                        "room1"
                                    ]
                                },
                                {
                                    "contains": [
                                        "@toLower(coalesce(first(triggerBody())?['subject'], ''))",
                                        "room2"
                                    ]
                                }
                            ]
                        },
                        {
                            "equals": [
                                "@first(first(triggerBody())?['data']?['data']?['patch'])?['path']",
                                "/airQualityState"
                            ]
                        },
                        {
                            "equals": [
                                "@toLower(string(first(first(triggerBody())?['data']?['data']?['patch'])?['value']))",
                                "too_high"
                            ]
                        }
                    ]
                },
                "type": "If"
            }
        },
        "outputs": {},
        "parameters": {
            "$connections": {
                "type": "Object",
                "defaultValue": {}
            }
        }
    },
    "parameters": {
        "$connections": {
            "type": "Object",
            "value": {
                "azureeventgrid": {
                    "id": "/subscriptions/d6855903-63a0-4942-b3cb-b4c72f8efa31/providers/Microsoft.Web/locations/switzerlandnorth/managedApis/azureeventgrid",
                    "connectionId": "/subscriptions/d6855903-63a0-4942-b3cb-b4c72f8efa31/resourceGroups/LeasProject/providers/Microsoft.Web/connections/azureeventgrid",
                    "connectionName": "azureeventgrid"
                },
                "office365": {
                    "id": "/subscriptions/d6855903-63a0-4942-b3cb-b4c72f8efa31/providers/Microsoft.Web/locations/switzerlandnorth/managedApis/office365",
                    "connectionId": "/subscriptions/d6855903-63a0-4942-b3cb-b4c72f8efa31/resourceGroups/LeasProject/providers/Microsoft.Web/connections/office365-1",
                    "connectionName": "office365-1"
                }
            }
        }
    }
}