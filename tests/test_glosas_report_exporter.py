"""
Tests unitarios y de integración para el módulo de Informe de Glosas (BD Externa),
calculadora de periodicidades, exportación a Excel (.xlsx) y PDF (.pdf),
y montaje como Tab independiente dentro de AnalyticsDashboardView.
"""
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import openpyxl
from pypdf import PdfReader

from app.service.dgh_sql_provider import DGH_GLOSAS_COLUMN_MAPPING, DghSqlGlosasProvider
from app.service.glosas_report_exporter import (
    ExternalGlosasReportService,
    ExternalTableSchema,
    GlosasReportExporter,
    PeriodRangeCalculator,
    _to_float,
)
from app.ui.views.analytics_dashboard_view import AnalyticsDashboardView
from app.ui.views.glosas_report_tab_view import GlosasReportTabView


class TestPeriodRangeCalculator:
    """Verifica el cálculo de cortes semanal, quincenal, mensual, trimestral y semestral."""

    def test_rolling_ranges(self):
        ref = date(2026, 11, 23)
        assert PeriodRangeCalculator.calculate_range("SEMANAL", ref, mode="rolling") == (date(2026, 11, 16), ref)
        assert PeriodRangeCalculator.calculate_range("QUINCENAL", ref, mode="rolling") == (date(2026, 11, 8), ref)
        assert PeriodRangeCalculator.calculate_range("MENSUAL", ref, mode="rolling") == (date(2026, 10, 24), ref)
        assert PeriodRangeCalculator.calculate_range("TRIMESTRAL", ref, mode="rolling") == (date(2026, 8, 25), ref)
        assert PeriodRangeCalculator.calculate_range("SEMESTRAL", ref, mode="rolling") == (date(2026, 5, 27), ref)

    def test_calendar_ranges(self):
        # 2026-11-23 es lunes
        ref = date(2026, 11, 23)
        assert PeriodRangeCalculator.calculate_range("SEMANAL", ref, mode="calendar") == (
            date(2026, 11, 23),
            date(2026, 11, 29),
        )
        # Segunda quincena de noviembre
        assert PeriodRangeCalculator.calculate_range("QUINCENAL", ref, mode="calendar") == (
            date(2026, 11, 16),
            date(2026, 11, 30),
        )
        # Primera quincena
        assert PeriodRangeCalculator.calculate_range("QUINCENAL", date(2026, 11, 10), mode="calendar") == (
            date(2026, 11, 1),
            date(2026, 11, 15),
        )
        assert PeriodRangeCalculator.calculate_range("MENSUAL", ref, mode="calendar") == (
            date(2026, 11, 1),
            date(2026, 11, 30),
        )
        assert PeriodRangeCalculator.calculate_range("TRIMESTRAL", ref, mode="calendar") == (
            date(2026, 10, 1),
            date(2026, 12, 31),
        )
        assert PeriodRangeCalculator.calculate_range("SEMESTRAL", ref, mode="calendar") == (
            date(2026, 7, 1),
            date(2026, 12, 31),
        )
        assert PeriodRangeCalculator.calculate_range("SEMESTRAL", date(2026, 3, 15), mode="calendar") == (
            date(2026, 1, 1),
            date(2026, 6, 30),
        )

    def test_period_labels(self):
        assert PeriodRangeCalculator.get_period_label("SEMANAL") == "Semanal"
        assert PeriodRangeCalculator.get_period_label("QUINCENAL") == "Quincenal"
        assert PeriodRangeCalculator.get_period_label("MENSUAL") == "Mensual"
        assert PeriodRangeCalculator.get_period_label("TRIMESTRAL") == "Trimestral"
        assert PeriodRangeCalculator.get_period_label("SEMESTRAL") == "Semestral"


