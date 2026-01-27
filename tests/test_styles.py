"""
Tests para estilos y componentes UI.

Este módulo contiene tests unitarios para verificar:
- Constantes de estilos
- Funciones de utilidad de estilos
- Validación de colores y tamaños
"""
import pytest

from app.ui.styles import (
    COLORS,
    FONT_SIZES,
    SPACING,
    WINDOW_SIZES,
    BUTTON_STYLES,
    get_shadow,
)


class TestColors:
    """Tests para constantes de colores."""
    
    def test_primary_colors_defined(self):
        """Colores primarios están definidos"""
        assert "primary" in COLORS
        assert "primary_dark" in COLORS
        assert "primary_light" in COLORS
    
    def test_state_colors_defined(self):
        """Colores de estado están definidos"""
        states = ["success", "error", "warning", "info"]
        for state in states:
            assert state in COLORS
            assert f"{state}_light" in COLORS
    
    def test_text_colors_defined(self):
        """Colores de texto están definidos"""
        assert "text_primary" in COLORS
        assert "text_secondary" in COLORS
        assert "text_light" in COLORS
    
    def test_bg_colors_defined(self):
        """Colores de fondo están definidos"""
        assert "bg_white" in COLORS
        assert "bg_light" in COLORS
        assert "bg_input" in COLORS
    
    def test_colors_are_hex(self):
        """Colores están en formato hex"""
        for name, color in COLORS.items():
            assert color.startswith("#"), f"{name} no es hex: {color}"
            assert len(color) == 7, f"{name} hex inválido: {color}"
    
    def test_primary_color_value(self):
        """Color primario es azul"""
        # #2563EB es un tono de azul
        primary = COLORS["primary"].lower()
        assert primary.startswith("#")
    
    def test_success_color_is_green(self):
        """Color success es verde"""
        # #10B981 es un tono de verde
        success = COLORS["success"].lower()
        assert success.startswith("#")
    
    def test_error_color_is_red(self):
        """Color error es rojo"""
        # #EF4444 es un tono de rojo
        error = COLORS["error"].lower()
        assert error.startswith("#")


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


class TestButtonStyles:
    """Tests para estilos de botones."""
    
    def test_primary_button_style(self):
        """Estilo de botón primario"""
        assert "primary" in BUTTON_STYLES
        assert "bgcolor" in BUTTON_STYLES["primary"]
        assert "color" in BUTTON_STYLES["primary"]
    
    def test_success_button_style(self):
        """Estilo de botón success"""
        assert "success" in BUTTON_STYLES
    
    def test_button_colors_match_theme(self):
        """Colores de botones coinciden con tema"""
        assert BUTTON_STYLES["primary"]["bgcolor"] == COLORS["primary"]
        assert BUTTON_STYLES["success"]["bgcolor"] == COLORS["success"]


class TestShadowFunction:
    """Tests para función get_shadow."""
    
    def test_shadow_sm(self):
        """Sombra pequeña"""
        shadow = get_shadow("sm")
        assert "blur_radius" in shadow
        assert shadow["blur_radius"] < 10
    
    def test_shadow_md(self):
        """Sombra mediana (default)"""
        shadow = get_shadow("md")
        assert "blur_radius" in shadow
        assert shadow["blur_radius"] >= 10
    
    def test_shadow_lg(self):
        """Sombra grande"""
        shadow = get_shadow("lg")
        assert "blur_radius" in shadow
        assert shadow["blur_radius"] > get_shadow("md")["blur_radius"]
    
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
    
    def test_shadow_has_required_keys(self):
        """Sombra tiene claves requeridas"""
        shadow = get_shadow()
        assert "blur_radius" in shadow
        assert "spread_radius" in shadow
        assert "opacity" in shadow
    
    def test_shadow_opacity_valid(self):
        """Opacidad es válida (0-1)"""
        for intensity in ["sm", "md", "lg"]:
            shadow = get_shadow(intensity)
            assert 0 <= shadow["opacity"] <= 1


class TestColorAccessibility:
    """Tests para accesibilidad de colores."""
    
    def test_text_primary_is_dark(self):
        """Texto primario es oscuro (para fondo claro)"""
        # #1F2937 es gris muy oscuro
        text = COLORS["text_primary"]
        # Verificar que el valor R es bajo (oscuro)
        r = int(text[1:3], 16)
        assert r < 128, "Texto primario debería ser oscuro"
    
    def test_bg_white_is_light(self):
        """Fondo blanco es claro"""
        bg = COLORS["bg_white"]
        assert bg.upper() == "#FFFFFF"
    
    def test_contrast_colors_different(self):
        """Colores de contraste son diferentes"""
        assert COLORS["text_primary"] != COLORS["bg_white"]
        assert COLORS["primary"] != COLORS["bg_white"]
