"""
Tests para la configuración de la aplicación (settings.py).

Este módulo contiene tests unitarios para verificar:
- Configuración de versión y constantes
- Rutas de red
- Configuración de actualizaciones
- Funciones de utilidad
"""
import pytest
import os
from pathlib import Path

from app.config.settings import (
    APP_VERSION,
    APP_NAME,
    GITHUB_REPO,
    AUTO_UPDATE_CONFIG,
    NETWORK_BASE,
    NETWORK_PATHS,
    HOMOLOGADOR_FILES,
    IMAP_CONFIG,
    ALLOWED_EXTENSIONS,
    ALL_ALLOWED_EXTENSIONS,
    LOG_CONFIG,
    WINDOW_SIZES,
    is_network_available,
    get_output_dir,
    get_homologador_path,
    ensure_dir,
)


class TestAppInfo:
    """Tests para información de la aplicación."""
    
    def test_app_version_format(self):
        """Versión sigue formato semver"""
        parts = APP_VERSION.split('.')
        assert len(parts) >= 2
        # Major y minor deben ser números
        assert parts[0].isdigit()
        assert parts[1].isdigit()
    
    def test_app_name_defined(self):
        """Nombre de la app está definido"""
        assert APP_NAME == "Glosaap"
    
    def test_github_repo_format(self):
        """Repo de GitHub tiene formato correcto"""
        assert "/" in GITHUB_REPO
        parts = GITHUB_REPO.split("/")
        assert len(parts) == 2
        assert parts[0]  # Owner no vacío
        assert parts[1]  # Repo no vacío


class TestAutoUpdateConfig:
    """Tests para configuración de auto-actualización."""
    
    def test_config_has_required_keys(self):
        """Config tiene todas las claves requeridas"""
        required_keys = [
            "enabled",
            "check_on_startup",
            "check_interval_hours",
            "show_changelog",
            "create_backup"
        ]
        
        for key in required_keys:
            assert key in AUTO_UPDATE_CONFIG
    
    def test_enabled_is_boolean(self):
        """enabled es booleano"""
        assert isinstance(AUTO_UPDATE_CONFIG["enabled"], bool)
    
    def test_check_interval_positive(self):
        """Intervalo de check es positivo"""
        assert AUTO_UPDATE_CONFIG["check_interval_hours"] > 0
    
    def test_check_interval_reasonable(self):
        """Intervalo de check es razonable (< 1 semana)"""
        assert AUTO_UPDATE_CONFIG["check_interval_hours"] <= 168  # 7 días


class TestNetworkPaths:
    """Tests para rutas de red."""
    
    def test_network_base_defined(self):
        """Ruta base de red está definida"""
        assert NETWORK_BASE
        assert isinstance(NETWORK_BASE, str)
    
    def test_network_paths_has_required_keys(self):
        """Paths de red tienen claves requeridas"""
        required = ["homologador", "resultados"]
        
        for key in required:
            assert key in NETWORK_PATHS
    
    def test_homologador_files_defined(self):
        """Archivos de homologación están definidos"""
        assert "mutualser" in HOMOLOGADOR_FILES
        assert "coosalud" in HOMOLOGADOR_FILES
    
    def test_homologador_files_are_xlsx(self):
        """Archivos de homologación son xlsx"""
        for eps, path in HOMOLOGADOR_FILES.items():
            assert path.endswith('.xlsx')


class TestImapConfig:
    """Tests para configuración IMAP."""
    
    def test_default_port_ssl(self):
        """Puerto por defecto es 993 (SSL)"""
        assert IMAP_CONFIG["default_port"] == 993
    
    def test_ssl_enabled(self):
        """SSL está habilitado"""
        assert IMAP_CONFIG["use_ssl"] is True
    
    def test_known_servers_not_empty(self):
        """Lista de servidores conocidos no está vacía"""
        assert len(IMAP_CONFIG["known_servers"]) > 0
    
    def test_gmail_server_correct(self):
        """Servidor Gmail es correcto"""
        assert IMAP_CONFIG["known_servers"]["gmail.com"] == "imap.gmail.com"
    
    def test_outlook_server_correct(self):
        """Servidor Outlook es correcto"""
        assert "office365.com" in IMAP_CONFIG["known_servers"]["outlook.com"]


