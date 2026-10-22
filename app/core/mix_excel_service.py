"""
Servicio para transferir datos entre archivos Excel
Mix Excel - Transferencia de columnas con distribución proporcional
"""
import shutil
from pathlib import Path

import pandas as pd

try:
    from app.config.settings import logger
except Exception:  # pragma: no cover - fallback si settings no disponible
    import logging
    logger = logging.getLogger("glosaap")


class MixExcelService:
    """Servicio para mezclar/transferir datos entre archivos Excel"""

    def __init__(self):
        self.source_df: pd.DataFrame | None = None
        self.dest_df: pd.DataFrame | None = None
        self.source_file: str | None = None
        self.dest_file: str | None = None

    def cargar_archivo(self, file_path: str, tipo: str = "source") -> tuple[bool, list[str], str]:
        """
        Carga un archivo Excel y retorna las columnas

        Args:
            file_path: Ruta del archivo
            tipo: 'source' o 'dest'

        Returns:
            Tuple[success, columns, message]
        """
        try:
            df = pd.read_excel(file_path)
            columns = df.columns.tolist()

            if tipo == "source":
                self.source_df = df
                self.source_file = file_path
            else:
                self.dest_df = df
                self.dest_file = file_path

            return True, columns, f"Archivo cargado: {len(df)} filas"

        except PermissionError:
            return False, [], "El archivo está abierto. Ciérralo e intenta de nuevo."
        except Exception as e:
            return False, [], f"Error al cargar: {str(e)}"

    def transferir_datos(
        self,
        source_col: str,
        source_ref_col: str,
        dest_col: str,
        dest_ref_col: str,
        dest_adjacent_col: str,
        tolerance: float = 0.05
    ) -> tuple[bool, int, str]:
        """
        Transfiere datos del origen al destino

        Args:
            source_col: Columna con valores a transferir
            source_ref_col: Columna de referencia en origen (ej: factura)
            dest_col: Columna destino donde pegar valores
            dest_ref_col: Columna de referencia en destino
            dest_adjacent_col: Columna adyacente para calcular proporción
            tolerance: Tolerancia para comparación (default 5%)

        Returns:
            Tuple[success, matches_found, message]
        """
        if self.source_df is None or self.dest_df is None:
            return False, 0, "Carga ambos archivos primero"

        try:
            matches_found = 0
            processed_refs = set()

            for _idx, dest_ref_value in self.dest_df[dest_ref_col].items():
                if pd.isna(dest_ref_value) or dest_ref_value in processed_refs:
                    continue

                # Buscar filas en destino con el mismo número de factura
                dest_matching_indices = self.dest_df[
                    self.dest_df[dest_ref_col] == dest_ref_value
                ].index.tolist()

                # Buscar facturas con el mismo número en origen
                source_matching_rows = self.source_df[
                    self.source_df[source_ref_col] == dest_ref_value
                ]

                if len(source_matching_rows) > 0 and len(dest_matching_indices) > 0:
                    # Obtener valores del origen
                    source_values = []
                    for _src_idx, src_row in source_matching_rows.iterrows():
                        src_val = src_row[source_col]
                        if pd.notna(src_val):
                            try:
                                source_values.append(float(src_val))
                            except (ValueError, TypeError):
                                continue

                    if len(source_values) > 0:
                        # Obtener valores adyacentes del destino
                        dest_adjacent_values = []
                        for dest_idx in dest_matching_indices:
                            adj_val = self.dest_df.at[dest_idx, dest_adjacent_col]
                            if pd.notna(adj_val):
                                try:
                                    dest_adjacent_values.append((dest_idx, float(adj_val))) # pyright: ignore[reportArgumentType]
                                except (ValueError, TypeError):
                                    pass

                        if len(dest_adjacent_values) > 0:
                            # CASO 1: Múltiples valores en origen - emparejar por similitud
                            # Se aplica tolerancia proporcional:
                            # |src - adj| / |adj| <= tolerance, si excede se omite.
                            if len(source_values) > 1:
                                used_source_values = set()
                                for dest_idx, dest_adj_val in dest_adjacent_values:
                                    best_match_value = None
                                    best_match_idx = None
                                    min_diff = float('inf')

                                    denom = abs(dest_adj_val) if dest_adj_val != 0 else 0
                                    if denom == 0:
                                        continue

                                    for i, src_val in enumerate(source_values):
                                        if i not in used_source_values:
                                            diff = abs(src_val - dest_adj_val) / denom
                                            if diff < min_diff:
                                                min_diff = diff
                                                best_match_value = src_val
                                                best_match_idx = i

                                    if best_match_value is not None and min_diff <= tolerance:
                                        self.dest_df.at[dest_idx, dest_col] = int(round(best_match_value))
                                        used_source_values.add(best_match_idx)
                                        matches_found += 1

                            # CASO 2: Un solo valor - distribuir proporcionalmente
                            # La última fila absorbe la diferencia para que la
                            # suma cuadre exacta con int(round(total)).
                            else:
                                total_to_distribute = source_values[0]
                                total_adjacent = sum([val for _, val in dest_adjacent_values])

                                if total_adjacent > 0:
                                    total_int = int(round(total_to_distribute))
                                    distributed_sum = 0
                                    for i, (dest_idx, adjacent_value) in enumerate(dest_adjacent_values):
                                        if i == len(dest_adjacent_values) - 1:
                                            assigned_value = total_int - distributed_sum
                                        else:
                                            proportion = adjacent_value / total_adjacent
                                            assigned_value = int(round(total_to_distribute * proportion))
                                            distributed_sum += assigned_value

                                        self.dest_df.at[dest_idx, dest_col] = assigned_value
                                        matches_found += 1

                        processed_refs.add(dest_ref_value)

            return True, matches_found, f"Transferencia completada: {matches_found} coincidencias"

        except Exception as e:
            return False, 0, f"Error en transferencia: {str(e)}"

    def guardar_destino(self, output_path: str | None = None) -> tuple[bool, str]:
        """Guarda el archivo destino con los cambios.

        Args:
            output_path: Ruta opcional de salida. Si se indica, se guarda
                allí sin modificar el archivo original. Si es None
                (comportamiento por defecto), se crea un backup ``.bak``
                del archivo original antes de sobreescribirlo.

        Returns:
            Tuple[success, message]
        """
        if self.dest_df is None or self.dest_file is None:
            return False, "No hay archivo destino cargado"

        try:
            target = output_path if output_path else self.dest_file
            target_path = Path(target)
            if target_path.parent and str(target_path.parent) not in ("", "."):
                target_path.parent.mkdir(parents=True, exist_ok=True)

            if output_path is None:
                # Backup del original antes de sobreescribir.
                original = Path(self.dest_file)
                if original.exists() and original.is_file():
                    backup_path = Path(str(original) + ".bak")
                    try:
                        shutil.copy2(original, backup_path)
                        logger.info("Backup creado en %s", backup_path)
                    except Exception as e:
                        logger.warning("No se pudo crear backup %s: %s", backup_path, e)

            self.dest_df.to_excel(str(target_path), index=False)
            return True, f"Guardado en {target_path.name}"
        except PermissionError:
            return False, "El archivo está abierto. Ciérralo e intenta de nuevo."
        except Exception as e:
            logger.error("Error al guardar destino: %s", e)
            return False, f"Error al guardar: {str(e)}"

    def get_preview(self, tipo: str = "source", limit: int = 5) -> pd.DataFrame:
        """Obtiene una vista previa del DataFrame"""
        df = self.source_df if tipo == "source" else self.dest_df
        if df is not None:
            return df.head(limit)
        return pd.DataFrame()

    def reset(self):
        """Reinicia el servicio"""
        self.source_df = None
        self.dest_df = None
        self.source_file = None
        self.dest_file = None
