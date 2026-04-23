"""Configuration package.

Re-exports:
  - get_settings, Settings    — runtime settings (Pydantic)
  - SIGNATURE_BLOCK, FIRM_*   — locked firm identity constants

The re-exports preserve all existing `from app.config import get_settings`
call sites after we converted this module into a package.
"""
from app.config.firm_identity import (
    FIRM_NAME,
    FIRM_PARTNER_NAME,
    SIGNATURE_BLOCK,
)
from app.config.settings import Settings, get_settings

__all__ = [
    "Settings",
    "get_settings",
    "SIGNATURE_BLOCK",
    "FIRM_NAME",
    "FIRM_PARTNER_NAME",
]
