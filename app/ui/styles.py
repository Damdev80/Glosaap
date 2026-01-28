"""
Estilos centralizados para la UI de Flet
Sistema de temas con soporte Light/Dark usando Flet nativo
"""
import flet as ft


class ThemeManager:
    """Administrador de temas para la aplicación usando Flet nativo"""
    
    _page = None
    _is_dark = False
    _rebuild_callback = None
    
    @classmethod
    def init(cls, page: ft.Page, rebuild_callback=None):
        """Inicializa el ThemeManager con la página"""
        cls._page = page
        cls._rebuild_callback = rebuild_callback
        
        # Cargar tema guardado
        try:
            saved_theme = page.client_storage.get("app_theme")
            cls._is_dark = saved_theme == "dark"
        except:
            cls._is_dark = False
        
        cls._apply_flet_theme()
    
    @classmethod
    def _apply_flet_theme(cls):
        """Aplica el tema usando el sistema nativo de Flet"""
        if cls._page:
            # Configurar tema de Flet
            if cls._is_dark:
                cls._page.theme_mode = ft.ThemeMode.DARK
                cls._page.bgcolor = "#0d1117"
                # Tema oscuro personalizado - Colores vibrantes
                cls._page.dark_theme = ft.Theme(
                    color_scheme_seed=ft.Colors.BLUE,
                    color_scheme=ft.ColorScheme(
                        primary="#3b82f6",
                        on_primary="#ffffff",
                        primary_container="#1e3a5f",
                        on_primary_container="#bfdbfe",
                        secondary="#8b5cf6",
                        on_secondary="#ffffff",
                        surface="#161b22",
                        surface_variant="#21262d",
                        on_surface="#e6edf3",
                        on_surface_variant="#8b949e",
                        background="#0d1117",
                        on_background="#e6edf3",
                        outline="#30363d",
                        outline_variant="#21262d",
                        error="#f87171",
                        on_error="#ffffff",
                    )
                )
            else:
                cls._page.theme_mode = ft.ThemeMode.LIGHT
                cls._page.bgcolor = "#f6f8fa"
                # Tema claro personalizado - Profesional y limpio
                cls._page.theme = ft.Theme(
                    color_scheme_seed=ft.Colors.BLUE,
                    color_scheme=ft.ColorScheme(
                        primary="#2563eb",
                        on_primary="#ffffff",
                        primary_container="#dbeafe",
                        on_primary_container="#1e40af",
                        secondary="#7c3aed",
                        on_secondary="#ffffff",
                        surface="#ffffff",
                        surface_variant="#f1f5f9",
                        on_surface="#1e293b",
                        on_surface_variant="#64748b",
                        background="#f6f8fa",
                        on_background="#1e293b",
                        outline="#cbd5e1",
                        outline_variant="#e2e8f0",
                        error="#dc2626",
                        on_error="#ffffff",
                    )
                )
    
    @classmethod
    def toggle_theme(cls):
        """Alterna entre tema claro y oscuro"""
        cls._is_dark = not cls._is_dark
        
        if cls._page:
            # Guardar preferencia
            try:
                cls._page.client_storage.set("app_theme", "dark" if cls._is_dark else "light")
            except:
                pass
            
            cls._apply_flet_theme()
            
            # Llamar callback para reconstruir UI
            if cls._rebuild_callback:
                cls._rebuild_callback()
            
            cls._page.update()
        
        return cls._is_dark
    
    @classmethod
    def is_dark(cls) -> bool:
        """Retorna True si el tema actual es oscuro"""
        return cls._is_dark
    
    @classmethod
    def get_colors(cls) -> dict:
        """Retorna colores según el tema actual"""
        if cls._is_dark:
            return DARK_COLORS
        return LIGHT_COLORS


# ==================== PALETAS DE COLORES ====================

LIGHT_COLORS = {
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
    "bg_card": "#FFFFFF",
    "bg_surface": "#F9FAFB",
    "bg_page": "#F3F4F6",
    
    # Bordes
    "border": "#D1D5DB",
    "border_light": "#E5E7EB",
    "border_focus": "#2563EB",
    
    # Hover
    "hover": "#F3F4F6",
    "hover_primary": "#1D4ED8",
    
    # Sombras
    "shadow_color": "#000000",
    "shadow_opacity": 0.08,
}

DARK_COLORS = {
    # Primarios
    "primary": "#60A5FA",
    "primary_dark": "#3B82F6",
    "primary_light": "#1E3A5F",
    "primary_hover": "#93C5FD",
    
    # Estados
    "success": "#34D399",
    "success_light": "#064E3B",
    "error": "#F87171",
    "error_light": "#7F1D1D",
    "warning": "#FBBF24",
    "warning_light": "#78350F",
    "info": "#60A5FA",
    "info_light": "#1E3A5F",
    
    # Textos
    "text_primary": "#F9FAFB",
    "text_secondary": "#E5E7EB",
    "text_light": "#9CA3AF",
    "text_muted": "#6B7280",
    
    # Fondos - OSCUROS REALES
    "bg_white": "#1a1a2e",
    "bg_light": "#16213e",
    "bg_input": "#0f3460",
    "bg_dark": "#0a0a0f",
    "bg_card": "#1a1a2e",
    "bg_surface": "#16213e",
    "bg_page": "#0f0f1a",
    
    # Bordes
    "border": "#4B5563",
    "border_light": "#374151",
    "border_focus": "#60A5FA",
    
    # Hover
    "hover": "#374151",
    "hover_primary": "#93C5FD",
    
    # Sombras
    "shadow_color": "#000000",
    "shadow_opacity": 0.4,
}


# Colores por defecto (compatibilidad)
COLORS = LIGHT_COLORS.copy()


def get_colors():
    """Obtiene los colores del tema actual"""
    return ThemeManager.get_colors()


def update_colors():
    """Actualiza el diccionario COLORS global"""
    global COLORS
    COLORS = ThemeManager.get_colors()


# ==================== CONSTANTES DE UI ====================

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


def get_shadow(intensity: str = "md"):
    """Retorna una sombra según la intensidad"""
    colors = get_colors()
    shadows = {
        "sm": {"blur": 4, "spread": 0},
        "md": {"blur": 12, "spread": 0},
        "lg": {"blur": 24, "spread": 0},
    }
    s = shadows.get(intensity, shadows["md"])
    return ft.BoxShadow(
        blur_radius=s["blur"],
        spread_radius=s["spread"],
        color=ft.Colors.with_opacity(colors["shadow_opacity"], colors["shadow_color"]),
        offset=ft.Offset(0, 4)
    )
