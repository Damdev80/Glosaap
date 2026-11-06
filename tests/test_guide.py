"""Tests de guías interactivas (Fase C): contenido, overlay y checklist.

Todo sin GUI real: contenido puro + overlay con page falsa.
"""
import pytest

from app.ui import guide_content
from app.ui.components.guide_overlay import GuideOverlay, help_button
from app.ui.navigation import NavigationController


class FakePage:
    def __init__(self):
        self.opened = []
        self.closed = []
        self.updated = 0

    def open(self, dialog):
        self.opened.append(dialog)

    def close(self, dialog):
        self.closed.append(dialog)

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
        assert len(page.opened) == 1
        # Sin marcar visto, volvería a arrancar (el tour completo lo marca).
        assert ov.maybe_start_tour() is True

    def test_navegacion_y_cierre_marcan_visto(self, overlay):
        ov, page, storage = overlay
        assert ov.maybe_start_tour() is True
        total = len(guide_content.TOUR_STEPS)
        for _ in range(total - 1):
            ov.next()
        assert page.updated >= total - 1
        ov.next()  # último -> cierra y marca
        assert storage.get(guide_content.STORAGE_KEY) is True
        assert len(page.closed) == 1
        # Ya no arranca solo.
        assert ov.maybe_start_tour() is False

    def test_back_no_sale_del_primero(self, overlay):
        ov, page, storage = overlay
        ov.maybe_start_tour()
        ov.back()
        assert ov._index == 0
        assert len(page.opened) == 1

    def test_no_volver_a_mostrar(self, overlay):
        ov, page, storage = overlay
        ov.maybe_start_tour()
        ov.close(mark_seen=False)
        assert guide_content.STORAGE_KEY not in storage
        ov.maybe_start_tour()
        ov.close(mark_seen=True)
        assert storage[guide_content.STORAGE_KEY] is True

    def test_show_help_por_vista(self, overlay):
        ov, page, storage = overlay
        assert ov.show_help("messages") is True
        assert len(page.opened) == 1
        assert ov.show_help("vista_inexistente_xyz") is False

    def test_start_sin_pasos_no_abre(self, overlay):
        ov, page, storage = overlay
        ov.start([])
        assert page.opened == []

    def test_help_button(self):
        assert help_button(None) is None
        btn = help_button(lambda: None)
        assert btn is not None
        assert btn.tooltip == "Ayuda de esta vista"
