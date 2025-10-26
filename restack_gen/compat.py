"""Pydantic v1/v2 compatibility shim.

This module provides a unified interface for Pydantic v1 and v2,
allowing generated projects to work with either version.
"""

from __future__ import annotations

from typing import Any

# Base classes selected at runtime
BaseModelBase: Any
SettingsBaseBase: Any

try:
    # Prefer Pydantic v2
    from pydantic import BaseModel as _BaseModelV2
    from pydantic import Field as _Field
    from pydantic import ValidationError
    from pydantic_settings import BaseSettings as _BaseSettingsV2

    PYDANTIC_V2 = True
    BaseModelBase = _BaseModelV2
    SettingsBaseBase = _BaseSettingsV2
    Field = _Field
except ImportError:
    # Fall back to Pydantic v1
    from pydantic import BaseModel as _BaseModelV1
    from pydantic import BaseSettings as _BaseSettingsV1
    from pydantic import Field as _FieldV1
    from pydantic import ValidationError

    PYDANTIC_V2 = False
    BaseModelBase = _BaseModelV1
    SettingsBaseBase = _BaseSettingsV1
    Field = _FieldV1


class BaseModel(BaseModelBase):  # type: ignore[misc]
    """Compatibility BaseModel wrapper for Pydantic v1/v2."""

    if PYDANTIC_V2:
        model_config = {"arbitrary_types_allowed": True, "validate_assignment": True}
    else:
        class Config:
            arbitrary_types_allowed = True
            validate_assignment = True

    @classmethod
    def from_yaml(cls: type["BaseModel"], path: str) -> "BaseModel":
        """Load model from YAML file."""
        from pathlib import Path

        import yaml

        yaml_path = Path(path)
        if not yaml_path.exists():
            # Return default instance if file doesn't exist
            return cls()

        with open(yaml_path) as f:
            data = yaml.safe_load(f)
            return cls(**data) if data else cls()


class SettingsBase(SettingsBaseBase):  # type: ignore[misc]
    """Compatibility Settings wrapper for Pydantic v1/v2."""

    if PYDANTIC_V2:
        model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}
    else:
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            extra = "ignore"

    @classmethod
    def from_yaml(cls: type["SettingsBase"], path: str) -> "SettingsBase":
        """Load settings from YAML file."""
        from pathlib import Path

        import yaml

        yaml_path = Path(path)
        if not yaml_path.exists():
            return cls()

        with open(yaml_path) as f:
            data = yaml.safe_load(f)
            return cls(**data) if data else cls()


__all__ = ["BaseModel", "Field", "SettingsBase", "ValidationError", "PYDANTIC_V2"]
