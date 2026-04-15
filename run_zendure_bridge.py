# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Top-level runner for zendure-bridge.

This file provides a convenient top-level script that calls the package
CLI entrypoint.
"""

from zendure_bridge.cli import main

if __name__ == "__main__":
    main()
