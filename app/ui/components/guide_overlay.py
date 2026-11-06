"""Guía interactiva: tour y ayuda por vista en tarjeta flotante no modal.

A diferencia de un AlertDialog (que apilaba instancias y no se cerraba),
aquí hay UNA sola tarjeta reutilizada en `page.overlay`: se muestra,
se actualiza por paso y al cerrar se retira del overlay. Al no ser
modal, la app sigue visible e interactuable, así el "focus" (parpadeo
del control mencionado, vía callback `on_flash`) sí se ve.

El texto y la lógica viven en `app/ui/guide_content.py`.
"""
from __future__ import annotations

from collections.abc import Callable

import flet as ft

from app.ui import guide_content


class GuideOverlay:
    """Tarjeta flotante de guía con pasos y "no volver a mostrar"."""

    def __init__(
        self,
        page: ft.Page,
        storage_get: Callable[[str], object | None] | None = None,
        storage_set: Callable[[str, object], None] | None = None,
    ):
        self.page = page
        self._get = storage_get or (lambda k: page.client_storage.get(k))
        self._set = storage_set or (lambda k, v: page.client_storage.set(k, v))
        self._steps: list[dict[str, str]] = []
        self._index = 0
        self._storage_key: str | None = None
        self._on_flash: Callable[[list[str]], None] | None = None
        self._flash: list[str] = []
        self._visible = False

        self._title = ft.Text("", size=16, weight=ft.FontWeight.W_600)
        self._counter = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self._body = ft.Text("", size=13)
        self._btn_back = ft.TextButton("Atrás", on_click=lambda e: self.back())
        self._btn_next = ft.ElevatedButton("Siguiente", on_click=lambda e: self.next())
        self._btn_skip = ft.TextButton("Omitir", on_click=lambda e: self.close())
        self._btn_hide = ft.TextButton(
            "No volver a mostrar", on_click=lambda e: self.close(mark_seen=True)
        )
        self._btn_close = ft.IconButton(
            icon=ft.Icons.CLOSE, tooltip="Cerrar", on_click=lambda e: self.close()
        )
        self._card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [self._title, self._btn_close],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        self._counter,
                        self._body,
                        ft.Row(
                            [self._btn_back, self._btn_skip],
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        ft.Row(
                            [self._btn_hide, self._btn_next],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ],
                    spacing=8,
                    tight=True,
                ),
                width=380,
                padding=16,
            ),
            elevation=8,
        )
        self._wrap = ft.Container(
            content=self._card,
            alignment=ft.alignment.bottom_right,
            padding=20,
        )

    # ==================== API pública ====================

    def maybe_start_tour(self) -> bool:
        """Inicia el tour de primera vez si nunca se vio. Retorna si arrancó."""
        if not guide_content.should_show_tour(self._safe_get):
            return False
        self.start(
            list(guide_content.TOUR_STEPS), storage_key=guide_content.STORAGE_KEY
        )
        return True

    def show_help(
        self, view_key: str, on_flash: Callable[[list[str]], None] | None = None
    ) -> bool:
        """Muestra la ayuda de una vista (una sola tarjeta + focus)."""
        entry = guide_content.HELP_BY_VIEW.get(view_key or "")
        if not entry:
            return False
        self.start(
            [{"title": entry["title"], "body": entry["body"]}],
            flash=list(entry.get("flash") or []),
            on_flash=on_flash,
        )
        return True

    def start(
        self,
        steps: list[dict[str, str]],
        storage_key: str | None = None,
        flash: list[str] | None = None,
        on_flash: Callable[[list[str]], None] | None = None,
    ) -> None:
        """Muestra la guía (hilo principal). Si ya está visible, la reemplaza."""
        if not steps:
            return
        self.close()
        self._steps = list(steps)
        self._index = 0
        self._storage_key = storage_key
        self._on_flash = on_flash
        self._flash = list(flash or [])
        self._render()
        try:
            if self._wrap not in self.page.overlay:
                self.page.overlay.append(self._wrap)
            self._visible = True
            self.page.update()
        except Exception:
            pass
        self._fire_flash()

    def next(self) -> None:
        """Avanza (o cierra y marca visto en el último paso)."""
        if self._index >= len(self._steps) - 1:
            self.close(mark_seen=True)
            return
        self._index += 1
        self._render()
        self._refresh()

    def back(self) -> None:
        """Retrocede un paso (sin salir del primero)."""
        if self._index > 0:
            self._index -= 1
            self._render()
            self._refresh()

    def close(self, mark_seen: bool = False) -> None:
        """Quita la guía del overlay. Con mark_seen guarda "no volver a mostrar"."""
        if mark_seen and self._storage_key:
            self._safe_set(self._storage_key, True)
        self._steps = []
        self._index = 0
        self._storage_key = None
        self._on_flash = None
        self._flash = []
        try:
            if self._wrap in self.page.overlay:
                self.page.overlay.remove(self._wrap)
            self._visible = False
            self.page.update()
        except Exception:
            pass

    @property
    def is_visible(self) -> bool:
        """True si la tarjeta de guía está mostrándose."""
        return self._visible

    # ==================== Internos ====================

    def _safe_get(self, key: str):
        try:
            return self._get(key)
        except Exception:
            return None

    def _safe_set(self, key: str, value) -> None:
        try:
            self._set(key, value)
        except Exception:
            pass

    def _fire_flash(self) -> None:
        if self._flash and self._on_flash is not None:
            try:
                self._on_flash(list(self._flash))
            except Exception:
                pass

    def _render(self) -> None:
        step = self._steps[self._index]
        total = len(self._steps)
        self._title.value = step.get("title", "")
        self._counter.value = f"Paso {self._index + 1} de {total}" if total > 1 else ""
        self._body.value = step.get("body", "")
        self._btn_back.disabled = self._index == 0
        self._btn_next.text = "Entendido" if self._index == total - 1 else "Siguiente"
        self._btn_hide.visible = self._storage_key is not None
        self._btn_skip.visible = total > 1

    def _refresh(self) -> None:
        try:
            self.page.update()
        except Exception:
            pass


def help_button(on_help: Callable | None):
    """Botón ? estándar para headers (None si no hay callback)."""
    if on_help is None:
        return None
    return ft.IconButton(
        icon=ft.Icons.HELP_OUTLINE,
        tooltip="Ayuda de esta vista",
        icon_size=20,
        on_click=lambda e: on_help(),
    )
