#!/usr/bin/env python
"""Initialize database tables for the Azure AutoML API."""

from automlapi.db import init_db

if __name__ == "__main__":
    init_db()
