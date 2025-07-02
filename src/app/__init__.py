"""Compatibility wrapper exposing ``automlapi`` under the ``app`` namespace."""

import sys
import automlapi

sys.modules[__name__].__dict__.update(automlapi.__dict__)
