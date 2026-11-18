"""
Paquete de vistas de la aplicación
"""
from .analytics_dashboard_view import AnalyticsDashboardView
from .dashboard_view import DashboardView
from .login_view import LoginView
from .messages_view import MessagesView
from .tools_view import ToolsView

__all__ = [
    'AnalyticsDashboardView',
    'DashboardView',
    'LoginView',
    'ToolsView',
    'MessagesView',
]
