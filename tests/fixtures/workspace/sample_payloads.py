"""Sample payloads for workspace collector tests (optional reference fixtures)."""
from __future__ import annotations

SAMPLE_DATASETS = [
    {"id": "d1", "name": "Sales", "configuredBy": "user@example.com"},
]

SAMPLE_WORKSPACE = {
    "id": "ws-1",
    "name": "My Workspace",
    "capacityRegion": "eastus",
}

SAMPLE_CAPACITY_SETTINGS = {
    "sso": True,
    "automaticPublishing": False,
    "publishToService": True,
}

SAMPLE_PARALLELISM = {
    "maxConnectionsPerDataSource": 10,
    "maxConcurrentJobs": 6,
    "maxParallelismPerQuery": 1,
    "maxSimultaneousEvaluations": 6,
}

SAMPLE_TABLES = [
    {"Name": "Fact", "RowCount": 1000, "StorageMode": "DirectQuery"},
]

SAMPLE_COLUMNS = [
    {"Table": "Fact", "Name": "id", "DataType": "int64", "IsNullable": False, "IsKey": True},
]

SAMPLE_RELATIONSHIPS: list[dict] = []

SAMPLE_MEASURES: list[dict] = []
