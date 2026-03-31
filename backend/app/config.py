from __future__ import annotations

from app.config_schema import ConfigurationSchema
from app.services.config_service import load_runtime_config


def load_configuration() -> ConfigurationSchema:
    return load_runtime_config().settings
