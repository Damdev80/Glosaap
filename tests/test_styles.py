"""
Tests para estilos y componentes UI.

Este módulo contiene tests unitarios para verificar:
- Constantes de estilos
- Funciones de utilidad de estilos
- Validación de colores y tamaños
"""
import pytest

from app.ui.styles import (
    FONT_SIZES,
    SPACING,
    WINDOW_SIZES,
    get_shadow,
)


# NOTE: TestColors fue removido - COLORS ya no existe
# Se usan ft.Colors.* para acceso a colores tema-aware

class TestFontSizes:
    """Tests para tamaños de fuente."""
    
    def test_font_sizes_defined(self):
        """Tamaños de fuente están definidos"""
        required = ["title", "heading", "body", "small", "caption", "button"]
        for size in required:
            assert size in FONT_SIZES
    
    def test_font_sizes_are_numbers(self):
        """Tamaños de fuente son números"""
        for name, size in FONT_SIZES.items():
            assert isinstance(size, (int, float))
            assert size > 0
    
    def test_title_is_largest(self):
        """Title es el tamaño más grande"""
        assert FONT_SIZES["title"] > FONT_SIZES["heading"]
        assert FONT_SIZES["title"] > FONT_SIZES["body"]
    
    def test_caption_is_smallest(self):
        """Caption es el tamaño más pequeño"""
        assert FONT_SIZES["caption"] < FONT_SIZES["body"]
        assert FONT_SIZES["caption"] < FONT_SIZES["small"]
    
    def test_hierarchy_order(self):
        """Jerarquía de tamaños es correcta"""
        assert FONT_SIZES["title"] > FONT_SIZES["heading"]
        assert FONT_SIZES["heading"] > FONT_SIZES["subheading"]
        assert FONT_SIZES["subheading"] > FONT_SIZES["body"]
        assert FONT_SIZES["body"] >= FONT_SIZES["small"]


class TestSpacing:
    """Tests para espaciados."""
    
    def test_spacing_defined(self):
        """Espaciados están definidos"""
        required = ["xs", "sm", "md", "lg", "xl"]
        for size in required:
            assert size in SPACING
    
    def test_spacing_are_numbers(self):
        """Espaciados son números"""
        for name, size in SPACING.items():
            assert isinstance(size, (int, float))
            assert size >= 0
    
    def test_spacing_hierarchy(self):
        """Jerarquía de espaciados es correcta"""
        assert SPACING["xs"] < SPACING["sm"]
        assert SPACING["sm"] < SPACING["md"]
        assert SPACING["md"] < SPACING["lg"]
        assert SPACING["lg"] < SPACING["xl"]
    
    def test_spacing_reasonable_values(self):
        """Espaciados tienen valores razonables"""
        assert SPACING["xs"] <= 8
        assert SPACING["sm"] <= 16
        assert SPACING["md"] <= 24
        assert SPACING["lg"] <= 32
        assert SPACING["xl"] <= 48


class TestWindowSizes:
    """Tests para tamaños de ventana."""
    
    def test_login_window_size(self):
        """Tamaño de ventana de login"""
        assert "login" in WINDOW_SIZES
        assert WINDOW_SIZES["login"]["width"] > 0
        assert WINDOW_SIZES["login"]["height"] > 0
    
    def test_main_window_size(self):
        """Tamaño de ventana principal"""
        assert "main" in WINDOW_SIZES
        assert WINDOW_SIZES["main"]["width"] > 0
        assert WINDOW_SIZES["main"]["height"] > 0
    
    def test_main_larger_than_login(self):
        """Ventana principal es más grande que login"""
        assert WINDOW_SIZES["main"]["width"] > WINDOW_SIZES["login"]["width"]
        assert WINDOW_SIZES["main"]["height"] >= WINDOW_SIZES["login"]["height"]


# NOTE: TestButtonStyles fue removido - BUTTON_STYLES y COLORS ya no existen
# Se usan ft.Colors.* y ft.ButtonStyle en su lugar


class TestShadowFunction:
    """Tests para función get_shadow."""
    
    def test_shadow_sm(self):
        """Sombra pequeña"""
        shadow = get_shadow("sm")
        assert shadow is not None
        assert hasattr(shadow, 'blur_radius')
    
    def test_shadow_md(self):
        """Sombra mediana (default)"""
        shadow = get_shadow("md")
        assert shadow is not None
        assert hasattr(shadow, 'blur_radius')
    
    def test_shadow_lg(self):
        """Sombra grande"""
        shadow = get_shadow("lg")
        assert shadow is not None
        assert hasattr(shadow, 'blur_radius')
    
    def test_shadow_default(self):
        """Sombra por defecto es md"""
        default = get_shadow()
        md = get_shadow("md")
        assert default == md
    
    def test_shadow_invalid_uses_default(self):
        """Intensidad inválida usa default"""
        invalid = get_shadow("invalid")
        md = get_shadow("md")
        assert invalid == md
    
    def test_shadow_has_required_attributes(self):
        """Sombra tiene atributos requeridos"""
        shadow = get_shadow()
        assert hasattr(shadow, 'blur_radius')
        assert hasattr(shadow, 'spread_radius')
        assert hasattr(shadow, 'color')


# NOTE: TestColorAccessibility fue removido - COLORS ya no existe
# Se usan ft.Colors.* para acceso a colores tema-aware
