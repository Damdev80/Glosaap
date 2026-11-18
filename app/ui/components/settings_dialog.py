"""Diálogo de configuración canónico de Glosaap.

Fuente única del panel de settings (tema, versión y conexión API Glosapp). Lo reutilizan
``app.py`` (botón global) y ``dashboard_view`` (botón local). Usa
``page.open``/``page.close`` (sin ``overlay.clear()`` destructivo) y
``ft.Colors.*`` (sin hex fijo).
"""
import re
import threading

import flet as ft

from app.config.settings import (
    APP_VERSION,
    DEFAULT_GLOSAPP_API_KEY,
    DEFAULT_GLOSAPP_API_URL,
)
from app.service.glosapp_api_client import api_client
from app.ui.styles import ThemeManager, update_colors


def get_stored_api_credentials(page: ft.Page) -> tuple[str, str]:
    """Obtiene la URL y la API-Key guardadas en client_storage o valores por defecto."""
    storage = getattr(page, "client_storage", None)
    stored_url = None
    stored_key = None
    if storage is not None:
        try:
            stored_url = storage.get("glosapp_api_url")
            stored_key = storage.get("glosapp_api_key")
        except Exception:
            pass
    url = (stored_url or DEFAULT_GLOSAPP_API_URL or "").strip()
    key = (stored_key or DEFAULT_GLOSAPP_API_KEY or "").strip()
    return url, key


def save_stored_api_credentials(page: ft.Page, url: str, key: str) -> None:
    """Guarda la URL y la API-Key en client_storage y actualiza el cliente global."""
    storage = getattr(page, "client_storage", None)
    if storage is not None:
        try:
            storage.set("glosapp_api_url", url.strip())
            storage.set("glosapp_api_key", key.strip())
        except Exception:
            pass
    api_client.update_credentials(base_url=url, api_key=key)


