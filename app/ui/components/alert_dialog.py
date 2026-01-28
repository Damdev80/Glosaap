"""
Componente de diálogos de alerta reutilizables
Usa page.open() y page.close() (API moderna de Flet)
Con soporte de temas claro/oscuro
"""
import flet as ft


class AlertDialog:
    """Di�logos de alerta modernos y reutilizables"""
    
    @staticmethod
    def show_success(page: ft.Page, title: str, message: str, on_close=None):
        """Muestra un di�logo de �xito"""
        def close_dialog(e):
            page.close(dialog)
            if on_close:
                on_close()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, size=28),
                ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE)
            ], spacing=10),
            content=ft.Text(message, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
            actions=[
                ft.TextButton("Aceptar", on_click=close_dialog, style=ft.ButtonStyle(color=ft.Colors.GREEN)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=ft.Colors.SURFACE
        )
        
        page.open(dialog)
        return dialog
    
    @staticmethod
    def show_error(page: ft.Page, title: str, message: str, on_close=None):
        """Muestra un di�logo de error"""
        def close_dialog(e):
            page.close(dialog)
            if on_close:
                on_close()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED, size=28),
                ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE)
            ], spacing=10),
            content=ft.Text(message, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
            actions=[
                ft.TextButton("Cerrar", on_click=close_dialog, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=ft.Colors.SURFACE
        )
        
        page.open(dialog)
        return dialog
    
    @staticmethod
    def show_info(page: ft.Page, title: str, message: str, on_close=None):
        """Muestra un di�logo informativo"""
        def close_dialog(e):
            page.close(dialog)
            if on_close:
                on_close()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.INFO, color=ft.Colors.PRIMARY, size=28),
                ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE)
            ], spacing=10),
            content=ft.Text(message, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
            actions=[
                ft.TextButton("Entendido", on_click=close_dialog, style=ft.ButtonStyle(color=ft.Colors.PRIMARY)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=ft.Colors.SURFACE
        )
        
        page.open(dialog)
        return dialog
    
    @staticmethod
    def show_warning(page: ft.Page, title: str, message: str, on_close=None):
        """Muestra un di�logo de advertencia"""
        def close_dialog(e):
            page.close(dialog)
            if on_close:
                on_close()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.WARNING, color=ft.Colors.ORANGE, size=28),
                ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE)
            ], spacing=10),
            content=ft.Text(message, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
            actions=[
                ft.TextButton("Entendido", on_click=close_dialog, style=ft.ButtonStyle(color=ft.Colors.ORANGE)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=ft.Colors.SURFACE
        )
        
        page.open(dialog)
        return dialog
    
    @staticmethod
    def show_processing_complete(page: ft.Page, eps_name: str, stats: dict, output_files: list, on_close=None, on_open_folder=None):
        """Muestra un di�logo detallado cuando termina el procesamiento"""
        def close_dialog(e):
            page.close(dialog)
            if on_close:
                on_close()
        
        def open_folder(e):
            page.close(dialog)
            if on_open_folder:
                on_open_folder()
        
        # Construir mensaje con estad�sticas
        stats_text = []
        if stats.get('total_registros'):
            stats_text.append(f" {stats['total_registros']} registros procesados")
        if stats.get('facturas_unicas'):
            stats_text.append(f" {stats['facturas_unicas']} facturas �nicas")
        if stats.get('codigos_homologados'):
            stats_text.append(f" {stats['codigos_homologados']} c�digos homologados")
        if stats.get('archivos_procesados'):
            stats_text.append(f" {stats['archivos_procesados']} archivos procesados")
        
        # Lista de archivos generados
        files_list = ft.Column([
            ft.Text(
                " " + (file.split("\\")[-1] if "\\" in file else file.split("/")[-1]),
                size=13, color=ft.Colors.ON_SURFACE, weight=ft.FontWeight.W_500
            ) for file in output_files
        ], spacing=6)
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, size=28),
                ft.Text(f"�Procesamiento completado! - {eps_name}", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE)
            ], spacing=10),
            content=ft.Column([
                ft.Container(
                    content=ft.Column([ft.Text(stat, size=13, color=ft.Colors.ON_SURFACE_VARIANT) for stat in stats_text], spacing=4, tight=True),
                    padding=12, bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.GREEN), border_radius=8,
                ),
                ft.Container(height=12),
                ft.Text("Archivos generados:", size=14, weight=ft.FontWeight.W_500, color=ft.Colors.ON_SURFACE),
                files_list
            ], spacing=4, tight=True),
            actions=[
                ft.TextButton("Cerrar", on_click=close_dialog, style=ft.ButtonStyle(color=ft.Colors.ON_SURFACE_VARIANT)),
                ft.ElevatedButton(" Abrir carpeta", on_click=open_folder, bgcolor=ft.Colors.GREEN, color=ft.Colors.SURFACE),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=ft.Colors.SURFACE
        )
        
        page.open(dialog)
        return dialog
    
    @staticmethod
    def show_search_complete(page: ft.Page, total_found: int, filtered_count: int, excel_count: int, eps_name: str, date_range: str, on_close=None):
        """Muestra un di�logo cuando termina la b�squeda de correos"""
        def close_dialog(e):
            page.close(dialog)
            if on_close:
                on_close()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.MAIL, color=ft.Colors.PRIMARY, size=28),
                ft.Text("B�squeda completada", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE)
            ], spacing=10),
            content=ft.Column([
                ft.Text(f"EPS: {eps_name}", size=14, color=ft.Colors.ON_SURFACE, weight=ft.FontWeight.W_500),
                ft.Text(date_range, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Divider(height=16),
                ft.Text(f" {total_found} correos encontrados", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(f" {filtered_count} correos de {eps_name}", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(f" {excel_count} archivos Excel descargados", size=13, color=ft.Colors.GREEN if excel_count > 0 else ft.Colors.ON_SURFACE_VARIANT),
            ], spacing=4, tight=True),
            actions=[
                ft.TextButton("Entendido", on_click=close_dialog, style=ft.ButtonStyle(color=ft.Colors.PRIMARY)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=ft.Colors.SURFACE
        )
        
        page.open(dialog)
        return dialog
