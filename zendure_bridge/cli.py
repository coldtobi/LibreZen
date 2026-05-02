# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from __future__ import annotations

import argparse
import signal
import sys
from typing import Any

from .version import __version__
from .config import load as load_config
from .bridge import setup_logging, ZendureBridge
from .device import ZendureDevice
from zendure_bridge.homeassistant.ha_publisher import HAPublisher
from .bridge_components import BridgeComponents

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Local MQTT bridge for Zendure SolarFlow"
    )
    parser.add_argument(
        "--config", default="config.yaml",
        help="Path to config file (default: config.yaml)"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--unpublish", action="store_true", default=False, help="Unpublish all Homeassistant entities, then exit.")

    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    setup_logging(config.log_level, config.log_file)

    bc = BridgeComponents(config=config)
    bc.device = ZendureDevice(bc)
    bc.bridge = bridge = ZendureBridge(bc)
    bc.ha_publisher = ha_publisher = HAPublisher(bc)

    # Graceful shutdown on Ctrl-C or SIGTERM
    def _signal_handler(sig: int, frame: Any) -> None:
        bridge.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    if args.unpublish:
        sys.exit(ha_publisher.unpublish())

    bridge.start()
    ha_publisher.start()

    signal.pause()


if __name__ == "__main__":
    main()
