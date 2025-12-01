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
                        if any(str(cell).strip() in ['Clave', 'clave', 'CVE', 'cve', 'ID', 'id'] for cell in row):
                            # Encontramos la fila de encabezados
                            header_row = row.tolist()
                            for j, header in enumerate(header_row):
                                header_str = str(header).strip()
                                if header_str in ['Clave', 'clave', 'CVE', 'cve', 'ID', 'id']:
                                    clave_col = j
                                elif header_str in ['Descripción', 'descripcion', 'Descrip', 'descrip', 'Nombre', 'nombre']:
                                    desc_col = j
                            data_start_row = i + 1
                            break

                    # Si no encontramos columnas claras, asumir primeras dos columnas
                    if clave_col is None and len(df.columns) >= 2:
                        clave_col = 0
                        desc_col = 1
                        data_start_row = 0

                    # Cargar datos reales
                    if clave_col is not None and desc_col is not None:
                        for i in range(data_start_row, len(df)):
                            try:
                                row_data = df.iloc[i]
                                clave = str(row_data.iloc[clave_col]).strip()
                                descripcion = str(row_data.iloc[desc_col]).strip()

                                # Skip empty or invalid rows
                                if clave and clave != 'nan' and descripcion and descripcion != 'nan':
                                    catalog_dict[clave] = descripcion
                            except (IndexError, KeyError, ValueError):
                                continue

                    self.catalogs[sheet_name] = catalog_dict
                    logger.info(f"Catálogo '{sheet_name}' cargado con {len(catalog_dict)} entradas")

            self.loaded = True
            logger.info("Todos los catálogos cargados exitosamente")

        except Exception as e:
            logger.error(f"Error cargando catálogos: {e}")
            self.loaded = False

    def get_description(self, catalog_name: str, key: str) -> str:
        """
        Obtiene la descripción de una clave de un catálogo específico

        Args:
            catalog_name: Nombre del catálogo
            key: Clave a buscar

        Returns:
            Descripción correspondiente o la clave si no se encuentra
        """
        if not self.loaded or catalog_name not in self.catalogs:
            return get_manual_description(catalog_name, key)

        catalog = self.catalogs[catalog_name]
        return catalog.get(str(key).strip(), get_manual_description(catalog_name, key))

    def get_available_catalogs(self) -> List[str]:
        """Retorna la lista de catálogos disponibles"""
        return list(self.catalogs.keys())

    def is_loaded(self) -> bool:
        """Verifica si los catálogos fueron cargados exitosamente"""
        return self.loaded

def get_manual_description(catalog_name: str, key: str) -> str:
    """
    Proporciona descripciones manuales para catálogos que no están en el archivo Excel
    o cuando el catálogo no está disponible
    """
    key = str(key).strip()

    # Catálogos manuales comunes
    manual_catalogs = {
        'TipoContrato': {
            '01': 'Contrato de trabajo por tiempo indeterminado',
            '02': 'Contrato de trabajo por tiempo determinado',
            '03': 'Contrato de trabajo para obra determinada',
            '04': 'Contrato de trabajo por tiempo indeterminado sujeto a prueba',
            '05': 'Contrato de trabajo por tiempo determinado sujeto a prueba',
            '06': 'Contrato de trabajo por temporada',
            '07': 'Contrato de trabajo por módulo laboral',
            '08': 'Contrato de trabajo por tiempo determinado discontinuo',
            '09': 'Contrato de trabajo para capacitación inicial',
            '10': 'Contrato de trabajo por tiempo indeterminado a prueba',
            '99': 'Otro tipo de contrato'
        },
        'TipoJornada': {
            '01': 'Diurna',
            '02': 'Nocturna',
            '03': 'Mixta',
            '04': 'Por hora',
            '05': 'Reducida',
            '06': 'Continuada',
            '07': 'Partida',
            '08': 'Por turnos',
            '09': 'Discontinua',
            '99': 'Otra jornada'
        },
        'PeriodicidadPago': {
            '01': 'Diario',
            '02': 'Semanal',
            '03': 'Catorcenal',
            '04': 'Quincenal',
            '05': 'Mensual',
            '06': 'Bimestral',
            '07': 'Trimestral',
            '08': 'Semestral',
            '09': 'Anual',
            '10': 'Decenal',
            '11': 'Paganini',
            '99': 'Otra periodicidad'
        },
        'RiesgoPuesto': {
            '1': 'Clase I (Gastos médicos)',
            '2': 'Clase II (Gastos médicos y pensiones)',
            '3': 'Clase III (Invalidez y vida)',
            '4': 'Clase IV (Invalidez, vida y cesantía)',
            '5': 'Clase V (Invalidez, vida, cesantía y vejez)',
            '99': 'No aplica'
        }
    }

    if catalog_name in manual_catalogs and key in manual_catalogs[catalog_name]:
        return manual_catalogs[catalog_name][key]

    # Si no se encuentra, retornar clave con formato
    return f"{key} (Sin descripción)"