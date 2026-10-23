"""
Servicio de gestión de emails
Orquesta las operaciones entre IMAP y adjuntos
"""
import os

from app.config.settings import HOMOLOGADOR_FILES, NETWORK_PATHS, logger
from app.core.imap_client import ImapClient
from app.core.mutualser_processor import MutualserProcessor
from app.service.attachment_service import AttachmentService
from app.service.processors.coosalud_processor import CoosaludProcessor
from app.service.processors.sanitas_processor import SanitasProcessor


class EmailService:
    """Servicio principal para gestionar correos electrónicos"""

    # Rutas de red para salida de archivos
    MUTUALSER_OUTPUT_RED = r"\\MINERVA\Cartera\GLOSAAP\REPOSITORIO DE RESULTADOS\MUTUALSER"

    def __init__(self):
        self.imap_client = None
        # AttachmentService usa directorio temporal del sistema (donde ya tienes archivos)
        self.attachment_service = AttachmentService()  # Sin base_dir = usa temporal
        self.messages = []

        # Procesadores por EPS - usar ruta de red MINERVA
        mutualser_output = self._get_output_path(self.MUTUALSER_OUTPUT_RED, "outputs/mutualser")
        self.mutualser_processor = MutualserProcessor(output_dir=mutualser_output)
        logger.debug("MUTUALSER guardara en: %s", mutualser_output)

        # Procesador COOSALUD - fuente unica de rutas en app/config/settings.py
        coosalud_output = self._get_output_path(
            NETWORK_PATHS.get("coosalud_output", "outputs/coosalud"),
            "outputs/coosalud",
        )
        self.coosalud_output_dir = coosalud_output
        coosalud_homologador = HOMOLOGADOR_FILES.get("coosalud", "")
        # Si el homologador de red no existe (entorno local/tests), iniciar sin
        # homologador para permitir procesamiento sin homologacion en lugar de
        # fallar siempre en load_homologador.
        if coosalud_homologador and not os.path.exists(coosalud_homologador):
            logger.warning(
                "Homologador Coosalud no encontrado (%s); se continua sin homologacion",
                coosalud_homologador,
            )
            coosalud_homologador = ""
        self.coosalud_processor = CoosaludProcessor(homologador_path=coosalud_homologador)
        logger.info("COOSALUD guardara en: %s", coosalud_output)

        # Procesador SANITAS - fuente unica de rutas en app/config/settings.py
        sanitas_output = self._get_output_path(
            NETWORK_PATHS.get("sanitas_output", "outputs/sanitas"),
            "outputs/sanitas",
        )
        self.sanitas_output_dir = sanitas_output
        sanitas_homologador = self._resolve_homologador("sanitas", "Sanitas")
        sanitas_insumos = self._resolve_homologador("sanitas_insumos", "Sanitas insumos")
        self.sanitas_processor = SanitasProcessor(
            homologador_path=sanitas_homologador,
            homologador_insumos_path=sanitas_insumos,
        )
        logger.info("SANITAS guardara en: %s", sanitas_output)

    def _resolve_homologador(self, key: str, label: str) -> str:
        """Resuelve ruta de homologador con fallback a "" si no existe.

        Fuente única: app/config/settings.py (HOMOLOGADOR_FILES).
        """
        path = HOMOLOGADOR_FILES.get(key, "")
        # Si el homologador de red no existe (entorno local/tests), iniciar sin
        # homologador para permitir procesamiento sin homologacion.
        if path and not os.path.exists(path):
            logger.warning(
                "Homologador %s no encontrado (%s); se continua sin homologacion",
                label,
                path,
            )
            path = ""
        return path

    def _get_output_path(self, network_path, fallback_path):
        """
        Intenta usar ruta de red, si no está disponible usa fallback local
        """
        try:
            # Verificar si la ruta de red existe o se puede crear
            if os.path.exists(network_path):
                return network_path

            # Intentar crear la ruta de red
            os.makedirs(network_path, exist_ok=True)
            if os.path.exists(network_path):
                logger.debug("Ruta de red accesible: %s", network_path)
                return network_path
        except Exception as e:
            logger.warning("Red no accesible (%s), usando local: %s", e, fallback_path)

        # Fallback a ruta local
        os.makedirs(fallback_path, exist_ok=True)
        return fallback_path

    def connect(self, email, password, server="imap.gmail.com", port=993):
        """Conecta al servidor IMAP"""
        self.imap_client = ImapClient()
        self.imap_client.connect(email, password, server, port)
        return True


    def search_messages(self, keyword, limit=None, timeout=120, on_found=None, date_from=None, date_to=None, from_addr=None):
        """
        Busca mensajes por palabra clave en el asunto con filtros opcionales.

        Args:
            keyword (str): Palabra clave a buscar en el asunto. Ej: "MUTUALSER", "Glosa"
            limit (int, optional): Límite máximo de mensajes a retornar. None = sin límite
            timeout (int): Tiempo máximo de búsqueda en segundos (default: 120)
            on_found (callable, optional): Función callback(message) ejecutada al encontrar cada mensaje
            date_from (datetime|str, optional): Fecha inicio del rango. Formato: datetime o 'YYYY-MM-DD'
            date_to (datetime|str, optional): Fecha fin del rango. Formato: datetime o 'YYYY-MM-DD'
            from_addr (str, optional): Remitente para filtrar a nivel IMAP (FROM).
                None = sin filtro por remitente (comportamiento anterior).

        Returns:
            list: Lista de diccionarios con información de mensajes encontrados.
                  Cada mensaje contiene: {'id', 'subject', 'from', 'date', 'has_attachments'}

        Raises:
            Exception: Si no hay conexión IMAP establecida

        Examples:
            >>> # Búsqueda básica
            >>> messages = email_service.search_messages("MUTUALSER")
            >>>
            >>> # Búsqueda con límite y callback
            >>> def on_message(msg):
            ...     print(f"Encontrado: {msg['subject']}")
            >>> messages = email_service.search_messages("Glosa", limit=10, on_found=on_message)
            >>>
            >>> # Búsqueda con rango de fechas
            >>> from datetime import datetime, timedelta
            >>> yesterday = datetime.now() - timedelta(days=1)
            >>> messages = email_service.search_messages(
            ...     "MUTUALSER",
            ...     date_from=yesterday,
            ...     date_to=datetime.now()
            ... )
            >>>
            >>> # Búsqueda con fechas como strings
            >>> messages = email_service.search_messages(
            ...     "Respuesta Glosa",
            ...     date_from="2024-01-01",
            ...     date_to="2024-01-31"
            ... )
        """
        if not self.imap_client:
            raise Exception("No hay conexión IMAP establecida")

        logger.debug("Buscando: keyword='%s', limit=%s, timeout=%s", keyword, limit, timeout)
        logger.debug("Rango: %s hasta %s", date_from, date_to)

        self.messages = self.imap_client.search_by_subject(
            keyword,
            limit=limit,
            timeout=timeout,
            on_found=on_found,
            date_from=date_from,
            date_to=date_to,
            from_addr=from_addr
        )
        return self.messages

    def download_message_attachments(self, message_id, email_date=None):
        """
        Descarga todos los adjuntos de un mensaje específico al directorio temporal.

        Args:
            message_id (str): ID único del mensaje en el servidor IMAP
            email_date (str, optional): Fecha del correo en formato '%Y-%m-%d %H:%M:%S'

        Returns:
            list: Lista de rutas absolutas de archivos descargados exitosamente.
                  Retorna lista vacía si no hay adjuntos o fallan todas las descargas.

        Raises:
            Exception: Si no hay conexión IMAP establecida

        Examples:
            >>> # Descargar adjuntos de un mensaje específico con fecha
            >>> message_id = "12345"
            >>> email_date = "2026-02-05 10:30:00"
            >>> files = email_service.download_message_attachments(message_id, email_date=email_date)
            >>> print(f"Descargados {len(files)} archivos:")
            >>> for file_path in files:
            ...     print(f"  - {os.path.basename(file_path)}")
            >>>
            >>> # Verificar si se descargaron archivos
            >>> if files:
            ...     print(f"Primer archivo: {files[0]}")
            ...     print(f"Tamaño: {os.path.getsize(files[0])} bytes")
            ... else:
            ...     print("No se descargaron adjuntos")

        Note:
            - Los archivos se descargan al directorio temporal del AttachmentService
            - Los nombres de archivo duplicados se renombran automáticamente
            - Los archivos se agregan automáticamente al registro de la sesión actual
            - Si se proporciona email_date, se guarda en los metadatos de cada archivo
        """
        if not self.imap_client:
            raise Exception("No hay conexión IMAP establecida")

        saved_files = self.imap_client.download_attachments(
            message_id,
            dest_dir=self.attachment_service.base_dir
        )

        if saved_files:
            # Crear metadata con fecha del correo si está disponible
            metadata = {}
            if email_date:
                for file_path in saved_files:
                    metadata[file_path] = {
                        "email_date": email_date,
                        "message_id": message_id
                    }

            self.attachment_service.add_files(saved_files, metadata=metadata)

        return saved_files

    def download_all_attachments(self, messages=None, on_progress=None):
        """
        Descarga adjuntos de múltiples mensajes con seguimiento de progreso detallado.

        Args:
            messages (list, optional): Lista de mensajes a procesar. Si None, usa self.messages
                                     de la última búsqueda realizada
            on_progress (callable, optional): Función callback(idx, total, message, files)
                                            ejecutada después de procesar cada mensaje

        Returns:
            dict: Estadísticas detalladas de la descarga con las siguientes claves:
                - total_messages (int): Número total de mensajes procesados
                - messages_with_attachments (int): Mensajes que tenían adjuntos
                - total_files (int): Número total de archivos descargados
                - errors (int): Número de errores encontrados

        Raises:
            Exception: Si no hay conexión IMAP establecida

        Examples:
            >>> # Descarga básica sin callback
            >>> stats = email_service.download_all_attachments()
            >>> print(f"Procesados {stats['total_messages']} mensajes")
            >>> print(f"Descargados {stats['total_files']} archivos")
            >>>
            >>> # Descarga con seguimiento de progreso
            >>> def show_progress(idx, total, message, files):
            ...     progress = (idx + 1) / total * 100
            ...     print(f"[{progress:.1f}%] {message['subject']}: {len(files)} archivos")
            >>>
            >>> stats = email_service.download_all_attachments(on_progress=show_progress)
            >>>
            >>> # Descarga de mensajes específicos con análisis detallado
            >>> messages = email_service.search_messages("MUTUALSER", limit=5)
            >>>
            >>> def detailed_progress(idx, total, msg, files):
            ...     print(f"Mensaje {idx+1}/{total}: {msg['from']}")
            ...     print(f"  Asunto: {msg['subject'][:50]}...")
            ...     print(f"  Adjuntos: {len(files)}")
            ...     for file_path in files:
            ...         size_mb = os.path.getsize(file_path) / (1024*1024)
            ...         print(f"    - {os.path.basename(file_path)} ({size_mb:.2f} MB)")
            >>>
            >>> stats = email_service.download_all_attachments(
            ...     messages=messages,
            ...     on_progress=detailed_progress
            ... )
            >>>
            >>> # Verificar resultados
            >>> if stats['errors'] > 0:
            ...     print(f"⚠️ {stats['errors']} errores durante la descarga")
            >>> print(f"✅ Descarga completada: {stats['total_files']} archivos")

        Note:
            - El proceso continúa aunque algunos mensajes fallen
            - Los errores se registran en la consola y en stats['errors']
            - Los archivos se descargan al directorio temporal del AttachmentService
        """
        msgs = messages or self.messages
        stats = {
            "total_messages": len(msgs),
            "messages_with_attachments": 0,
            "total_files": 0,
            "errors": 0
        }
        # Dedupe por asunto normalizado dentro de esta corrida: evita
        # descargar dos veces el mismo correo reenviado/duplicado.
        seen_subjects = set()

        for idx, msg in enumerate(msgs):
            try:
                subject_key = str(msg.get("subject") or "").lower().strip()
                import re as _re
                subject_key = _re.sub(r"\s+", " ", subject_key)
                if subject_key and subject_key in seen_subjects:
                    logger.debug(
                        "Asunto duplicado, se omite descarga: %s",
                        (msg.get("subject") or "")[:60],
                    )
                    if on_progress:
                        on_progress(idx, len(msgs), msg, [])
                    continue
                if subject_key:
                    seen_subjects.add(subject_key)
                # Extraer fecha del correo si está disponible
                email_date = None
                if "date" in msg and msg["date"]:
                    from datetime import datetime
                    msg_date = msg["date"]
                    try:
                        # Intentar convertir a formato estándar
                        if isinstance(msg_date, str):
                            for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                                try:
                                    parsed = datetime.strptime(msg_date.strip(), fmt)
                                    email_date = parsed.strftime('%Y-%m-%d %H:%M:%S')
                                    break
                                except ValueError:
                                    continue
                        elif hasattr(msg_date, 'strftime'):
                            email_date = msg_date.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        pass

                files = self.download_message_attachments(msg["id"], email_date=email_date)

                if files:
                    stats["messages_with_attachments"] += 1
                    stats["total_files"] += len(files)

                if on_progress:
                    on_progress(idx, len(msgs), msg, files)

            except Exception as e:
                stats["errors"] += 1
                logger.warning("Error descargando adjuntos del mensaje %s: %s", msg.get("id"), e)

        return stats

    def get_attachment_summary(self):
        """Obtiene resumen de adjuntos descargados"""
        return self.attachment_service.get_summary()

    def get_excel_files(self, exclude_devoluciones=True, session_only=True):
        """
        Obtiene archivos Excel/CSV descargados

        Args:
            exclude_devoluciones: Excluir archivos de devolución
            session_only: Si True, solo retorna archivos de la sesión actual
        """
        if session_only:
            return self.attachment_service.get_session_excel_files(exclude_devoluciones=exclude_devoluciones)
        return self.attachment_service.get_excel_files(exclude_devoluciones=exclude_devoluciones)

    def clear_session(self):
        """Limpia los archivos de la sesión actual (para nueva búsqueda)"""
        return self.attachment_service.clear_session()

    def clear_attachments(self):
        """Limpia todos los archivos descargados del directorio temporal"""
        return self.attachment_service.clear_all()

    def disconnect(self):
        """Cierra la conexión IMAP"""
        if self.imap_client:
            self.imap_client.logout()
            self.imap_client = None

    # Métodos específicos para procesamiento de EPS

    def procesar_mutualser(self, archivos=None):
        """
        Procesa archivos de respuesta de glosas de MUTUALSER y genera Excel consolidado
        con objeciones separadas por tipo.

        Args:
            archivos (list, optional): Lista de rutas de archivos Excel a procesar.
                                     Si None, usa archivos Excel descargados en la sesión actual.

        Returns:
            dict: Resultado del procesamiento con las siguientes claves:
                - success (bool): True si el procesamiento fue exitoso
                - message (str): Mensaje descriptivo (solo si success=False)
                - output_file (str): Ruta del archivo consolidado generado
                - objeciones_file (str): Ruta del archivo de objeciones generado
                - resumen (dict): Estadísticas del procesamiento

        Examples:
            >>> # Procesamiento automático de archivos descargados
            >>> # (después de search_messages y download_all_attachments)
            >>> resultado = email_service.procesar_mutualser()
            >>> if resultado['success']:
            ...     print(f"Consolidado: {resultado['output_file']}")
            ...     print(f"Objeciones: {resultado['objeciones_file']}")
            ...     print(f"Procesados: {resultado['resumen']['total_registros']} registros")
            >>>
            >>> # Procesamiento de archivos específicos
            >>> archivos_mutualser = [
            ...     "C:/temp/respuesta_glosa_001.xlsx",
            ...     "C:/temp/respuesta_glosa_002.xlsx"
            ... ]
            >>> resultado = email_service.procesar_mutualser(archivos_mutualser)
            >>>
            >>> # Análisis del resultado
            >>> if resultado['success']:
            ...     resumen = resultado['resumen']
            ...     print(f"📊 Resumen del procesamiento:")
            ...     print(f"   Total registros: {resumen['total_registros']}")
            ...     print(f"   Glosas aprobadas: {resumen.get('aprobadas', 0)}")
            ...     print(f"   Glosas objetadas: {resumen.get('objetadas', 0)}")
            ...     print(f"   Archivos procesados: {len(archivos_mutualser)}")
            ... else:
            ...     print(f"❌ Error: {resultado['message']}")
            >>>
            >>> # Verificar archivos generados
            >>> import os
            >>> if resultado['success']:
            ...     output_path = resultado['output_file']
            ...     if os.path.exists(output_path):
            ...         size_mb = os.path.getsize(output_path) / (1024*1024)
            ...         print(f"Archivo consolidado: {size_mb:.2f} MB")

        Note:
            - Los archivos se procesan y consolidan según la estructura de MUTUALSER
            - Se genera automáticamente un archivo separado para objeciones
            - Los archivos resultantes se guardan en la ruta de red MINERVA si está disponible
            - Si no se especifican archivos, usa solo archivos Excel de la sesión actual
            - Excluye automáticamente archivos de devolución
        """
        # Si no se especifican archivos, usar los Excel descargados
        if archivos is None:
            archivos = self.get_excel_files()

        if not archivos:
            return {
                'success': False,
                'message': 'No hay archivos para procesar'
            }

        # Procesar archivos
        df = self.mutualser_processor.procesar_multiples_archivos(archivos)

        if df is None or df.empty:
            return {
                'success': False,
                'message': 'No se pudo procesar ningún archivo'
            }

        # Exportar consolidado y generar archivo de objeciones
        resultado = self.mutualser_processor.exportar_consolidado()

        if resultado:
            output_path, objeciones_path = resultado
            resumen = self.mutualser_processor.get_resumen()
            return {
                'success': True,
                'output_file': output_path,
                'objeciones_file': objeciones_path,
                'resumen': resumen
            }
        else:
            return {
                'success': False,
                'message': 'Error al exportar archivos'
            }

    def procesar_cosalud(self, archivos=None, email_date=None):
        """
        Procesa archivos de respuesta de glosas de COOSALUD y genera Excel consolidado.

        Usa CoosaludProcessor con el mismo contrato que procesar_mutualser para
        que el caller (app/ui/app.py) pueda tratar ambos EPS de forma uniforme.

        Args:
            archivos (list, optional): Lista de rutas de archivos Excel a procesar.
                Si None, usa archivos Excel descargados en la sesion actual
                (excluyendo devoluciones).
            email_date (str, optional): Fecha del correo en formato
                '%Y-%m-%d %H:%M:%S'. Si None, se usan los metadatos
                individuales de attachment_service con fallback a fecha actual.

        Returns:
            dict: Resultado del procesamiento con las siguientes claves:
                - success (bool): True si el procesamiento fue exitoso
                - message (str): Mensaje descriptivo del resultado
                - output_file (str): Ruta del archivo consolidado generado
                - objeciones_file (str|None): Ruta del archivo de objeciones
                - path (str): Alias de output_file para compatibilidad
                - resumen (dict): Estadisticas del procesamiento
        """
        # Si no se especifican archivos, usar los Excel descargados (sin devoluciones)
        if archivos is None:
            archivos = self.get_excel_files(
                exclude_devoluciones=True, session_only=True
            )

        if not archivos:
            return {
                'success': False,
                'message': 'No hay archivos para procesar'
            }

        # Asegurar procesador disponible (compatibilidad con instancias antiguas)
        if not hasattr(self, 'coosalud_processor') or self.coosalud_processor is None:
            coosalud_homologador = HOMOLOGADOR_FILES.get("coosalud", "")
            if coosalud_homologador and not os.path.exists(coosalud_homologador):
                logger.warning(
                    "Homologador Coosalud no encontrado (%s); se continua sin homologacion",
                    coosalud_homologador,
                )
                coosalud_homologador = ""
            self.coosalud_processor = CoosaludProcessor(
                homologador_path=coosalud_homologador
            )
        if not hasattr(self, 'coosalud_output_dir') or not self.coosalud_output_dir:
            self.coosalud_output_dir = self._get_output_path(
                NETWORK_PATHS.get("coosalud_output", "outputs/coosalud"),
                "outputs/coosalud",
            )

        output_dir = self.coosalud_output_dir
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as exc:
            logger.warning("No se pudo crear directorio Coosalud %s: %s", output_dir, exc)

        # Registrar archivos existentes para detectar los generados en esta corrida
        try:
            archivos_previos = set(os.listdir(output_dir)) if os.path.exists(output_dir) else set()
        except Exception:
            archivos_previos = set()

        try:
            result_data, message = self.coosalud_processor.process_glosas(
                archivos,
                output_dir=output_dir,
                email_date=email_date,
                attachment_service=self.attachment_service,
            )
        except Exception as exc:
            logger.exception("Error al procesar Coosalud: %s", exc)
            return {
                'success': False,
                'message': f'Error al procesar archivos de Coosalud: {exc}'
            }

        if result_data is None:
            return {
                'success': False,
                'message': message or 'No se pudo procesar ningun archivo'
            }

        detalle_df = result_data.get("detalle") if isinstance(result_data, dict) else None
        glosa_df = result_data.get("glosa") if isinstance(result_data, dict) else None
        total_detalles = len(detalle_df) if detalle_df is not None else 0
        total_glosas = len(glosa_df) if glosa_df is not None else 0

        # Localizar archivos generados (consolidado + objeciones)
        output_file = None
        objeciones_file = None
        try:
            actuales = os.listdir(output_dir) if os.path.exists(output_dir) else []
            nuevos = [f for f in actuales if f not in archivos_previos]
            candidatos = nuevos if nuevos else actuales

            consolidados = [
                os.path.join(output_dir, f) for f in candidatos
                if f.startswith("COOSALUD_GLOSAS_") and f.endswith(".xlsx")
            ]
            objeciones = [
                os.path.join(output_dir, f) for f in candidatos
                if f.startswith("Objeciones_COOSALUD_") and f.endswith(".xlsx")
            ]
            if consolidados:
                output_file = max(consolidados, key=os.path.getmtime)
            if objeciones:
                objeciones_file = max(objeciones, key=os.path.getmtime)
        except Exception as exc:
            logger.warning("No se pudieron localizar archivos generados: %s", exc)

        # Construir resumen compatible con procesar_mutualser
        try:
            facturas_unicas = 0
            if detalle_df is not None and not detalle_df.empty:
                if "_FACTURA" in detalle_df.columns:
                    facturas_unicas = int(detalle_df["_FACTURA"].nunique())
                else:
                    for col in ("numero_factura", "numero factura", "factura"):
                        if col in detalle_df.columns:
                            facturas_unicas = int(detalle_df[col].nunique())
                            break
            codigos_homologados = 0
            if detalle_df is not None and "Codigo homologado DGH" in detalle_df.columns:
                codigos_homologados = int((detalle_df["Codigo homologado DGH"] != "").sum())
        except Exception:
            facturas_unicas = 0
            codigos_homologados = 0

        resumen = {
            'total_registros': total_detalles,
            'total_detalles': total_detalles,
            'total_glosas': total_glosas,
            'archivos_procesados': len(archivos),
            'facturas_unicas': facturas_unicas,
            'codigos_homologados': codigos_homologados,
            'errores': len(getattr(self.coosalud_processor, 'errors', []) or []),
        }

        logger.info(
            "Coosalud procesado: %s detalles, %s glosas, %s archivos",
            total_detalles, total_glosas, len(archivos),
        )

        return {
            'success': True,
            'message': message or 'Procesamiento Coosalud completado',
            'output_file': output_file,
            'objeciones_file': objeciones_file,
            'path': output_file,
            'resumen': resumen,
        }

    def procesar_sanitas(self, archivos=None, email_date=None):
        """
        Procesa archivos de respuesta de glosas de SANITAS y genera Excel consolidado.

        Usa SanitasProcessor con el mismo contrato que procesar_cosalud para
        que el caller (app/ui/app.py) pueda tratar ambos EPS de forma uniforme.
        Solo se procesan .xlsx (el PDF adjunto se ignora tanto en
        get_excel_files como en identify_files del procesador).

        Args:
            archivos (list, optional): Lista de rutas de archivos Excel a procesar.
                Si None, usa archivos Excel descargados en la sesion actual
                (excluyendo devoluciones; los PDF ya quedan excluidos).
            email_date (str, optional): Fecha del correo en formato
                '%Y-%m-%d %H:%M:%S'. Si None, se usan los metadatos
                individuales de attachment_service con fallback a fecha actual.

        Returns:
            dict: Resultado del procesamiento con las siguientes claves:
                - success (bool): True si el procesamiento fue exitoso
                - message (str): Mensaje descriptivo del resultado
                - output_file (str): Ruta del archivo consolidado generado
                - objeciones_file (str|None): Ruta del archivo de objeciones
                - path (str): Alias de output_file para compatibilidad
                - resumen (dict): Estadisticas del procesamiento
        """
        # Si no se especifican archivos, usar los Excel descargados (sin devoluciones;
        # get_excel_files ya excluye los PDF por extension).
        if archivos is None:
            archivos = self.get_excel_files(
                exclude_devoluciones=True, session_only=True
            )

        if not archivos:
            return {
                'success': False,
                'message': 'No hay archivos para procesar'
            }

        # Asegurar procesador disponible (compatibilidad con instancias antiguas)
        if not hasattr(self, 'sanitas_processor') or self.sanitas_processor is None:
            sanitas_homologador = self._resolve_homologador("sanitas", "Sanitas")
            sanitas_insumos = self._resolve_homologador("sanitas_insumos", "Sanitas insumos")
            self.sanitas_processor = SanitasProcessor(
                homologador_path=sanitas_homologador,
                homologador_insumos_path=sanitas_insumos,
            )
        if not hasattr(self, 'sanitas_output_dir') or not self.sanitas_output_dir:
            self.sanitas_output_dir = self._get_output_path(
                NETWORK_PATHS.get("sanitas_output", "outputs/sanitas"),
                "outputs/sanitas",
            )

        output_dir = self.sanitas_output_dir
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as exc:
            logger.warning("No se pudo crear directorio Sanitas %s: %s", output_dir, exc)

        # Registrar archivos existentes para detectar los generados en esta corrida
        try:
            archivos_previos = set(os.listdir(output_dir)) if os.path.exists(output_dir) else set()
        except Exception:
            archivos_previos = set()

        try:
            result_data, message = self.sanitas_processor.process_glosas(
                archivos,
                output_dir=output_dir,
                email_date=email_date,
                attachment_service=self.attachment_service,
            )
        except Exception as exc:
            logger.exception("Error al procesar Sanitas: %s", exc)
            return {
                'success': False,
                'message': f'Error al procesar archivos de Sanitas: {exc}'
            }

        if result_data is None:
            return {
                'success': False,
                'message': message or 'No se pudo procesar ningun archivo'
            }

        detalle_df = result_data.get("detalle") if isinstance(result_data, dict) else None
        glosa_df = None
        if isinstance(result_data, dict):
            glosa_df = result_data.get("objeciones", result_data.get("glosa"))
        total_detalles = len(detalle_df) if detalle_df is not None else 0
        total_glosas = len(glosa_df) if glosa_df is not None else 0

        # Localizar archivos generados (consolidado + objeciones)
        output_file = None
        objeciones_file = None
        try:
            actuales = os.listdir(output_dir) if os.path.exists(output_dir) else []
            nuevos = [f for f in actuales if f not in archivos_previos]
            candidatos = nuevos if nuevos else actuales

            consolidados = [
                os.path.join(output_dir, f) for f in candidatos
                if f.startswith("SANITAS_GLOSAS_") and f.endswith(".xlsx")
            ]
            objeciones = [
                os.path.join(output_dir, f) for f in candidatos
                if f.startswith("Objeciones_SANITAS_") and f.endswith(".xlsx")
            ]
            if consolidados:
                output_file = max(consolidados, key=os.path.getmtime)
            if objeciones:
                objeciones_file = max(objeciones, key=os.path.getmtime)
        except Exception as exc:
            logger.warning("No se pudieron localizar archivos generados: %s", exc)

        # Construir resumen compatible con procesar_mutualser/procesar_cosalud
        try:
            facturas_unicas = 0
            if detalle_df is not None and not detalle_df.empty:
                if "_FACTURA" in detalle_df.columns:
                    facturas_unicas = int(detalle_df["_FACTURA"].nunique())
                elif "CRNCXC" in detalle_df.columns:
                    facturas_unicas = int(detalle_df["CRNCXC"].nunique())
            codigos_homologados = 0
            if detalle_df is not None and "SLNSERPRO" in detalle_df.columns:
                codigos_homologados = int((detalle_df["SLNSERPRO"] != "").sum())
        except Exception:
            facturas_unicas = 0
            codigos_homologados = 0

        resumen = {
            'total_registros': total_detalles,
            'total_detalles': total_detalles,
            'total_glosas': total_glosas,
            'archivos_procesados': len(archivos),
            'facturas_unicas': facturas_unicas,
            'codigos_homologados': codigos_homologados,
            'errores': len(getattr(self.sanitas_processor, 'errors', []) or []),
        }

        logger.info(
            "Sanitas procesado: %s detalles, %s glosas, %s archivos",
            total_detalles, total_glosas, len(archivos),
        )

        return {
            'success': True,
            'message': message or 'Procesamiento Sanitas completado',
            'output_file': output_file,
            'objeciones_file': objeciones_file,
            'path': output_file,
            'resumen': resumen,
        }



# Procesar adjunto de acuerdo a la EPS
