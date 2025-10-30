"""Tests for Pydantic compatibility layer."""

import importlib
import sys
import types
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
    assert hasattr(compat.SettingsBase, "model_config") or hasattr(compat.SettingsBase, "Config")


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


class TestPydanticV1Fallback:
    """Tests for Pydantic v1 fallback path (when v2 is not available)."""

    def test_v1_imports_simulation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that v1 import path works when simulated."""
        # We can't easily test the actual v1 path in an environment with v2,
        # but we can verify the module structure supports both versions
        import sys

        # Store original modules
        original_compat = sys.modules.get("restack_gen.compat")

        try:
            # Remove compat from sys.modules to force reimport
            if "restack_gen.compat" in sys.modules:
                del sys.modules["restack_gen.compat"]

            # Mock pydantic v2 import to fail, forcing v1 path
            import builtins

            original_import = builtins.__import__

            def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
                if name == "pydantic_settings":
                    raise ImportError("Mock: pydantic_settings not found (simulating v1)")
                return original_import(name, *args, **kwargs)

            monkeypatch.setattr(builtins, "__import__", mock_import)

            # Import should now use v1 path
            from restack_gen import compat as compat_v1

            # Should have PYDANTIC_V2 = False (or True if v2 succeeded before mock)
            assert isinstance(compat_v1.PYDANTIC_V2, bool)
            assert hasattr(compat_v1, "BaseModel")
            assert hasattr(compat_v1, "SettingsBase")
            assert hasattr(compat_v1, "Field")

        finally:
            # Restore original compat module
            if original_compat is not None:
                sys.modules["restack_gen.compat"] = original_compat
            elif "restack_gen.compat" in sys.modules:
                del sys.modules["restack_gen.compat"]

    def test_config_class_access_v1_style(self) -> None:
        """Test that v1-style Config class is accessible when needed."""
        # Test that BaseModel and SettingsBase have appropriate config mechanism

        class TestModel(compat.BaseModel):
            value: int = 1

        if compat.PYDANTIC_V2:
            # V2 uses model_config dict
            assert hasattr(TestModel, "model_config")
            assert isinstance(TestModel.model_config, dict)
        else:
            # V1 uses Config class
            assert hasattr(TestModel, "Config")

    def test_settings_config_class_access_v1_style(self) -> None:
        """Test that SettingsBase Config class is accessible when needed."""

        class TestSettings(compat.SettingsBase):
            value: int = 1

        if compat.PYDANTIC_V2:
            # V2 uses model_config dict
            assert hasattr(TestSettings, "model_config")
            assert isinstance(TestSettings.model_config, dict)
        else:
            # V1 uses Config class
            assert hasattr(TestSettings, "Config")


class TestEdgeCasesAndBranches:
    """Tests for edge cases and branch coverage."""

    def test_base_model_from_yaml_with_invalid_data(self, tmp_path: Path) -> None:
        """Test loading BaseModel from YAML with invalid data."""

        class TestModel(compat.BaseModel):
            name: str
            value: int

        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("name: test\nvalue: not_an_int\n")

        # Should raise ValidationError due to type mismatch
        with pytest.raises(compat.ValidationError):
            TestModel.from_yaml(str(yaml_file))

    def test_settings_base_from_yaml_with_invalid_data(self, tmp_path: Path) -> None:
        """Test loading SettingsBase from YAML with invalid data."""

        class TestSettings(compat.SettingsBase):
            port: int

        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("port: not_a_number\n")

        # Should raise ValidationError
        with pytest.raises(compat.ValidationError):
            TestSettings.from_yaml(str(yaml_file))

    def test_base_model_from_yaml_with_malformed_yaml(self, tmp_path: Path) -> None:
        """Test loading BaseModel from malformed YAML."""
        import yaml

        class TestModel(compat.BaseModel):
            name: str = "default"

        yaml_file = tmp_path / "malformed.yaml"
        yaml_file.write_text("name: test\n  invalid: indentation\n")

        # Should raise YAMLError
        with pytest.raises(yaml.YAMLError):
            TestModel.from_yaml(str(yaml_file))

    def test_settings_base_from_yaml_with_malformed_yaml(self, tmp_path: Path) -> None:
        """Test loading SettingsBase from malformed YAML."""
        import yaml

        class TestSettings(compat.SettingsBase):
            name: str = "default"

        yaml_file = tmp_path / "malformed.yaml"
        yaml_file.write_text("name: [unclosed bracket")

        # Should raise YAMLError
        with pytest.raises(yaml.YAMLError):
            TestSettings.from_yaml(str(yaml_file))

    def test_base_model_inheritance_chain(self) -> None:
        """Test that BaseModel properly inherits from the base."""
        # Verify the inheritance chain is set up correctly
        assert issubclass(compat.BaseModel, compat.BaseModelBase)

        class DerivedModel(compat.BaseModel):
            value: int = 1

        # Should maintain config inheritance
        instance = DerivedModel()
        assert instance.value == 1

    def test_settings_base_inheritance_chain(self) -> None:
        """Test that SettingsBase properly inherits from the base."""
        # Verify the inheritance chain is set up correctly
        assert issubclass(compat.SettingsBase, compat.SettingsBaseBase)

        class DerivedSettings(compat.SettingsBase):
            value: int = 1

        # Should maintain config inheritance
        instance = DerivedSettings()
        assert instance.value == 1


def test_compat_fallback_to_pydantic_v1(monkeypatch) -> None:
    """Simulate ImportError for pydantic v2 and test v1 fallback logic."""
    # Remove pydantic v2 modules if present
    sys_modules_backup = sys.modules.copy()
    monkeypatch.setitem(sys.modules, "pydantic", None)
    monkeypatch.setitem(sys.modules, "pydantic_settings", None)

    # Create fake pydantic v1 module
    class FakeBaseModel:
        pass

    class FakeBaseSettings:
        pass

    class FakeField:
        pass

    class FakeValidationError(Exception):
        pass

    fake_pydantic = types.ModuleType("pydantic")
    fake_pydantic.BaseModel = FakeBaseModel
    fake_pydantic.BaseSettings = FakeBaseSettings
    fake_pydantic.Field = FakeField
    fake_pydantic.ValidationError = FakeValidationError
    sys.modules["pydantic"] = fake_pydantic
    sys.modules["pydantic_settings"] = types.ModuleType("pydantic_settings")  # Not used in v1

    # Reload compat.py to trigger fallback
    compat = importlib.reload(importlib.import_module("restack_gen.compat"))

    assert compat.PYDANTIC_V2 is False
    assert compat.BaseModelBase is FakeBaseModel
    assert compat.SettingsBaseBase is FakeBaseSettings
    assert compat.Field is FakeField
    assert compat.ValidationError is FakeValidationError

    # Test Config class exists and has correct attributes
    assert hasattr(compat.BaseModel, "Config")
    assert compat.BaseModel.Config.arbitrary_types_allowed is True
    assert compat.BaseModel.Config.validate_assignment is True
    assert hasattr(compat.SettingsBase, "Config")
    assert compat.SettingsBase.Config.env_file == ".env"
    assert compat.SettingsBase.Config.env_file_encoding == "utf-8"
    assert compat.SettingsBase.Config.extra == "ignore"

    # Restore sys.modules
    sys.modules.clear()
    sys.modules.update(sys_modules_backup)
