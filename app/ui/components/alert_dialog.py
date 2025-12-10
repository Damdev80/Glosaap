"""
Componente de diálogos de alerta reutilizables
"""
import flet as ft
from app.ui.styles import COLORS


class AlertDialog:
    """Diálogos de alerta modernos y reutilizables"""
    
    @staticmethod
    def show_success(page: ft.Page, title: str, message: str, on_close=None):
        """Muestra un diálogo de éxito"""
        def close_dialog(e):
            dialog.open = False
            page.update()
            if on_close:
                on_close()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=COLORS["success"], size=32),
                ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"])
            ], spacing=12),
            content=ft.Container(
                content=ft.Text(
                    message,
                    size=15,
                    color=COLORS["text_secondary"]
                ),
                padding=ft.padding.only(top=10, bottom=10)
            ),
            actions=[
                ft.TextButton(
                    "Aceptar",
                    on_click=close_dialog,
                    style=ft.ButtonStyle(
                        color=COLORS["success"]
                    )
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=16),
            bgcolor=COLORS["bg_white"]
        )
        
        page.overlay.append(dialog)
        dialog.open = True
        page.update()
        return dialog
    
    @staticmethod
    def show_error(page: ft.Page, title: str, message: str, on_close=None):
        """Muestra un diálogo de error"""
        def close_dialog(e):
            dialog.open = False
            page.update()
            if on_close:
                on_close()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.ERROR, color=COLORS["error"], size=32),
                ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"])
            ], spacing=12),
            content=ft.Container(
                content=ft.Text(
                    message,
                    size=15,
                    color=COLORS["text_secondary"]
                ),
                padding=ft.padding.only(top=10, bottom=10)
            ),
            actions=[
                ft.TextButton(
                    "Cerrar",
                    on_click=close_dialog,
                    style=ft.ButtonStyle(
                        color=COLORS["error"]
                    )
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=16),
            bgcolor=COLORS["bg_white"]
        )
        
        page.overlay.append(dialog)
        dialog.open = True
        page.update()
        return dialog
    
    @staticmethod
    def show_info(page: ft.Page, title: str, message: str, on_close=None):
        """Muestra un diálogo informativo"""
        def close_dialog(e):
            dialog.open = False
            page.update()
            if on_close:
                on_close()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.INFO, color=COLORS["primary"], size=32),
                ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"])
            ], spacing=12),
            content=ft.Container(
                content=ft.Text(
                    message,
                    size=15,
                    color=COLORS["text_secondary"]
                ),
                padding=ft.padding.only(top=10, bottom=10)
            ),
            actions=[
                ft.TextButton(
                    "Entendido",
                    on_click=close_dialog,
                    style=ft.ButtonStyle(
                        color=COLORS["primary"]
                    )
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=16),
            bgcolor=COLORS["bg_white"]
        )
        
        page.overlay.append(dialog)
        dialog.open = True
        page.update()
        return dialog
    
    @staticmethod
    def show_warning(page: ft.Page, title: str, message: str, on_close=None):
        """Muestra un diálogo de advertencia"""
        def close_dialog(e):
            dialog.open = False
            page.update()
            if on_close:
                on_close()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.WARNING, color=COLORS["warning"], size=32),
                ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"])
            ], spacing=12),
            content=ft.Container(
                content=ft.Text(
                    message,
                    size=15,
                    color=COLORS["text_secondary"]
                ),
                padding=ft.padding.only(top=10, bottom=10)
            ),
            actions=[
                ft.TextButton(
                    "Entendido",
                    on_click=close_dialog,
                    style=ft.ButtonStyle(
                        color=COLORS["warning"]
                    )
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=16),
            bgcolor=COLORS["bg_white"]
        )
        
        page.overlay.append(dialog)
        dialog.open = True
        page.update()
        return dialog
    
    @staticmethod
    def show_processing_complete(page: ft.Page, eps_name: str, stats: dict, output_files: list, on_close=None, on_open_folder=None):
        """Muestra un diálogo detallado cuando termina el procesamiento"""
        def close_dialog(e):
            dialog.open = False
            page.update()
            if on_close:
                on_close()
        
        def open_folder(e):
            dialog.open = False
            page.update()
            if on_open_folder:
                on_open_folder()
        
        # Construir mensaje con estadísticas
        stats_text = []
        if stats.get('total_registros'):
            stats_text.append(f"📊 {stats['total_registros']} registros procesados")
        if stats.get('facturas_unicas'):
            stats_text.append(f"🧾 {stats['facturas_unicas']} facturas únicas")
        if stats.get('codigos_homologados'):
            stats_text.append(f"✅ {stats['codigos_homologados']} códigos homologados")
        if stats.get('archivos_procesados'):
            stats_text.append(f"📁 {stats['archivos_procesados']} archivos procesados")
        
        # Lista de archivos generados
        files_list = ft.Column([
            ft.Text(
                "📄 " + file.split("\\")[-1] if "\\" in file else "📄 " + file.split("/")[-1],
                size=13,
                color=COLORS["text_primary"],
                weight=ft.FontWeight.W_500
            ) for file in output_files
        ], spacing=6)
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=COLORS["success"], size=36),
                ft.Column([
                    ft.Text("¡Procesamiento completado!", size=20, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"]),
                    ft.Text(eps_name, size=14, color=COLORS["text_secondary"])
                ], spacing=2)
            ], spacing=12),
            content=ft.Container(
                content=ft.Column([
                    # Estadísticas
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Resumen:", size=15, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"]),
                            ft.Container(height=8),
                            *[ft.Text(stat, size=14, color=COLORS["text_secondary"]) for stat in stats_text]
                        ]),
                        padding=ft.padding.all(16),
                        bgcolor=ft.Colors.with_opacity(0.05, COLORS["success"]),
                        border_radius=12,
                        border=ft.border.all(1, ft.Colors.with_opacity(0.2, COLORS["success"]))
                    ),
                    ft.Container(height=16),
                    # Archivos generados
                    ft.Text("Archivos generados:", size=15, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"]),
                    ft.Container(height=8),
                    files_list
                ], spacing=0),
                padding=ft.padding.only(top=10, bottom=10)
            ),
            actions=[
                ft.TextButton(
                    "Cerrar",
                    on_click=close_dialog,
                    style=ft.ButtonStyle(
                        color=COLORS["text_secondary"]
                    )
                ),
                ft.ElevatedButton(
                    "📂 Abrir carpeta",
                    on_click=open_folder,
                    bgcolor=COLORS["success"],
                    color=COLORS["bg_white"],
                    icon=ft.Icons.FOLDER_OPEN
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=16),
            bgcolor=COLORS["bg_white"]
        )
        
        page.overlay.append(dialog)
        dialog.open = True
        page.update()
        return dialog
    
    @staticmethod
    def show_search_complete(page: ft.Page, total_found: int, filtered_count: int, excel_count: int, eps_name: str, date_range: str, on_close=None):
        """Muestra un diálogo cuando termina la búsqueda de correos"""
        def close_dialog(e):
            dialog.open = False
            page.update()
            if on_close:
                on_close()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.MAIL, color=COLORS["primary"], size=36),
                ft.Text("Búsqueda completada", size=20, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"])
            ], spacing=12),
            content=ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.BUSINESS, size=20, color=COLORS["primary"]),
                                ft.Text(f"EPS: {eps_name}", size=14, color=COLORS["text_primary"], weight=ft.FontWeight.W_500)
                            ], spacing=8),
                            ft.Row([
                                ft.Icon(ft.Icons.CALENDAR_TODAY, size=20, color=COLORS["primary"]),
                                ft.Text(date_range, size=14, color=COLORS["text_secondary"])
                            ], spacing=8),
                        ]),
                        padding=ft.padding.all(16),
                        bgcolor=ft.Colors.with_opacity(0.05, COLORS["primary"]),
                        border_radius=12,
                        border=ft.border.all(1, ft.Colors.with_opacity(0.2, COLORS["primary"]))
                    ),
                    ft.Container(height=16),
                    ft.Column([
                        ft.Text("Resultados:", size=15, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"]),
                        ft.Container(height=8),
                        ft.Text(f"📧 {total_found} correos encontrados", size=14, color=COLORS["text_secondary"]),
                        ft.Text(f"🎯 {filtered_count} correos de {eps_name}", size=14, color=COLORS["text_secondary"]),
                        ft.Text(f"📊 {excel_count} archivos Excel descargados", size=14, color=COLORS["success"] if excel_count > 0 else COLORS["text_light"]),
                    ])
                ], spacing=0),
                padding=ft.padding.only(top=10, bottom=10)
            ),
            actions=[
                ft.TextButton(
                    "Entendido",
                    on_click=close_dialog,
                    style=ft.ButtonStyle(
                        color=COLORS["primary"]
                    )
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=16),
            bgcolor=COLORS["bg_white"]
        )
        
        page.overlay.append(dialog)
        dialog.open = True
        page.update()
        return dialog