class TestExternalGlosasReportService:
    """Verifica el esquema configurable, filtros y agregaciones del servicio de informes."""

    def test_custom_schema_mapping_and_aggregation(self):
        schema = ExternalTableSchema()
        schema.configure(
            database_name="DGH_CLINICA",
            table_name="CRN_OBJECIONES_EXT",
            column_mapping={
                "id_glosa": "OID_GLOSA",
                "fecha_glosa": "FEC_RADICACION",
                "numero_factura": "NRO_CXC",
                "entidad_eps": "NOMBRE_TERCERO",
                "codigo_glosa": "COD_CONCEPTO",
                "concepto_glosa": "OBS_DETALLE",
                "valor_facturado": "VLR_FACTURA",
                "valor_glosado": "VLR_OBJETADO",
                "estado_glosa": "EST_ACTUAL",
            },
        )

        raw_rows = [
            {
                "OID_GLOSA": "101",
                "FEC_RADICACION": "2026-11-10",
                "NRO_CXC": "FC000010",
                "NOMBRE_TERCERO": "SANITAS",
                "COD_CONCEPTO": "TA0601",
                "OBS_DETALLE": "Diferencia de tarifa",
                "VLR_FACTURA": "1.000.000",
                "VLR_OBJETADO": "$250.000",
                "EST_ACTUAL": "PENDIENTE",
            },
            {
                "OID_GLOSA": "102",
                "FEC_RADICACION": "2026-11-15",
                "NRO_CXC": "FC000010",
                "NOMBRE_TERCERO": "SANITAS",
                "COD_CONCEPTO": "SO4801",
                "OBS_DETALLE": "Falta soporte",
                "VLR_FACTURA": "1.000.000",
                "VLR_OBJETADO": 100000,
                "EST_ACTUAL": "OBJETADA",
            },
            {
                "OID_GLOSA": "103",
                "FEC_RADICACION": "2026-08-01",  # Fuera de rango
                "NRO_CXC": "FC000099",
                "NOMBRE_TERCERO": "MUTUALSER",
                "COD_CONCEPTO": "FA0101",
                "OBS_DETALLE": "Antigua",
                "VLR_FACTURA": 300000,
                "VLR_OBJETADO": 50000,
                "EST_ACTUAL": "ACEPTADA",
            },
        ]

        service = ExternalGlosasReportService(
            schema=schema,
            custom_query_fn=lambda d, h, e: raw_rows,
        )
        report = service.fetch_report(
            periodicity="MENSUAL",
            fecha_desde="2026-11-01",
            fecha_hasta="2026-11-30",
        )

        assert report.database_name == "DGH_CLINICA"
        assert report.table_name == "CRN_OBJECIONES_EXT"
        assert report.is_preview_data is False
        assert report.total_glosas == 2
        assert report.total_facturas == 1
        # Deduplicación por factura: FC000010 vale 1.000.000 (no 2.000.000)
        assert report.valor_total_facturado == 1000000.0
        assert report.valor_total_glosado == 350000.0
        assert len(report.resumen_por_entidad) == 1
        assert report.resumen_por_entidad[0]["entidad"] == "SANITAS"
        assert report.resumen_por_entidad[0]["valor_facturado"] == 1000000.0

    def test_decimal_conversion_and_sql_fallback(self):
        assert _to_float(Decimal("19233090.0000")) == 19233090.0
        assert _to_float(Decimal("NaN")) == 0.0

        def _failing_provider(d, h, e):
            raise RuntimeError("Sin red hacia SQL")

        service = ExternalGlosasReportService(custom_query_fn=_failing_provider)
        report = service.fetch_report(
            periodicity="MENSUAL",
            fecha_desde="2026-11-01",
            fecha_hasta="2026-11-30",
        )
        assert report.is_preview_data is True
        assert "SQL no disponible" in report.source_note
        assert report.total_glosas > 0

    def test_dgh_sql_provider_query_and_mapping(self):
        fake_cursor = MagicMock()
        fake_cursor.description = [
            ("NumeroGlosaInterno",),
            ("FechaGlosa",),
            ("NumeroFactura",),
            ("Entidad",),
            ("CodigoMotivoGlosa",),
            ("MotivoGlosa",),
            ("ObservacionDetalle",),
            ("ObservacionGeneral",),
            ("ValorFacturado",),
            ("ValorGlosado",),
            ("ServicioGlosado",),
            ("NombreCentroCosto",),
            ("EstadoGlosa",),
        ]
        fake_cursor.fetchall.return_value = [
            (
                227964,
                datetime(2026, 10, 13, 0, 0),
                "FC0000815852",
                "SAVIA SALUD EPS",
                "TA0201",
                "Diferencia de tarifa",
                "Se objeta diferencia\r\nde tarifa",
                "REG, GLOSA SEGUN RAD",
                Decimal("19233090.0000"),
                Decimal("15224.0000"),
                "CUIDADO INTRAHOSPITALARIO",
                "HOSPITALIZACION PISO DOS",
                "CONFIRMADA",
            ),
            (
                227964,
                datetime(2026, 10, 13, 0, 0),
                "FC0000815852",
                "SAVIA SALUD EPS",
                "FA0101",
                "Cantidad facturada",
                "No facturable",
                "REG, GLOSA SEGUN RAD",
                Decimal("19233090.0000"),
                Decimal("69300.0000"),
                "TERAPIA TRANSFUSIONAL",
                "SERVICIO TRANSFUSIONAL",
                "CONFIRMADA",
            ),
        ]
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.service.dgh_sql_provider.pyodbc") as mock_pyodbc:
            mock_pyodbc.drivers.return_value = ["ODBC Driver 18 for SQL Server"]
            mock_pyodbc.connect.return_value = fake_conn

            provider = DghSqlGlosasProvider(
                server=r"diana\sql1",
                database="DGEMPRES91",
                username="user_dev",
                password="secret_for_unit_test",
            )
            records = provider.fetch_records("2026-10-01", "2026-10-31", entidad_filter="SAVIA")

            executed_sql, executed_params = fake_cursor.execute.call_args[0]
            assert "TOP 10" not in executed_sql.upper()
            assert "WITH (NOLOCK)" in executed_sql
            assert "rec.CROFECOBJ >= ?" in executed_sql
            assert "rec.CROFECOBJ < ?" in executed_sql
            assert executed_params[0] == date(2026, 10, 1)
            assert executed_params[1] == date(2026, 11, 1)  # inclusive hasta + 1 dia
            assert executed_params[2] == "%SAVIA%"
            fake_conn.close.assert_called_once()

        schema = ExternalTableSchema(
            database_name="DGEMPRES91",
            table_name="CRNRECOBJC",
            column_mapping=dict(DGH_GLOSAS_COLUMN_MAPPING),
        )
        svc = ExternalGlosasReportService(schema=schema)
        rep = svc.build_report_from_records(records, "PERSONALIZADO", "2026-10-01", "2026-10-31")
        assert rep.total_glosas == 2
        assert rep.total_facturas == 1
        assert rep.valor_total_facturado == 19233090.0
        assert rep.valor_total_glosado == 84524.0
        assert rep.registros[0]["servicio_glosado"] != ""
        assert rep.registros[0]["centro_costo"] != ""

    def test_dgh_sql_provider_fetch_breakdowns(self):
        fake_cursor = MagicMock()
        fake_cursor.fetchall.side_effect = [
            [("HABITACION BIPERSONAL", 49, 40, Decimal("54775700.0000"))],
            [("1103114921", "CARLOS MAYORIANO", 3164, 60, Decimal("349474372.0000"))],
            [("TA0201", "Diferencia tarifa", "Administrativo", 4631, 399, Decimal("307047334.0000"))],
        ]
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.service.dgh_sql_provider.pyodbc") as mock_pyodbc:
            mock_pyodbc.drivers.return_value = ["ODBC Driver 18 for SQL Server"]
            mock_pyodbc.connect.return_value = fake_conn

            provider = DghSqlGlosasProvider(
                server=r"diana\sql1",
                database="DGEMPRES91",
                username="user_dev",
                password="secret_for_unit_test",
            )
            bd = provider.fetch_breakdowns("2026-10-01", "2026-10-31")

            assert fake_cursor.execute.call_count == 3
            for call in fake_cursor.execute.call_args_list:
                sql_txt, sql_params = call[0]
                assert "rec.CROFECOBJ >= ?" in sql_txt
                assert "rec.CROFECOBJ < ?" in sql_txt
                assert sql_params == [date(2026, 10, 1), date(2026, 11, 1)]
            fake_conn.close.assert_called_once()

        assert bd["por_servicio"][0]["servicio_glosado"] == "HABITACION BIPERSONAL"
        assert bd["por_facturador"][0]["nombre_facturador"] == "CARLOS MAYORIANO"
        assert bd["top_conceptos"][0]["clase_objecion"] == "Administrativo"


