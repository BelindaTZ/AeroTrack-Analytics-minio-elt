"""Tests unitarios para configuración de la aplicación."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestConfigImports:
    def test_config_module_imports(self):
        from app import config
        assert hasattr(config, "MINIO_ENDPOINT")
        assert hasattr(config, "PB_URL")
        assert hasattr(config, "SECRET_KEY")
        assert hasattr(config, "ALGORITHM")
        assert hasattr(config, "ACCESS_TOKEN_EXPIRE_MINUTES")

    def test_docker_detection(self):
        from app import config
        assert isinstance(config.IN_DOCKER, bool)

    def test_algorithm_default(self):
        from app import config
        assert config.ALGORITHM == "HS256"

    def test_token_expire_is_int(self):
        from app import config
        assert isinstance(config.ACCESS_TOKEN_EXPIRE_MINUTES, int)
        assert config.ACCESS_TOKEN_EXPIRE_MINUTES > 0
