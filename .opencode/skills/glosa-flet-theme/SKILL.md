---
name: Glosa Flet Theme
description: Reglas de UI Flet, temas claro oscuro y navegación del proyecto
---

# Glosa Flet Theme

Úsalo antes de tocar `app/ui/`.

## Colores
- Usa `ft.Colors.SURFACE`, `ON_SURFACE`, `PRIMARY`, `ON_PRIMARY`. Prohibido hex fijo (`#ffffff`, `#000000`, `#2196F3`, `#4CAF50`, `#4488ee`).
- Todo `Container` de vista lleva `bgcolor=ft.Colors.SURFACE` para evitar transparencias/pantalla negra.
- Verifica en tema claro Y oscuro. El hint `#000000` de `homologacion_view.py:164` es el ejemplo de lo que no hacer.

## Navegación
- Toda vista expone `.container`. Registra la ruta en `app/ui/app.py` (go_to_*) Y en `app/ui/navigation.py` a la vez.
- No dejes back muerto: `homologacion` vuelve a `tools`, `messages` a `eps`, `eps` a `dashboard`.
- No uses `overlay.clear()` (borra FilePicker/DatePicker). Cierra solo tu diálogo.
- No llames `page.update()` desde threads (Flet no es thread-safe); devuelve el resultado al hilo principal.
- `Toast` y `LoadingOverlay` se remueven tras usarlos; no hagas append infinito.

## Componentes
- Reutiliza `AlertDialog`, `LoadingOverlay`, `LoadingButton`, `ToastNotification`, `EpsCard`, `DateRangePicker`, `NavigationHeader`, `UpdateDialog`.
- No resucites muertos sin motivo: `data_table.py`, `custom_dialogs.py`, `settings_button.create_settings_fab`.