class TestGlosasReportExporter:
    """Verifica la exportación física completa en Excel (5 hojas) y resumen PDF (2 tablas)."""

    def test_export_excel_all_sheets_and_pdf_two_tables(self, tmp_path: Path):
        service = ExternalGlosasReportService()
        many_records = []
        for idx in range(1, 46):
            many_records.append(
                {
                    "id_glosa": f"G-{idx:03d}",
                    "fecha_glosa": f"2026-11-{(idx % 20) + 1:02d}",
                    "numero_factura": f"FC0000{1000 + idx}",
                    "entidad_eps": "SANITAS" if idx % 2 == 0 else "MUTUALSER",
                    "codigo_glosa": "TA0601" if idx % 2 == 0 else "SO4801",
                    "concepto_glosa": f"Observación con tilde y ñ registro número {idx}",
                    "servicio_glosado": "CONSULTA EXTERNA" if idx % 2 == 0 else "URGENCIAS",
                    "estado_glosa": "PENDIENTE",
                    "valor_facturado": 1000000.0,
                    "valor_glosado": 200000.0,
                }
            )

        breakdowns = {
            "por_servicio": [
                {"servicio_glosado": "CONSULTA EXTERNA", "cantidad_glosas": 22, "facturas_afectadas": 22, "total_valor_glosado": 4400000.0},
                {"servicio_glosado": "URGENCIAS", "cantidad_glosas": 23, "facturas_afectadas": 23, "total_valor_glosado": 4600000.0},
            ],
            "por_facturador": [
                {"usuario_facturador": "U101", "nombre_facturador": "ANA PEREZ", "cantidad_items_glosados": 45, "facturas_glosadas": 45, "total_valor_glosado": 9000000.0},
            ],
            "top_conceptos": [
                {"codigo_concepto": "TA0601", "nombre_concepto": "Tarifa superior", "clase_objecion": "Administrativo", "cantidad_glosas": 22, "facturas_afectadas": 22, "total_valor_glosado": 4400000.0},
                {"codigo_concepto": "SO4801", "nombre_concepto": "Falta soporte", "clase_objecion": "Asistencial", "cantidad_glosas": 23, "facturas_afectadas": 23, "total_valor_glosado": 4600000.0},
            ],
        }

        report = service.build_report_from_records(
            records=many_records,
            periodicity="TRIMESTRAL",
            fecha_desde="2026-09-01",
            fecha_hasta="2026-11-30",
            breakdowns=breakdowns,
        )

        exporter = GlosasReportExporter(output_dir=str(tmp_path))

        # 1. Excel completo (5 hojas)
        xlsx_path = exporter.export_to_excel(report)
        assert Path(xlsx_path).exists()
        wb = openpyxl.load_workbook(xlsx_path)
        assert wb.sheetnames == [
            "Resumen del Informe",
            "Glosas por Servicio",
            "Glosas por Facturador",
            "Top Conceptos Objecion",
            "Detalle de Glosas",
        ]
        ws_res = wb["Resumen del Informe"]
        assert ws_res["B2"].value == "Trimestral"
        assert ws_res["A8"].value == 45
        assert wb["Glosas por Servicio"]["A2"].value == "URGENCIAS"
        assert wb["Glosas por Facturador"]["B2"].value == "ANA PEREZ"
        assert wb["Top Conceptos Objecion"]["C2"].value == "Asistencial"
        ws_det = wb["Detalle de Glosas"]
        assert ws_det.max_row == 46  # 1 cabecera + 45 registros
        headers = [ws_det.cell(1, c).value for c in range(1, 12)]
        assert "Servicio Glosado" in headers
        assert "Centro de Costo" in headers

        # 2. PDF resumen ejecutivo (Entidades, Conceptos y Facturadores; sin detalle individual)
        pdf_path = exporter.export_to_pdf(report)
        pdf_file = Path(pdf_path)
        assert pdf_file.exists()
        raw_bytes = pdf_file.read_bytes()
        assert raw_bytes.startswith(b"%PDF-1.4")

        reader = PdfReader(str(pdf_file))
        full_text = "\n".join(p.extract_text() or "" for p in reader.pages)
        assert "CLINICA LA CONCEPCION" in full_text
        assert "Tabla 1. Resumen por Entidad / EPS" in full_text
        assert "Tabla 2. Top Conceptos de Objecion" in full_text
        assert "Tabla 3. Glosas por Facturador" in full_text
        assert "ANA PEREZ" in full_text
        assert "Resumen ejecutivo (Entidades, Conceptos y Facturadores)" in full_text
        assert "FC00001001" not in full_text  # El detalle no se vuelca en PDF

    def test_pdf_remains_compact_summary_with_many_records(self, tmp_path: Path):
        service = ExternalGlosasReportService()
        many_records = [
            {
                "id_glosa": f"G-{idx:04d}",
                "fecha_glosa": "2026-10-10",
                "numero_factura": f"FC{idx:05d}",
                "entidad_eps": f"ENTIDAD_{idx % 18}",
                "codigo_glosa": f"C{idx % 15:02d}",
                "concepto_glosa": f"Concepto {idx % 15}",
                "usuario_auditor": f"FACTURADOR_{idx % 12}",
                "estado_glosa": "CONFIRMADA",
                "valor_facturado": 100000.0,
                "valor_glosado": 10000.0,
            }
            for idx in range(520)
        ]
        report = service.build_report_from_records(
            many_records,
            periodicity="MENSUAL",
            fecha_desde="2026-10-01",
            fecha_hasta="2026-10-31",
        )
        exporter = GlosasReportExporter(output_dir=str(tmp_path))
        pdf_path = exporter.export_to_pdf(report)
        reader = PdfReader(pdf_path)
        assert len(reader.pages) <= 2
        full_text = "\n".join(p.extract_text() or "" for p in reader.pages)
        assert "Tabla 1. Resumen por Entidad / EPS" in full_text
        assert "Tabla 2. Top Conceptos de Objecion" in full_text
        assert "Tabla 3. Glosas por Facturador" in full_text
        assert "FC00500" not in full_text


