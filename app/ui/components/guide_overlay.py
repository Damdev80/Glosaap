"""Overlay de guías interactivas (tour + ayuda por vista).

Renderiza sobre `ft.AlertDialog` (mismo canal que el resto de la app:
hilo principal, `page.open/close`). El texto y la lógica viven en
`app/ui/guide_content.py` para poder probarse sin Flet.
"""
from __future__ import annotations

from collections.abc import Callable

import flet as ft

from app.ui import guide_content


class GuideOverlay:
    """Tour modal paso a paso con "no volver a mostrar"."""

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
        self._dialog: ft.AlertDialog | None = None
        self._title = ft.Text("", size=16, weight=ft.FontWeight.W_600)
        self._counter = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self._body = ft.Text("", size=13)
        self._btn_back = ft.TextButton("Atrás", on_click=lambda e: self.back())
        self._btn_next = ft.ElevatedButton("Siguiente", on_click=lambda e: self.next())
        self._btn_skip = ft.TextButton("Omitir", on_click=lambda e: self.close())

    # ==================== API pública ====================

    def maybe_start_tour(self) -> bool:
        """Inicia el tour de primera vez si nunca se vio. Retorna si arrancó."""
        if not guide_content.should_show_tour(self._safe_get):
            return False
        self.start(
            list(guide_content.TOUR_STEPS), storage_key=guide_content.STORAGE_KEY
        )
        return True

    def show_help(self, view_key: str) -> bool:
        """Muestra la ayuda de una vista (una sola tarjeta)."""
        entry = guide_content.HELP_BY_VIEW.get(view_key or "")
        if not entry:
            return False
        self.start([{"title": entry["title"], "body": entry["body"]}])
        return True

    def start(
        self, steps: list[dict[str, str]], storage_key: str | None = None
    ) -> None:
        """Inicia un tour con los pasos dados (hilo principal)."""
        if not steps:
            return
        self._steps = list(steps)
        self._index = 0
        self._storage_key = storage_key
        self._render()
        try:
            self.page.open(self._dialog)
        except Exception:
            pass

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
        """Cierra el tour; con mark_seen guarda "no volver a mostrar"."""
        if mark_seen and self._storage_key:
            self._safe_set(self._storage_key, True)
        try:
            if self._dialog is not None:
                self.page.close(self._dialog)
        except Exception:
            pass
        self._dialog = None
        self._steps = []
        self._index = 0

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

    def _render(self) -> None:
        step = self._steps[self._index]
        total = len(self._steps)
        self._title.value = step.get("title", "")
        self._counter.value = (
            f"Paso {self._index + 1} de {total}" if total > 1 else ""
        )
        self._body.value = step.get("body", "")
        self._btn_back.disabled = self._index == 0
        self._btn_next.text = "Entendido" if self._index == total - 1 else "Siguiente"
        actions = [self._btn_back, self._btn_skip]
        if self._storage_key:
            actions.append(
                ft.TextButton(
                    "No volver a mostrar",
                    on_click=lambda e: self.close(mark_seen=True),
                )
            )
        actions.append(self._btn_next)
        content = ft.Column(
            [self._counter, self._body],
            spacing=8,
            tight=True,
            width=420,
        )
        try:
            content.scroll = ft.ScrollMode.AUTO  # type: ignore[attr-defined]
        except Exception:
            pass
        self._dialog = ft.AlertDialog(
            modal=True,
            title=self._title,
            content=content,
            actions=actions,
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )

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
