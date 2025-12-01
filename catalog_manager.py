import pandas as pd
import os
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class CatalogManager:
    """
    Gestiona los catálogos del archivo catNomina.xls para decodificar claves del SAT
    """

    def __init__(self, catalog_file: str = "catNomina.xls"):
        self.catalog_file = catalog_file
        self.catalogs: Dict[str, Dict[str, Any]] = {}
        self.loaded = False
        self._load_catalogs()

    def _load_catalogs(self):
        """Carga todos los catálogos desde el archivo Excel"""
        try:
            if not os.path.exists(self.catalog_file):
                logger.warning(f"Archivo de catálogos no encontrado: {self.catalog_file}")
                self.loaded = False
                return

            # Leer todas las pestañas del archivo Excel
            excel_file = pd.ExcelFile(self.catalog_file)

            logger.info(f"Catálogos encontrados en {self.catalog_file}:")
            for sheet_name in excel_file.sheet_names:
                logger.info(f"  - {sheet_name}")

                # Leer cada catálogo
                df = pd.read_excel(self.catalog_file, sheet_name=sheet_name)

                if not df.empty:
                    # Estandarizar el formato del catálogo
                    # Manejar formato especial del SAT donde los datos reales empiezan después de filas de metadata
                    columns = df.columns.tolist()
                    catalog_dict = {}

                    # Intentar identificar columnas de clave y descripción
                    clave_col = None
                    desc_col = None

                    # Para catálogos SAT, buscar filas que contienen los nombres de columna reales
                    # y encontrar donde empiezan los datos reales
                    data_start_row = 0
                    for i, row in df.iterrows():
                        row_values = [str(val) for val in row.values]
                        # Buscar fila que contiene "c_Tipo" o similar
                        if any('c_' in str(val) and 'Tipo' in str(val) for val in row_values if pd.notna(val)):
                            data_start_row = i + 1
                            # Encontrar las columnas correctas - buscar los índices de los valores en la fila
                            for j, val in enumerate(row_values):
                                if 'c_' in str(val):
                                    clave_col = columns[j]  # Esta es la columna que contiene los códigos
                                elif 'Descripci' in str(val) or 'Descripción' in str(val):
                                    desc_col = columns[j]    # Esta es la columna que contiene las descripciones
                            break

                    # Si no se encuentra el formato especial, usar el método original
                    if clave_col is None:
                        # Buscar columnas numéricas o que contengan 'Clave', 'c_', 'Tipo'
                        for i, col in enumerate(columns):
                            col_str = str(col).lower()
                            if any(keyword in col_str for keyword in ['clave', 'c_', 'tipo', 'id']):
                                if clave_col is None:
                                    clave_col = col
                                elif desc_col is None and i > 0:
                                    desc_col = columns[i+1] if i+1 < len(columns) else columns[i-1]

                        # Si no se identifican las columnas correctamente, usar las dos primeras
                        if clave_col is None and len(columns) >= 2:
                            clave_col = columns[0]
                            desc_col = columns[1]
                        data_start_row = 0

                    if clave_col and desc_col:
                        # Convertir a diccionario, omitiendo filas de metadata
                        for i, row in df.iterrows():
                            if i < data_start_row:
                                continue  # Omitir filas de metadata
                            try:
                                clave = str(row[clave_col]).strip()
                                desc = str(row[desc_col]).strip()
                                if clave != 'nan' and desc != 'nan' and clave and desc:
                                    catalog_dict[clave] = desc
                                    # Also add zero-padded version for common codes
                                    if clave.isdigit() and len(clave) == 1:
                                        catalog_dict[f"0{clave}"] = desc
                            except:
                                continue

                        if catalog_dict:
                            self.catalogs[sheet_name] = {
                                'data': df,
                                'mapping': catalog_dict,
                                'clave_column': clave_col,
                                'desc_column': desc_col
                            }
                            logger.info(f"    Cargado: {len(catalog_dict)} registros")

            self.loaded = len(self.catalogs) > 0
            logger.info(f"Total de catálogos cargados: {len(self.catalogs)}")

        except Exception as e:
            logger.error(f"Error cargando catálogos: {e}")
            self.loaded = False

    def get_description(self, catalog_name: str, key: str) -> str:
        """
        Obtiene la descripción de un catálogo basado en la clave

        Args:
            catalog_name: Nombre del catálogo/pestaña
            key: Clave a buscar

        Returns:
            Descripción correspondiente o la clave si no encuentra
        """
        if not self.loaded or catalog_name not in self.catalogs:
            return str(key)

        try:
            return self.catalogs[catalog_name]['mapping'].get(str(key), str(key))
        except:
            return str(key)

    def decode_tipo_contrato(self, clave: str) -> str:
        """Decodifica tipo de contrato"""
        return self.get_description('c_TipoContrato', clave)

    def decode_tipo_jornada(self, clave: str) -> str:
        """Decodifica tipo de jornada"""
        return self.get_description('c_TipoJornada', clave)

    def decode_tipo_regimen(self, clave: str) -> str:
        """Decodifica tipo de régimen"""
        return self.get_description('c_TipoRegimen', clave)

    def decode_periodicidad_pago(self, clave: str) -> str:
        """Decodifica periodicidad de pago"""
        return self.get_description('c_PeriodicidadPago', clave)

    def decode_riesgo_puesto(self, clave: str) -> str:
        """Decodifica riesgo puesto"""
        return self.get_description('c_RiesgoPuesto', clave)

    def decode_banco(self, clave: str) -> str:
        """Decodifica banco"""
        return self.get_description('c_Banco', clave)

    def decode_tipo_percepcion(self, clave: str) -> str:
        """Decodifica tipo de percepción"""
        return self.get_description('c_TipoPercepcion', clave)

    def decode_tipo_deduccion(self, clave: str) -> str:
        """Decodifica tipo de deducción"""
        return self.get_description('c_TipoDeduccion', clave)

    def decode_tipo_otro_pago(self, clave: str) -> str:
        """Decodifica otro tipo de pago"""
        return self.get_description('c_TipoOtroPago', clave)

    def get_catalog_info(self) -> Dict[str, Any]:
        """Retorna información sobre los catálogos cargados"""
        info = {}
        for name, catalog in self.catalogs.items():
            info[name] = {
                'total_records': len(catalog['mapping']),
                'clave_column': catalog['clave_column'],
                'desc_column': catalog['desc_column'],
                'sample_keys': list(catalog['mapping'].keys())[:5]
            }
        return info

    def is_loaded(self) -> bool:
        """Verifica si los catálogos se cargaron correctamente"""
        return self.loaded

    def get_available_catalogs(self) -> List[str]:
        """Retorna la lista de catálogos disponibles"""
        return list(self.catalogs.keys())