class TestDashboardReportTabIntegration:
    """Verifica que el módulo exista como Tab independiente dentro del Dashboard."""

    def test_dashboard_has_report_tab_and_switches_cleanly(self, tmp_path: Path):
        mock_page = MagicMock()
        mock_page.client_storage = MagicMock()
        mock_page.client_storage.get.return_value = None
        mock_page.overlay = []

        offline_service = ExternalGlosasReportService()
        with patch("app.ui.views.glosas_report_tab_view.default_report_service", offline_service):
            dashboard = AnalyticsDashboardView(page=mock_page)
        assert len(dashboard._tabs.tabs) == 3
        assert dashboard._tabs.tabs[2].text == "Informe de Glosas"

        # Cambiar al Tab del Informe (modo offline usa load_report_sync)
        dashboard._tabs.selected_index = 2
        dashboard._on_tab_change(None)

        assert dashboard._filters_bar.visible is False
        assert dashboard._kpi_row.visible is False
        assert dashboard._tab_content_area.content is dashboard._report_tab_view.container
        assert dashboard._report_tab_view._current_report is not None
        assert dashboard._report_tab_view._current_report.total_glosas > 0

        # Volver al Tab 0 restaura filtros generales y KPIs
        dashboard._tabs.selected_index = 0
        dashboard._on_tab_change(None)
        assert dashboard._filters_bar.visible is True
        assert dashboard._kpi_row.visible is True

    def test_report_tab_standalone_export_with_custom_exporter(self, tmp_path: Path):
        mock_page = MagicMock()
        mock_page.overlay = []
        exporter = GlosasReportExporter(output_dir=str(tmp_path))
        offline_service = ExternalGlosasReportService()
        tab_view = GlosasReportTabView(page=mock_page, report_service=offline_service, exporter=exporter)

        tab_view.ensure_loaded(sync=True)
        assert tab_view._current_report is not None

        # Cambiar periodicidad a SEMESTRAL
        tab_view._period_dropdown.value = "SEMESTRAL"
        tab_view._on_periodicity_change(None)
        report = tab_view.load_report_sync()
        assert report.periodicity == "SEMESTRAL"

        xlsx_path = tab_view.exporter.export_to_excel(report)
        pdf_path = tab_view.exporter.export_to_pdf(report)
        assert Path(xlsx_path).exists()
        assert Path(pdf_path).exists()

    def test_search_filter_and_pagination(self, tmp_path: Path):
        mock_page = MagicMock()
        mock_page.overlay = []
        exporter = GlosasReportExporter(output_dir=str(tmp_path))

        records = [
            {
                "id_glosa": f"G-{idx:03d}",
                "fecha_glosa": "2026-10-12",
                "numero_factura": f"FC{1000 + idx}",
                "entidad_eps": "SANITAS" if idx % 2 == 0 else "MUTUALSER",
                "codigo_glosa": "TA0201" if idx == 77 else "SO4801",
                "concepto_glosa": "Concepto especial unico" if idx == 77 else f"Detalle #{idx}",
                "estado_glosa": "CONFIRMADA",
                "valor_facturado": 500000.0,
                "valor_glosado": 80000.0,
            }
            for idx in range(120)
        ]

        service = ExternalGlosasReportService(custom_query_fn=lambda d, h, e: records)
        tab_view = GlosasReportTabView(page=mock_page, report_service=service, exporter=exporter)
        tab_view._desde_field.value = "2026-10-01"
        tab_view._hasta_field.value = "2026-10-31"
        report = tab_view.load_report_sync()

        # Cuando SQL está conectado (no preview), el banner amarillo no ocupa espacio
        assert report.is_preview_data is False
        assert tab_view._status_pill.visible is True
        assert tab_view._schema_banner.visible is False

        # Paginación (120 registros / 50 por página = 3 páginas)
        assert tab_view._page_index == 0
        tab_view._go_page(1)
        assert tab_view._page_index == 1
        tab_view._go_page(1)
        assert tab_view._page_index == 2
        tab_view._go_page(1)  # Tope en última página
        assert tab_view._page_index == 2

        # Buscador rápido local reinicia a página 0 y filtra en memoria
        tab_view._search_field.value = "FC1077"
        tab_view._on_search_change(None)
        assert tab_view._page_index == 0
        filtered = tab_view._get_filtered_registros()
        assert len(filtered) == 1
        assert filtered[0]["codigo_glosa"] == "TA0201"

        # Cambiar entre sub-vistas (servicios, facturadores, conceptos)
        tab_view._search_field.value = ""
        tab_view._search_query = ""
        tab_view._set_subview("servicios")
        assert tab_view._active_subview == "servicios"
        assert len(tab_view._get_filtered_subview_items()) >= 1

        tab_view._set_subview("facturadores")
        assert tab_view._active_subview == "facturadores"
        assert len(tab_view._get_filtered_subview_items()) >= 1

        tab_view._set_subview("conceptos")
        assert tab_view._active_subview == "conceptos"
        assert len(tab_view._get_filtered_subview_items()) == 2
