#!/usr/bin/env python
"""Initialize database tables for the Azure AutoML API."""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from automlapi.db import init_db

if __name__ == "__main__":
    init_db()