def show_settings_dialog(page: ft.Page, on_theme_change=None, on_api_change=None):
    """Abre el diálogo de configuración canónico.

    Args:
        page: Página de Flet.
        on_theme_change: Callback opcional tras cambiar el tema.
        on_api_change: Callback opcional tras guardar cambios de la API.

    Returns:
        El ``ft.AlertDialog`` abierto.
    """
    is_dark = ThemeManager.is_dark()
    current_url, current_key = get_stored_api_credentials(page)
    # Sincronizar el singleton al abrir
    api_client.update_credentials(base_url=current_url, api_key=current_key)

    def toggle_theme(ev):
        page.close(settings_dialog)
        ThemeManager.toggle_theme()
        update_colors()
        if on_theme_change is not None:
            try:
                on_theme_change()
            except Exception:
                pass

    # Controles de API
    api_url_input = ft.TextField(
        label="URL Base API",
        value=current_url,
        dense=True,
        text_size=12,
        hint_text="http://10.10.10.18:8081/glosapp/api/v1",
        prefix_icon=ft.Icons.LINK,
    )
    api_key_input = ft.TextField(
        label="X-API-Key",
        value=current_key,
        password=True,
        can_reveal_password=True,
        dense=True,
        text_size=12,
        hint_text="Pega la clave entregada por Sistemas",
        prefix_icon=ft.Icons.KEY,
    )
    status_icon = ft.Icon(
        ft.Icons.CHECK_CIRCLE if current_key else ft.Icons.INFO_OUTLINE,
        size=14,
        color=ft.Colors.PRIMARY if current_key else ft.Colors.AMBER_700,
    )
    status_text = ft.Text(
        "Ingresa tu clave para conectar con el servidor" if not current_key else "Clave configurada",
        size=11,
        color=ft.Colors.PRIMARY if current_key else ft.Colors.AMBER_700,
        expand=True,
    )
    status_row = ft.Row(
        [status_icon, status_text],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    test_btn = ft.OutlinedButton("Probar conexión", icon=ft.Icons.NETWORK_CHECK)
    save_btn = ft.ElevatedButton("Guardar clave", icon=ft.Icons.SAVE)

    def on_test_click(e):
        test_btn.disabled = True
        status_icon.name = ft.Icons.SYNC
        status_icon.color = ft.Colors.ON_SURFACE_VARIANT
        status_text.value = "Verificando con el servidor..."
        status_text.color = ft.Colors.ON_SURFACE_VARIANT
        try:
            page.update()
        except Exception:
            pass

        def _do_test():
            target_url = api_url_input.value.strip() or current_url
            target_key = api_key_input.value.strip()
            res = api_client.validate_key(api_key=target_key, base_url=target_url)
            if res.get("valid"):
                status_icon.name = ft.Icons.CHECK_CIRCLE
                status_icon.color = ft.Colors.GREEN_700
                status_text.value = "Conexión y clave válidas con el servidor mercurio"
                status_text.color = ft.Colors.GREEN_700
            else:
                msg = res.get("message", "Error de conexión")
                msg_str = re.sub(r'[\U00010000-\U0010ffff\u2600-\u27bf]', '', str(msg)).strip()
                if ":8001" in target_url or ":8000" in target_url:
                    msg_str = "Error de puerto: el servidor mercurio atiende en el puerto 8081 (http://10.10.10.18:8081/glosapp/api/v1)"
                elif "Timeout" in msg_str or "ConnectTimeout" in msg_str:
                    msg_str = "Tiempo agotado al conectar. Verifica usar el puerto 8081 (http://10.10.10.18:8081/glosapp/api/v1)."
                status_icon.name = ft.Icons.ERROR_OUTLINE
                status_icon.color = ft.Colors.ERROR
                status_text.value = msg_str
                status_text.color = ft.Colors.ERROR
            test_btn.disabled = False
            try:
                page.update()
            except Exception:
                pass

        threading.Thread(target=_do_test, daemon=True).start()

    def on_save_click(e):
        target_url = api_url_input.value.strip()
        target_key = api_key_input.value.strip()
        save_stored_api_credentials(page, target_url, target_key)
        status_icon.name = ft.Icons.CHECK_CIRCLE
        status_icon.color = ft.Colors.GREEN_700
        status_text.value = "Configuración guardada correctamente"
        status_text.color = ft.Colors.GREEN_700
        try:
            page.update()
        except Exception:
            pass
        if on_api_change is not None:
            try:
                on_api_change()
            except Exception:
                pass

    test_btn.on_click = on_test_click
    save_btn.on_click = on_save_click

    settings_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon(ft.Icons.SETTINGS, size=20, color=ft.Colors.PRIMARY),
            ft.Text("Configuración", size=18, weight=ft.FontWeight.W_600),
        ], spacing=8),
        content=ft.Container(
            content=ft.Column([
                # Apariencia
                ft.Text("Apariencia", size=14, weight=ft.FontWeight.W_600),
                ft.Container(height=4),
                ft.Row([
                    ft.Icon(
                        ft.Icons.DARK_MODE if is_dark else ft.Icons.LIGHT_MODE,
                        size=20,
                    ),
                    ft.Text("Modo oscuro", size=13),
                    ft.Container(expand=True),
                    ft.Switch(value=is_dark, on_change=toggle_theme),
                ], alignment=ft.MainAxisAlignment.START),
                ft.Divider(height=16),

                # Conexión API Glosapp
                ft.Row([
                    ft.Icon(ft.Icons.CLOUD_SYNC, size=18, color=ft.Colors.PRIMARY),
                    ft.Text("Conexión API Glosapp (Servidor mercurio)", size=14, weight=ft.FontWeight.W_600),
                ], spacing=6),
                ft.Text(
                    "Permite alimentar métricas y consultar el Dashboard de trazabilidad.",
                    size=11,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.Container(height=6),
                api_url_input,
                api_key_input,
                status_row,
                ft.Row([
                    test_btn,
                    save_btn,
                ], spacing=8, alignment=ft.MainAxisAlignment.END),
                ft.Divider(height=16),

                # Información
                ft.Text("Información", size=14, weight=ft.FontWeight.W_600),
                ft.Container(height=4),
                ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=20),
                    ft.Column([
                        ft.Text(f"Versión: {APP_VERSION}", size=12),
                        ft.Text("Glosaap - Gestión de Glosas", size=11),
                    ], spacing=2),
                ], alignment=ft.MainAxisAlignment.START, spacing=10),
            ], spacing=6, tight=True, scroll=ft.ScrollMode.AUTO),
            width=380,
            padding=ft.padding.only(top=10),
        ),
        actions=[
            ft.TextButton(
                "Cerrar",
                on_click=lambda e: page.close(settings_dialog),
            )
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.open(settings_dialog)
    return settings_dialog


# Alias para compatibilidad de import.
open_settings_dialog = show_settings_dialog
