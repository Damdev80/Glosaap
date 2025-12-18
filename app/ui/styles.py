"""
Estilos centralizados para la UI de Flet
"""

# Colores del tema - Paleta profesional
COLORS = {
    # Primarios
    "primary": "#2563EB",
    "primary_dark": "#1E40AF",
    "primary_light": "#DBEAFE",
    "primary_hover": "#1D4ED8",
    
    # Estados
    "success": "#10B981",
    "success_light": "#D1FAE5",
    "error": "#EF4444",
    "error_light": "#FEE2E2",
    "warning": "#F59E0B",
    "warning_light": "#FEF3C7",
    "info": "#3B82F6",
    "info_light": "#DBEAFE",
    
    # Textos
    "text_primary": "#1F2937",
    "text_secondary": "#6B7280",
    "text_light": "#9CA3AF",
    "text_muted": "#D1D5DB",
    
    # Fondos
    "bg_white": "#FFFFFF",
    "bg_light": "#F9FAFB",
    "bg_input": "#F3F4F6",
    "bg_dark": "#111827",
    
    # Bordes
    "border": "#D1D5DB",
    "border_light": "#E5E7EB",
    "border_focus": "#2563EB",
    
    # Hover
    "hover": "#F3F4F6",
    "hover_primary": "#1D4ED8",
}

# Tamaños de fuente
FONT_SIZES = {
    "title": 36,
    "heading": 22,
    "subheading": 18,
    "body": 14,
    "small": 13,
    "caption": 11,
    "button": 15,
}

# Espaciados
SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 16,
    "lg": 24,
    "xl": 32,
    "xxl": 48,
}

# Dimensiones de ventana
WINDOW_SIZES = {
    "login": {"width": 480, "height": 520},
    "main": {"width": 950, "height": 720},
}

# Sombras reutilizables
def get_shadow(intensity: str = "md"):
    """Retorna una sombra según la intensidad"""
    shadows = {
        "sm": {"blur": 4, "spread": 0, "opacity": 0.1},
        "md": {"blur": 12, "spread": 0, "opacity": 0.15},
        "lg": {"blur": 24, "spread": 0, "opacity": 0.2},
    }
    s = shadows.get(intensity, shadows["md"])
    return {
        "blur_radius": s["blur"],
        "spread_radius": s["spread"],
        "opacity": s["opacity"],
    }

# Estilos de botones
BUTTON_STYLES = {
    "primary": {
        "bgcolor": COLORS["primary"],
        "color": COLORS["bg_white"],
        "hover": COLORS["primary_hover"],
    },
    "success": {
        "bgcolor": COLORS["success"],
        "color": COLORS["bg_white"],
        "hover": "#059669",
    },
    "outline": {
        "bgcolor": "transparent",
        "color": COLORS["primary"],
        "border": COLORS["primary"],
    },
}
