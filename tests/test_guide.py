"""Tests de guías interactivas (Fase C): contenido, overlay y checklist.

Todo sin GUI real: contenido puro + overlay con page falsa.
"""
from types import SimpleNamespace

import pytest

from app.ui import guide_content
from app.ui.components.guide_overlay import GuideOverlay, help_button
from app.ui.navigation import NavigationController


class FakePage:
    def __init__(self):
        self.overlay = []
        self.updated = 0

    def update(self):
        self.updated += 1


@pytest.fixture
def storage():
    return {}


@pytest.fixture
def overlay(storage):
    page = FakePage()
    return (
        GuideOverlay(
            page,
            storage_get=storage.get,
            storage_set=storage.__setitem__,
        ),
        page,
        storage,
    )


class TestGuideContent:
    def test_tour_tiene_pasos_completos(self):
        assert len(guide_content.TOUR_STEPS) >= 4
        for step in guide_content.TOUR_STEPS:
            assert step["title"].strip()
            assert step["body"].strip()

    def test_ayuda_cubre_todas_las_vistas(self):
        for view_key in NavigationController.BACK_ROUTES:
            assert view_key in guide_content.HELP_BY_VIEW, f"sin ayuda: {view_key}"
            entry = guide_content.HELP_BY_VIEW[view_key]
            assert entry["title"].strip()
            assert entry["body"].strip()

    def test_checklist_vacio_todo_pendiente_menos_primero(self):
        states = guide_content.checklist_state(0, 0, False)
        assert [s["label"] for s in states] == ["Buscar", "Descargar", "Procesar", "Revisar"]
        assert states[0]["state"] == "current"
        assert all(s["state"] == "pending" for s in states[1:])

    def test_checklist_progresa_y_completa(self):
        assert [s["state"] for s in guide_content.checklist_state(3, 0, False)] == [
            "done", "current", "pending", "pending",
        ]
        assert [s["state"] for s in guide_content.checklist_state(3, 2, False)] == [
            "done", "done", "current", "pending",
        ]
        assert [s["state"] for s in guide_content.checklist_state(3, 2, True)] == [
            "done", "done", "done", "done",
        ]

    def test_checklist_tolera_negativos_y_none(self):
        states = guide_content.checklist_state(-5, None, False)
        assert states[0]["state"] == "current"

    def test_should_show_tour(self):
        assert guide_content.should_show_tour({}.get) is True
        lleno = {guide_content.STORAGE_KEY: True}
        assert guide_content.should_show_tour(lleno.get) is False
        assert (
            guide_content.should_show_tour(
                lambda k: (_ for _ in ()).throw(RuntimeError("x"))
            )
            is False
        )


class TestGuideOverlay:
    def test_maybe_start_tour_una_sola_vez(self, overlay):
        ov, page, storage = overlay
        assert ov.maybe_start_tour() is True
        assert ov.is_visible is True
        assert len(page.overlay) == 1
        # Sin marcar visto, volvería a arrancar (el tour completo lo marca),
        # pero sin apilar tarjetas.
        assert ov.maybe_start_tour() is True
        assert len(page.overlay) == 1

    def test_navegacion_y_cierre_marcan_visto(self, overlay):
        ov, page, storage = overlay
        assert ov.maybe_start_tour() is True
        total = len(guide_content.TOUR_STEPS)
        for _ in range(total - 1):
            ov.next()
        assert ov.is_visible is True
        ov.next()  # último -> cierra y marca
        assert storage.get(guide_content.STORAGE_KEY) is True
        assert ov.is_visible is False
        assert page.overlay == []
        # Ya no arranca solo.
        assert ov.maybe_start_tour() is False

    def test_back_no_sale_del_primero(self, overlay):
        ov, page, storage = overlay
        ov.maybe_start_tour()
        ov.back()
        assert ov._index == 0
        assert len(page.overlay) == 1

    def test_no_volver_a_mostrar(self, overlay):
        ov, page, storage = overlay
        ov.maybe_start_tour()
        ov.close(mark_seen=False)
        assert guide_content.STORAGE_KEY not in storage
        assert page.overlay == []
        ov.maybe_start_tour()
        ov.close(mark_seen=True)
        assert storage[guide_content.STORAGE_KEY] is True

    def test_show_help_por_vista_y_flash(self, overlay):
        ov, page, storage = overlay
        seen = []

        def _flash(names):
            seen.append(names)

        assert ov.show_help("messages", on_flash=_flash) is True
        assert len(page.overlay) == 1
        assert seen == [["checklist", "process"]]
        ov.close()
        assert page.overlay == []
        assert ov.show_help("vista_inexistente_xyz") is False

    def test_start_sin_pasos_no_abre(self, overlay):
        ov, page, storage = overlay
        ov.start([])
        assert page.overlay == []

    def test_help_button(self):
        assert help_button(None) is None
        btn = help_button(lambda: None)
        assert btn is not None
        assert btn.tooltip == "Ayuda de esta vista"


class FakeViewPage:
    """Page mínima para instanciar vistas (sin Flet real corriendo)."""

    def __init__(self):
        self.overlay = []
        self.updated = 0
        self.window = SimpleNamespace(width=800, height=600)

    def update(self):
        self.updated += 1


class TestGuideFlash:
    def test_checklist_y_flash_mensajes(self):
        import time

        from app.ui.views.messages_view import MessagesView

        view = MessagesView(
            FakeViewPage(),
            on_back=None,
            on_refresh=None,
            on_download_selected=None,
            on_process=None,
        )
        assert view.guide_banner.visible is False
        view.refresh_checklist(2, 1, False)
        assert view.guide_banner.visible is True
        assert len(view._guide_steps_row.controls) == 7  # 4 chips + 3 flechas

        view.flash_checklist(duration=0.05)
        assert view.guide_banner.bgcolor is not None
        time.sleep(0.2)
        assert view.guide_banner.bgcolor is None

        view.flash_process_button(duration=0.05)
        time.sleep(0.2)

    def test_flash_manejar_dashboard(self):
        import time

        from app.ui.views.dashboard_view import DashboardView

        view = DashboardView(FakeViewPage(), assets_dir="inexistente")
        assert view._manejar_card is not None
        view.flash_manejar(duration=0.05)
        time.sleep(0.2)
        assert view._manejar_card.color is None
