"""Pydantic v1/v2 compatibility shim.

This module provides a unified interface for Pydantic v1 and v2,
allowing generated projects to work with either version.
"""

try:
    # Try Pydantic v2 first
    from pydantic import BaseModel as _BaseModel
    from pydantic import Field as _Field
    from pydantic import ValidationError
    from pydantic_settings import BaseSettings as _BaseSettings

    PYDANTIC_V2 = True

    class BaseModel(_BaseModel):
        """Pydantic v2 BaseModel wrapper."""

        model_config = {"arbitrary_types_allowed": True, "validate_assignment": True}

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

    class SettingsBase(_BaseSettings):
        """Pydantic v2 Settings wrapper."""

        model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

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

    Field = _Field

except ImportError:
    # Fall back to Pydantic v1
    from pydantic import BaseModel as _BaseModelV1  # type: ignore
    from pydantic import BaseSettings as _BaseSettingsV1  # type: ignore
    from pydantic import Field as _FieldV1  # type: ignore
    from pydantic import ValidationError  # type: ignore

    PYDANTIC_V2 = False

    class BaseModel(_BaseModelV1):  # type: ignore
        """Pydantic v1 BaseModel wrapper."""

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
                return cls()

            with open(yaml_path) as f:
                data = yaml.safe_load(f)
                return cls(**data) if data else cls()

    class SettingsBase(_BaseSettingsV1):  # type: ignore
        """Pydantic v1 Settings wrapper."""

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

    Field = _FieldV1  # type: ignore


__all__ = ["BaseModel", "Field", "SettingsBase", "ValidationError", "PYDANTIC_V2"]
