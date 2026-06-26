"""Tests unitarios para dependencias RBAC."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.shared.deps import has_permission


class TestHasPermission:
    def test_permission_present(self):
        perms = {"seguridad": ["ver", "editar"], "dashboard": ["ver"]}
        assert has_permission(perms, "seguridad", "ver") is True

    def test_permission_absent(self):
        perms = {"seguridad": ["ver"]}
        assert has_permission(perms, "seguridad", "editar") is False

    def test_module_absent(self):
        perms = {"dashboard": ["ver"]}
        assert has_permission(perms, "seguridad", "ver") is False

    def test_empty_permissions(self):
        assert has_permission({}, "seguridad", "ver") is False

    def test_permission_multiple_actions(self):
        perms = {"reportes": ["ver", "exportar", "crear"]}
        assert has_permission(perms, "reportes", "exportar") is True
        assert has_permission(perms, "reportes", "eliminar") is False
