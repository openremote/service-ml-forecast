# OpenRemote Client

A Python client for interacting with the OpenRemote API.

## Installation

This package is part of the service-ml-forecast workspace and can be installed as a dependency.

## Usage

```python
from openremote_client import OpenRemoteClient

# Initialize the client
client = OpenRemoteClient(
    openremote_url="https://your-openremote-instance.com",
    keycloak_url="https://your-keycloak-instance.com/auth",
    service_user="your-service-user",
    service_user_secret="your-service-user-secret"
)

# Check if the API is healthy
if client.health_check():
    print("OpenRemote API is healthy")

# Get historical datapoints
datapoints = client.get_historical_datapoints(
    asset_id="your-asset-id",
    attribute_name="your-attribute-name",
    from_timestamp=1716153600000,
    to_timestamp=1716240000000
)

# Write predicted datapoints
from openremote_client import AssetDatapoint

predicted_datapoints = [
    AssetDatapoint(x=1716153600000, y=100.5),
    AssetDatapoint(x=1716153660000, y=101.2),
]

success = client.write_predicted_datapoints(
    asset_id="your-asset-id",
    attribute_name="your-attribute-name",
    datapoints=predicted_datapoints
)
```

## Available Classes

- `OpenRemoteClient`: Main client for API interactions
- `AssetDatapoint`: Data point model with timestamp and value
- `BasicAsset`: Asset model with basic information
- `Realm`: Realm model
- `AssetDatapointPeriod`: Period information model
- `AssetDatapointQuery`: Query request model
- `BasicAttribute`: Basic attribute model

## API Reference

### Health Check

#### `health_check() -> bool`
Check if the OpenRemote API is healthy.

```python
if client.health_check():
    print("API is healthy")
else:
    print("API is not responding")
```

### Asset Datapoint Operations

#### `get_asset_datapoint_period(asset_id: str, attribute_name: str, realm: str = "master") -> AssetDatapointPeriod | None`
Retrieve the datapoints timestamp period of a given asset attribute.

```python
period = client.get_asset_datapoint_period(
    asset_id="your-asset-id",
    attribute_name="temperature"
)
if period:
    print(f"Oldest timestamp: {period.oldestTimestamp}")
    print(f"Latest timestamp: {period.latestTimestamp}")
```

#### `get_historical_datapoints(asset_id: str, attribute_name: str, from_timestamp: int, to_timestamp: int, realm: str = "master") -> list[AssetDatapoint] | None`
Retrieve historical data points of a given asset attribute.

**Note**: Request may fail if more than 100k datapoints are requested, depending on the OpenRemote instance.

```python
datapoints = client.get_historical_datapoints(
    asset_id="your-asset-id",
    attribute_name="temperature",
    from_timestamp=1716153600000,  # Start time in milliseconds
    to_timestamp=1716240000000     # End time in milliseconds
)
if datapoints:
    for datapoint in datapoints:
        print(f"Time: {datapoint.x}, Value: {datapoint.y}")
```

#### `write_predicted_datapoints(asset_id: str, attribute_name: str, datapoints: list[AssetDatapoint], realm: str = "master") -> bool`
Write predicted data points of a given asset attribute.

```python
from openremote_client import AssetDatapoint

predicted_datapoints = [
    AssetDatapoint(x=1716153600000, y=100.5),
    AssetDatapoint(x=1716153660000, y=101.2),
    AssetDatapoint(x=1716153720000, y=102.1),
]

success = client.write_predicted_datapoints(
    asset_id="your-asset-id",
    attribute_name="temperature",
    datapoints=predicted_datapoints
)
if success:
    print("Predicted datapoints written successfully")
```

#### `get_predicted_datapoints(asset_id: str, attribute_name: str, from_timestamp: int, to_timestamp: int, realm: str = "master") -> list[AssetDatapoint] | None`
Retrieve predicted data points of a given asset attribute.

```python
predicted_datapoints = client.get_predicted_datapoints(
    asset_id="your-asset-id",
    attribute_name="temperature",
    from_timestamp=1716153600000,
    to_timestamp=1716240000000
)
if predicted_datapoints:
    for datapoint in predicted_datapoints:
        print(f"Predicted Time: {datapoint.x}, Value: {datapoint.y}")
```

### Asset Management

#### `asset_query(asset_query: dict, query_realm: str, realm: str = "master") -> list[BasicAsset] | None`
Perform a custom asset query.

```python
# Query assets with specific criteria
query = {
    "recursive": True,
    "realm": {"name": "your-realm"},
    "ids": ["asset1", "asset2"],
}

assets = client.asset_query(query, "your-realm")
if assets:
    for asset in assets:
        print(f"Asset ID: {asset.id}, Name: {asset.name}")
```

#### `get_assets_by_ids(asset_ids: list[str], query_realm: str, realm: str = "master") -> list[BasicAsset] | None`
Retrieve assets by their IDs.

```python
asset_ids = ["asset1", "asset2", "asset3"]
assets = client.get_assets_by_ids(asset_ids, "your-realm")
if assets:
    for asset in assets:
        print(f"Asset ID: {asset.id}, Name: {asset.name}, Realm: {asset.realm}")
```

### Realm Management

#### `get_realms(realm: str = "master") -> list[Realm] | None`
Retrieve all realms.

```python
realms = client.get_realms()
if realms:
    for realm in realms:
        print(f"Realm ID: {realm.id}")
        print(f"Realm Name: {realm.name}")
        print(f"Display Name: {realm.displayName}")
        print(f"Enabled: {realm.enabled}")
```

## Features

- OAuth2 authentication with automatic token refresh
- Historical datapoint retrieval
- Predicted datapoint writing and retrieval
- Asset querying and management
- Realm management
- Health check functionality
- Comprehensive error handling
- Type hints for better IDE support

## Error Handling

All methods return appropriate fallback values on errors:
- `None` for data retrieval methods when the operation fails
- `False` for boolean methods when the operation fails
- Exceptions are logged but not raised to the caller

## Authentication

The client automatically handles OAuth2 authentication with Keycloak:
- Automatic token acquisition on initialization
- Token refresh when tokens expire
- Transparent authentication for all API calls

