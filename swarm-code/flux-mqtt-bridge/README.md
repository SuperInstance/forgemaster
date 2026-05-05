# MQTT Constraint Bridge

Publishes FLUX constraint violations and heartbeat telemetry to an MQTT broker.

## Usage

```python
from flux_mqtt_bridge import FluxMqttBridge

bridge = FluxMqttBridge("mqtt.local", 8883, tls=True)
bridge.connect()
bridge.publish_violation("motor_temp", {"temperature": 145.0, "limit": 120.0})
```

## Requirements

- Python 3.11+
- `paho-mqtt>=1.6` (`pip install paho-mqtt`)

## Running Tests

```bash
cd flux-mqtt-bridge/
python test_flux_mqtt_bridge.py
```

Note: Tests that don't require an MQTT broker are included. Integration tests need a running broker.
