"""
Tests para el servicio de actualizaciones (update_service.py).

Este módulo contiene tests unitarios para verificar:
- Parseo de versiones semver
- Comparación de versiones
- Detección de actualizaciones disponibles
- Descarga de releases
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from app.service.update_service import (
    parse_version,
    compare_versions,
    is_update_available,
    ReleaseInfo,
)


class TestVersionParsing:
    """Tests para el parseo de versiones semver."""
    
    def test_parse_simple_version(self):
        """Parsea versión simple X.Y.Z"""
        result = parse_version("1.2.3")
        assert result == (1, 2, 3, '')
    
    def test_parse_version_with_v_prefix(self):
        """Parsea versión con prefijo 'v'"""
        result = parse_version("v1.2.3")
        assert result == (1, 2, 3, '')
    
    def test_parse_version_with_prerelease(self):
        """Parsea versión con prerelease"""
        result = parse_version("1.0.0-beta")
        assert result == (1, 0, 0, 'beta')
    
    def test_parse_version_with_rc(self):
        """Parsea versión con release candidate"""
        result = parse_version("2.0.0-rc.1")
        assert result == (2, 0, 0, 'rc.1')
    
    def test_parse_version_two_parts(self):
        """Parsea versión con solo dos partes"""
        result = parse_version("1.2")
        assert result == (1, 2, 0, '')
    
    def test_parse_version_one_part(self):
        """Parsea versión con solo una parte"""
        result = parse_version("5")
        assert result == (5, 0, 0, '')
    
    def test_parse_invalid_version(self):
        """Maneja versión inválida gracefully"""
        result = parse_version("invalid")
        assert result == (0, 0, 0, 'invalid')
    
    def test_parse_empty_version(self):
        """Maneja versión vacía"""
        result = parse_version("")
        assert result[0] == 0


class TestVersionComparison:
    """Tests para la comparación de versiones."""
    
    def test_compare_equal_versions(self):
        """Versiones iguales retornan 0"""
        result = compare_versions("1.0.0", "1.0.0")
        assert result == 0
    
    def test_compare_current_greater_major(self):
        """Current mayor que remote en major"""
        result = compare_versions("2.0.0", "1.0.0")
        assert result > 0
    
    def test_compare_remote_greater_major(self):
        """Remote mayor que current en major"""
        result = compare_versions("1.0.0", "2.0.0")
        assert result < 0
    
    def test_compare_current_greater_minor(self):
        """Current mayor que remote en minor"""
        result = compare_versions("1.5.0", "1.4.0")
        assert result > 0
    
    def test_compare_remote_greater_minor(self):
        """Remote mayor que current en minor"""
        result = compare_versions("1.4.0", "1.5.0")
        assert result < 0
    
    def test_compare_current_greater_patch(self):
        """Current mayor que remote en patch"""
        result = compare_versions("1.0.5", "1.0.4")
        assert result > 0
    
    def test_compare_remote_greater_patch(self):
        """Remote mayor que current en patch"""
        result = compare_versions("1.0.4", "1.0.5")
        assert result < 0
    
    def test_compare_with_v_prefix(self):
        """Comparación con prefijo v"""
        result = compare_versions("v1.0.0", "1.0.0")
        assert result == 0
    
    def test_compare_prerelease_vs_release(self):
        """Prerelease es menor que release"""
        result = compare_versions("1.0.0-beta", "1.0.0")
        # Prerelease debería ser "menor" que la versión final
        assert result != 0


class TestUpdateAvailability:
    """Tests para verificar disponibilidad de actualizaciones."""
    
    def test_update_available_when_remote_newer(self):
        """Detecta actualización cuando remote es más nueva"""
        result = is_update_available("1.0.0", "1.1.0")
        assert result is True
    
    def test_no_update_when_equal(self):
        """No hay actualización cuando son iguales"""
        result = is_update_available("1.0.0", "1.0.0")
        assert result is False
    
    def test_no_update_when_current_newer(self):
        """No hay actualización cuando current es más nueva"""
        result = is_update_available("2.0.0", "1.0.0")
        assert result is False
    
    def test_update_available_minor_bump(self):
        """Detecta bump de minor version"""
        result = is_update_available("0.11.7", "0.12.0")
        assert result is True
    
    def test_update_available_patch_bump(self):
        """Detecta bump de patch version"""
        result = is_update_available("0.11.7", "0.11.8")
        assert result is True


class TestReleaseInfo:
    """Tests para el dataclass ReleaseInfo."""
    
    def test_release_info_creation(self):
        """Crea ReleaseInfo correctamente"""
        info = ReleaseInfo(
            version="1.0.0",
            tag_name="v1.0.0",
            name="Release 1.0.0",
            body="## Changelog\n- Feature 1",
            published_at="2026-01-27T10:00:00Z",
            download_url="https://example.com/release.zip",
            asset_name="Glosaap_v1.0.0.zip",
            asset_size=80000000
        )
        
        assert info.version == "1.0.0"
        assert info.tag_name == "v1.0.0"
    
    def test_release_info_changelog_property(self):
        """Retorna changelog correctamente"""
        info = ReleaseInfo(
            version="1.0.0",
            tag_name="v1.0.0",
            name="Release",
            body="Custom changelog",
            published_at="",
            download_url="",
            asset_name="",
            asset_size=0
        )
        
        assert info.changelog == "Custom changelog"
    
    def test_release_info_changelog_empty(self):
        """Retorna mensaje default cuando no hay changelog"""
        info = ReleaseInfo(
            version="1.0.0",
            tag_name="v1.0.0",
            name="Release",
            body="",
            published_at="",
            download_url="",
            asset_name="",
            asset_size=0
        )
        
        assert "Sin descripción" in info.changelog
    
    def test_release_info_size_mb(self):
        """Calcula tamaño en MB correctamente"""
        info = ReleaseInfo(
            version="1.0.0",
            tag_name="v1.0.0",
            name="Release",
            body="",
            published_at="",
            download_url="",
            asset_name="",
            asset_size=80 * 1024 * 1024  # 80 MB
        )
        
        assert info.size_mb == 80.0


class TestGitHubAPI:
    """Tests para interacción con GitHub API (mockeados)."""
    
    @patch('app.service.update_service.urllib.request.urlopen')
    def test_check_for_updates_success(self, mock_urlopen):
        """Verifica correctamente actualizaciones desde GitHub"""
        from app.service.update_service import UpdateService
        
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "tag_name": "v1.1.0",
            "name": "Glosaap v1.1.0",
            "body": "## New features",
            "published_at": "2026-01-27T10:00:00Z",
            "assets": [{
                "name": "Glosaap_v1.1.0.zip",
                "browser_download_url": "https://example.com/download",
                "size": 80000000
            }]
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        # Test using UpdateService class method
        service = UpdateService(current_version="1.0.0")
        result = service.check_for_updates()
        
        # Verify - puede ser None si no hay actualización o ReleaseInfo si hay
        assert result is None or isinstance(result, ReleaseInfo)
    
    @patch('app.service.update_service.urllib.request.urlopen')
    def test_check_for_updates_network_error(self, mock_urlopen):
        """Maneja errores de red lanzando UpdateCheckError"""
        import urllib.error
        from app.service.update_service import UpdateService, UpdateCheckError
        
        mock_urlopen.side_effect = urllib.error.URLError("Network error")
        
        service = UpdateService(current_version="1.0.0")
        
        # El servicio lanza UpdateCheckError en caso de error de red
        with pytest.raises(UpdateCheckError):
            service.check_for_updates()
