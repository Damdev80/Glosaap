"""
Script para homologar códigos del archivo de observación
Aplica las mismas reglas de homologación que MutualserProcessor

FLUJO DE HOMOLOGACIÓN:
1. Tomar código de la columna "Tecnología"
2. Buscar ese código en "Código Servicio de la ERP" (archivo de homologación)
3. De esa fila, tomar el valor de "Código producto en DGH"
4. Buscar ese valor en TODA la columna "COD_SERV_FACT"
5. Si existe → devolverlo, si no → dejar en blanco
"""

import pandas as pd
import os
from datetime import datetime


class HomologadorObservacion:
    """Clase para homologar códigos del archivo de observación"""
    
    def __init__(self, homologacion_path=None):
        """
        Inicializa el homologador
        
        Args:
            homologacion_path: Ruta al archivo de homologación (por defecto usa el de la red)
        """
        # Ruta por defecto al homologador en la red
        self.homologacion_path = homologacion_path or r"\\minerva\Cartera\GLOSAAP\HOMOLOGADOR\HOMOLOGADOR_MUTUALSER.xlsx"
        self.df_homologacion = None
        self.todos_cod_serv_fact = set()
        
        # Cargar archivo de homologación
        self._cargar_homologacion()
    
    def _cargar_homologacion(self):
        """Carga el archivo de homologación"""
        try:
            if not os.path.exists(self.homologacion_path):
                print(f"⚠️ Archivo de homologación no encontrado: {self.homologacion_path}")
                return
            
            self.df_homologacion = pd.read_excel(self.homologacion_path)
            self.df_homologacion.columns = self.df_homologacion.columns.str.strip()
            
            # Crear conjunto de todos los valores válidos en COD_SERV_FACT
            columna_cod_serv_fact = 'COD_SERV_FACT'
            if columna_cod_serv_fact in self.df_homologacion.columns:
                self.todos_cod_serv_fact = set(
                    self.df_homologacion[columna_cod_serv_fact]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .tolist()
                )
                self.todos_cod_serv_fact.discard('0')
                self.todos_cod_serv_fact.discard('')
            
            print(f"✅ Archivo de homologación cargado: {len(self.df_homologacion)} registros")
            print(f"   COD_SERV_FACT únicos: {len(self.todos_cod_serv_fact)}")
            
        except Exception as e:
            print(f"❌ Error al cargar archivo de homologación: {e}")
    
    def _buscar_codigo_homologado(self, codigo_tecnologia):
        """
        Busca el código homologado según las reglas de negocio
        
        FLUJO:
        1. Buscar código en "Código Servicio de la ERP"
        2. Tomar el valor de "Código producto en DGH" de esa fila
        3. Buscar ese valor en TODA la columna "COD_SERV_FACT"
        4. Si existe → devolverlo
        """
        if self.df_homologacion is None or pd.isna(codigo_tecnologia):
            return ''
        
        try:
            # Convertir código a string y limpiar
            codigo_str = str(codigo_tecnologia).strip()
            
            # Si está vacío, retornar vacío
            if not codigo_str or codigo_str == 'nan':
                return ''
            
            # Nombres de columnas
            columna_erp = 'Código Servicio de la ERP'
            columna_codigo_producto = 'Código producto en DGH'
            columna_cod_serv_fact = 'COD_SERV_FACT'
            
            # Verificar que las columnas existen
            for col in [columna_erp, columna_codigo_producto, columna_cod_serv_fact]:
                if col not in self.df_homologacion.columns:
                    return ''
            
            # Extraer solo dígitos del código para comparación flexible
            codigo_numerico = ''.join(filter(str.isdigit, codigo_str))
            
            # PASO 1: Buscar en 'Código Servicio de la ERP'
            mask = self.df_homologacion[columna_erp].astype(str).str.strip() == codigo_str
            resultado = self.df_homologacion[mask]
            
            # Búsqueda flexible si no encuentra exacto
            if resultado.empty and codigo_numerico:
                mask = self.df_homologacion[columna_erp].astype(str).str.replace(r'\D', '', regex=True) == codigo_numerico
                resultado = self.df_homologacion[mask]
            
            if not resultado.empty:
                # PASO 2: Tomar el valor de 'Código producto en DGH'
                codigo_producto_dgh = resultado.iloc[0][columna_codigo_producto]
                
                if pd.notna(codigo_producto_dgh):
                    codigo_producto_str = str(codigo_producto_dgh).strip()
                    
                    if codigo_producto_str and codigo_producto_str != '0' and codigo_producto_str != 'nan':
                        # PASO 3: Buscar en TODA la columna COD_SERV_FACT
                        if codigo_producto_str in self.todos_cod_serv_fact:
                            return codigo_producto_str
                        
                        # Búsqueda flexible por parte numérica
                        codigo_producto_numerico = ''.join(filter(str.isdigit, codigo_producto_str))
                        if codigo_producto_numerico:
                            for cod in self.todos_cod_serv_fact:
                                cod_numerico = ''.join(filter(str.isdigit, cod))
                                if cod_numerico == codigo_producto_numerico:
                                    return cod
            
            return ''
            
        except Exception as e:
            print(f"   ⚠️ Error buscando código {codigo_tecnologia}: {e}")
            return ''
    
    def homologar_archivo(self, archivo_entrada, archivo_salida=None):
        """
        Homologa los códigos del archivo de observación
        
        Args:
            archivo_entrada: Ruta del archivo Excel a homologar
            archivo_salida: Ruta del archivo de salida (opcional)
            
        Returns:
            Ruta del archivo generado o None si hay error
        """
        try:
            print(f"\n{'='*70}")
            print("HOMOLOGANDO ARCHIVO DE OBSERVACIÓN")
            print(f"{'='*70}")
            
            # Leer archivo
            print(f"📄 Leyendo: {archivo_entrada}")
            df = pd.read_excel(archivo_entrada)
            df.columns = df.columns.str.strip()
            
            print(f"   Registros: {len(df)}")
            print(f"   Columnas: {list(df.columns)}")
            
            # Verificar columna Tecnología
            if 'Tecnología' not in df.columns:
                print("❌ Columna 'Tecnología' no encontrada")
                return None
            
            # Homologar cada código
            print(f"\n🔄 Homologando códigos...")
            codigos_homologados = []
            tecnologias_no_homologadas = []
            total = len(df)
            encontrados = 0
            
            for idx, row in df.iterrows():
                tecnologia = row.get('Tecnología')
                codigo_homologado = self._buscar_codigo_homologado(tecnologia)
                codigos_homologados.append(codigo_homologado)
                
                if codigo_homologado:
                    encontrados += 1
                else:
                    if pd.notna(tecnologia) and str(tecnologia).strip():
                        tecnologias_no_homologadas.append(str(tecnologia).strip())
                
                # Mostrar progreso cada 10%
                if (idx + 1) % max(1, total // 10) == 0:
                    porcentaje = ((idx + 1) / total) * 100
                    print(f"   Progreso: {porcentaje:.0f}% ({idx + 1}/{total})")
            
            # Actualizar columna de código homologado
            df['Codigo homologado DGH'] = codigos_homologados
            
            # Agregar columna de tecnologías NO homologadas
            df['Tecnologia NO homologada'] = df.apply(
                lambda row: row['Tecnología'] if (pd.isna(row['Codigo homologado DGH']) or row['Codigo homologado DGH'] == '') and pd.notna(row['Tecnología']) else '',
                axis=1
            )
            
            # Generar archivo de salida
            if archivo_salida is None:
                nombre_base = os.path.splitext(os.path.basename(archivo_entrada))[0]
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                directorio = os.path.dirname(archivo_entrada)
                archivo_salida = os.path.join(directorio, f"{nombre_base}_HOMOLOGADO_{timestamp}.xlsx")
            
            # Guardar
            df.to_excel(archivo_salida, index=False)
            
            print(f"\n{'='*70}")
            print("✅ HOMOLOGACIÓN COMPLETADA")
            print(f"{'='*70}")
            print(f"   • Total de registros: {total}")
            print(f"   • Códigos homologados: {encontrados}")
            print(f"   • Sin homologar: {total - encontrados}")
            print(f"   • Archivo generado: {archivo_salida}")
            
            return archivo_salida
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """Función principal para ejecutar desde línea de comandos"""
    import sys
    
    # Rutas por defecto (homologador en la red)
    archivo_observacion = 'app/archivos_sep/MUTUAL SER SEP.xlsx'
    archivo_homologacion = r"\\minerva\Cartera\GLOSAAP\HOMOLOGADOR\HOMOLOGADOR_MUTUALSER.xlsx"
    
    # Permitir pasar archivo como argumento
    if len(sys.argv) > 1:
        archivo_observacion = sys.argv[1]
    if len(sys.argv) > 2:
        archivo_homologacion = sys.argv[2]
    
    # Crear homologador y procesar
    homologador = HomologadorObservacion(homologacion_path=archivo_homologacion)
    resultado = homologador.homologar_archivo(archivo_observacion)
    
    if resultado:
        print(f"\n🎉 ¡Proceso completado!")
        print(f"   Archivo: {resultado}")
    else:
        print(f"\n❌ El proceso falló")


if __name__ == "__main__":
    main()
