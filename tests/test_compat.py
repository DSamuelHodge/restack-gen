"""Tests for Pydantic compatibility layer."""

from pathlib import Path
from typing import Any

import pytest

from restack_gen import compat


def test_pydantic_version_detection() -> None:
    """Test that we correctly detect Pydantic version."""
    assert isinstance(compat.PYDANTIC_V2, bool)
    # Should have detected one version or the other
    assert compat.PYDANTIC_V2 is True or compat.PYDANTIC_V2 is False


def test_base_model_available() -> None:
    """Test that BaseModel is available."""
    assert compat.BaseModel is not None
    assert hasattr(compat.BaseModel, "model_config") or hasattr(compat.BaseModel, "Config")


def test_settings_base_available() -> None:
    """Test that SettingsBase is available."""
    assert compat.SettingsBase is not None
    assert hasattr(compat.SettingsBase, "model_config") or hasattr(
        compat.SettingsBase, "Config"
    )


def test_field_available() -> None:
    """Test that Field is available."""
    assert compat.Field is not None


def test_validation_error_available() -> None:
    """Test that ValidationError is available."""
    assert compat.ValidationError is not None


def test_base_model_instantiation() -> None:
    """Test creating a BaseModel instance."""

    class TestModel(compat.BaseModel):
        name: str
        value: int = 0

    model = TestModel(name="test")
    assert model.name == "test"
    assert model.value == 0


def test_base_model_validation() -> None:
    """Test BaseModel validation."""

    class TestModel(compat.BaseModel):
        name: str
        value: int

    # Valid data
    model = TestModel(name="test", value=42)
    assert model.name == "test"
    assert model.value == 42

    # Invalid data should raise ValidationError
    with pytest.raises(compat.ValidationError):
        TestModel(name="test", value="not an int")  # type: ignore[arg-type]


def test_base_model_from_yaml(tmp_path: Path) -> None:
    """Test loading BaseModel from YAML file."""

    class TestModel(compat.BaseModel):
        name: str
        value: int = 0

    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("name: test\nvalue: 42\n")

    model = TestModel.from_yaml(str(yaml_file))
    assert model.name == "test"
    assert model.value == 42


def test_base_model_from_yaml_missing_file(tmp_path: Path) -> None:
    """Test loading BaseModel from non-existent YAML file."""

    class TestModel(compat.BaseModel):
        name: str = "default"
        value: int = 0

    # Should return default instance
    model = TestModel.from_yaml(str(tmp_path / "missing.yaml"))
    assert model.name == "default"
    assert model.value == 0


def test_base_model_from_yaml_empty_file(tmp_path: Path) -> None:
    """Test loading BaseModel from empty YAML file."""

    class TestModel(compat.BaseModel):
        name: str = "default"
        value: int = 0

    yaml_file = tmp_path / "empty.yaml"
    yaml_file.write_text("")

    model = TestModel.from_yaml(str(yaml_file))
    assert model.name == "default"
    assert model.value == 0


def test_settings_base_instantiation() -> None:
    """Test creating a SettingsBase instance."""

    class TestSettings(compat.SettingsBase):
        app_name: str = "test"
        debug: bool = False

    settings = TestSettings()
    assert settings.app_name == "test"
    assert settings.debug is False


def test_settings_base_from_yaml(tmp_path: Path) -> None:
    """Test loading SettingsBase from YAML file."""

    class TestSettings(compat.SettingsBase):
        app_name: str = "default"
        debug: bool = False

    yaml_file = tmp_path / "settings.yaml"
    yaml_file.write_text("app_name: myapp\ndebug: true\n")

    settings = TestSettings.from_yaml(str(yaml_file))
    assert settings.app_name == "myapp"
    assert settings.debug is True


def test_settings_base_from_yaml_missing_file(tmp_path: Path) -> None:
    """Test loading SettingsBase from non-existent YAML file."""

    class TestSettings(compat.SettingsBase):
        app_name: str = "default"
        debug: bool = False

    # Should return default instance
    settings = TestSettings.from_yaml(str(tmp_path / "missing.yaml"))
    assert settings.app_name == "default"
    assert settings.debug is False


def test_field_usage() -> None:
    """Test using Field for field metadata."""

    class TestModel(compat.BaseModel):
        name: str = compat.Field(default="test", description="Name field")
        value: int = compat.Field(default=0, ge=0, le=100)

    model = TestModel()
    assert model.name == "test"
    assert model.value == 0

    # Test validation with Field constraints
    model2 = TestModel(name="custom", value=50)
    assert model2.name == "custom"
    assert model2.value == 50


def test_base_model_arbitrary_types() -> None:
    """Test that arbitrary_types_allowed works."""

    class CustomType:
        def __init__(self, value: Any) -> None:
            self.value = value

    class TestModel(compat.BaseModel):
        custom: CustomType

    custom_obj = CustomType("test")
    model = TestModel(custom=custom_obj)
    assert model.custom.value == "test"


def test_base_model_validate_assignment() -> None:
    """Test that validate_assignment works."""

    class TestModel(compat.BaseModel):
        value: int

    model = TestModel(value=42)
    assert model.value == 42

    # Should validate on assignment
    model.value = 100
    assert model.value == 100

    # Invalid assignment should raise ValidationError
    with pytest.raises(compat.ValidationError):
        model.value = "not an int"  # type: ignore[assignment]


def test_settings_base_extra_ignore() -> None:
    """Test that extra fields are ignored in SettingsBase."""

    class TestSettings(compat.SettingsBase):
        app_name: str = "test"

    # Extra field should be ignored, not cause an error
    settings = TestSettings(app_name="myapp", extra_field="ignored")  # type: ignore[call-arg]
    assert settings.app_name == "myapp"
    # extra_field should not be present
    assert not hasattr(settings, "extra_field")


def test_all_exports() -> None:
    """Test that all expected exports are available."""
    expected = ["BaseModel", "Field", "SettingsBase", "ValidationError", "PYDANTIC_V2"]
    for name in expected:
        assert hasattr(compat, name), f"Missing export: {name}"
        assert name in compat.__all__, f"Missing from __all__: {name}"