# Catálogos manuales como respaldo
CATALOGOS_MANUALES = {
    'tipo_contrato': {
        '01': 'Contrato por tiempo indeterminado',
        '02': 'Contrato por tiempo determinado',
        '03': 'Contrato para obra determinada',
        '04': 'Contrato sujeto a prueba',
        '05': 'Contrato con capacitación inicial'
    },
    'tipo_jornada': {
        '01': 'Diurna',
        '02': 'Mixta',
        '03': 'Nocturna',
        '04': 'Por hora',
        '05': 'Reducida',
        '06': 'Continuada',
        '07': 'Partida',
        '08': 'Discontinua'
    },
    'tipo_regimen': {
        '02': 'Sueldos y salarios',
        '04': 'Salarios mínimos',
        '05': 'Jubilados',
        '06': 'Pensionados',
        '07': 'Asimilados a salarios',
        '08': 'Servicios profesionales (honorarios)',
        '09': 'Arrendamiento',
        '10': 'Régimen de actividades empresariales y profesionales',
        '12': 'Personas físicas con actividades empresariales y profesionales'
    },
    'periodicidad_pago': {
        '01': 'Diario',
        '02': 'Semanal',
        '03': 'Catorcenal',
        '04': 'Quincenal',
        '05': 'Mensual',
        '06': 'Bimestral',
        '07': 'Unidad por obra',
        '08': 'Comisión',
        '09': 'Precio alzado',
        '10': 'Consolidado mensual'
    },
    'riesgo_puesto': {
        '1': 'Clase I',
        '2': 'Clase II',
        '3': 'Clase III',
        '4': 'Clase IV',
        '5': 'Clase V'
    }
}

def get_manual_description(catalog_type: str, clave: str) -> str:
    """
    Obtiene descripción de catálogos manuales como respaldo

    Args:
        catalog_type: Tipo de catálogo
        clave: Clave a buscar

    Returns:
        Descripción correspondiente
    """
    try:
        return CATALOGOS_MANUALES.get(catalog_type, {}).get(str(clave), str(clave))
    except:
        return str(clave)