class TestAllowedExtensions:
    """Tests para extensiones permitidas."""
    
    def test_excel_extensions_defined(self):
        """Extensiones Excel están definidas"""
        assert "excel" in ALLOWED_EXTENSIONS
        assert '.xlsx' in ALLOWED_EXTENSIONS["excel"]
        assert '.xls' in ALLOWED_EXTENSIONS["excel"]
    
    def test_word_extensions_defined(self):
        """Extensiones Word están definidas"""
        assert "word" in ALLOWED_EXTENSIONS
        assert '.docx' in ALLOWED_EXTENSIONS["word"]
    
    def test_pdf_extension_defined(self):
        """Extensión PDF está definida"""
        assert "pdf" in ALLOWED_EXTENSIONS
        assert '.pdf' in ALLOWED_EXTENSIONS["pdf"]
    
    def test_all_extensions_combined(self):
        """ALL_ALLOWED_EXTENSIONS combina todas"""
        assert '.xlsx' in ALL_ALLOWED_EXTENSIONS
        assert '.pdf' in ALL_ALLOWED_EXTENSIONS
        assert '.docx' in ALL_ALLOWED_EXTENSIONS


class TestLogConfig:
    """Tests para configuración de logging."""
    
    def test_log_level_defined(self):
        """Nivel de log está definido"""
        import logging
        assert LOG_CONFIG["level"] in [
            logging.DEBUG, logging.INFO, 
            logging.WARNING, logging.ERROR
        ]
    
    def test_log_format_defined(self):
        """Formato de log está definido"""
        assert LOG_CONFIG["format"]
        assert "%(asctime)s" in LOG_CONFIG["format"]
    
    def test_log_file_path_valid(self):
        """Ruta de archivo de log es válida"""
        assert LOG_CONFIG["file"]


class TestWindowSizes:
    """Tests para tamaños de ventana."""
    
    def test_login_size_defined(self):
        """Tamaño de login está definido"""
        assert "login" in WINDOW_SIZES
        assert "width" in WINDOW_SIZES["login"]
        assert "height" in WINDOW_SIZES["login"]
    
    def test_sizes_are_positive(self):
        """Tamaños son positivos"""
        for view, size in WINDOW_SIZES.items():
            assert size["width"] > 0
            assert size["height"] > 0
    
    def test_sizes_are_reasonable(self):
        """Tamaños son razonables (< 4K)"""
        for view, size in WINDOW_SIZES.items():
            assert size["width"] <= 3840
            assert size["height"] <= 2160


class TestUtilityFunctions:
    """Tests para funciones de utilidad."""
    
    def test_get_output_dir_mutualser(self):
        """Obtiene directorio de salida para Mutualser"""
        result = get_output_dir("mutualser")
        assert result
        assert "MUTUALSER" in result.upper() or "mutualser" in result.lower()
    
    def test_get_output_dir_coosalud(self):
        """Obtiene directorio de salida para Coosalud"""
        result = get_output_dir("coosalud")
        assert result
        assert "COOSALUD" in result.upper() or "coosalud" in result.lower()
    
    def test_get_output_dir_unknown(self):
        """Directorio para EPS desconocida usa temp"""
        result = get_output_dir("eps_desconocida")
        assert result
        # Debería usar directorio temporal
    
    def test_get_homologador_path_mutualser(self):
        """Obtiene ruta de homologador para Mutualser"""
        result = get_homologador_path("mutualser")
        assert result
        assert result.endswith('.xlsx')
        assert "mutualser" in result.lower()
    
    def test_get_homologador_path_coosalud(self):
        """Obtiene ruta de homologador para Coosalud"""
        result = get_homologador_path("coosalud")
        assert result
        assert result.endswith('.xlsx')
        assert "coosalud" in result.lower()
    
    def test_ensure_dir_creates_directory(self, tmp_path):
        """ensure_dir crea directorio"""
        new_dir = tmp_path / "new_directory"
        result = ensure_dir(str(new_dir))
        
        assert result is True
        assert new_dir.exists()
    
    def test_ensure_dir_existing_directory(self, tmp_path):
        """ensure_dir no falla con directorio existente"""
        result = ensure_dir(str(tmp_path))
        
        assert result is True
    
    def test_is_network_available_returns_bool(self):
        """is_network_available retorna booleano"""
        result = is_network_available()
        assert isinstance(result, bool)


class TestProjectRoot:
    """Tests para rutas del proyecto."""
    
    def test_project_root_exists(self):
        """PROJECT_ROOT existe"""
        from app.config.settings import PROJECT_ROOT
        assert PROJECT_ROOT.exists()
    
    def test_assets_dir_valid(self):
        """ASSETS_DIR es válido"""
        from app.config.settings import ASSETS_DIR
        assert ASSETS_DIR
        # Puede no existir en tests, pero la ruta debe ser válida
