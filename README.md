# zendure-bridge

Local MQTT bridge for the **Zendure SolarFlow** battery storage system.
Replaces the manufacturer cloud with a local Home Assistant integration.

## What it does

- Intercepts MQTT traffic between the Zendure device and the cloud (via DNS redirect)
- Publishes device state to Home Assistant via **MQTT Discovery** (no custom component needed)
- Allows controlling output power without the Zendure app or cloud
- Extensible: add your own control logic (PID controller, time schedules, price-based automation)

## Hardware

- Zendure SolarFlow hub (tested: `solarFlow` product family)
- Raspberry Pi (or any Linux box) running Mosquitto as MQTT broker
- DNS redirect pointing the Zendure cloud hostname to the local broker

## Requirements

Debian/Ubuntu (preferred – use system packages):

```bash
apt install python3-paho-mqtt python3-yaml
# optional, for automation features:
apt install python3-requests python3-apscheduler
```

Other systems:

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -e .
```

## Configuration

Copy the example config and edit it:

```bash
cp config.yaml.example config.yaml
$EDITOR config.yaml
```

`config.yaml` is in `.gitignore` – your credentials will never be committed.

## Running

```bash
python3 -m zendure_bridge.bridge
```

Or as a systemd service – see `contrib/zendure-bridge.service`.

## Architecture

```
Zendure Device
    │  MQTT (unencrypted, port 1883)
    ▼
Raspberry Pi / Mosquitto  ←──────────────────────┐
    │                                             │
    ▼                                             │
zendure-bridge                             publish state
    │  subscribe: /??????/+/properties/report     │
    │  subscribe: /??????/+/function/invoke       │
    │                                             │
    ├── ZendureDevice (state model)               │
    │                                             │
    └── HAMqttPublisher ───────────────────────────
            │  MQTT Discovery + state topics
            ▼
        Home Assistant
```

## License

Copyright (C) 2026  Your Name

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

See [LICENSE](LICENSE) for the full text.

## Status

🚧 Work in progress – early development.
