import xml.etree.ElementTree as ET
import pandas as pd
from typing import List, Dict, Any, Optional
import re
from datetime import datetime
import logging
import os
import glob
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from catalog_manager import CatalogManager, get_manual_description

class EmployeeDatabaseExtractor:
    """
    Extracts employee information from XML payroll files to create a database.
    Handles duplicate detection and data normalization.
    """

    def __init__(self, catalog_file: str = "catNomina.xls"):
        self.employees_df = None
        self.catalog_manager = CatalogManager(catalog_file)
        self.namespaces = {
            'cfdi': 'http://www.sat.gob.mx/cfd/4',
            'cfdi3': 'http://www.sat.gob.mx/cfd/3',
            'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
            'nomina12': 'http://www.sat.gob.mx/nomina12'
        }

    def extract_employee_data_from_xml(self, xml_content: str) -> Optional[Dict[str, Any]]:
        """
        Extract employee data from a single XML file.

        Args:
            xml_content: XML content as string

        Returns:
            Dictionary with employee data or None if extraction fails
        """
        try:
            root = ET.fromstring(xml_content)

            # Try to find the nomina complement
            nomina = self._find_nomina_element(root)
            if nomina is None:
                logger.warning("No se encontró el complemento de nómina en el XML")
                return None

            # Extraer datos básicos del empleado
            rfc_empleado = self._safe_find_text(root, './/cfdi:Receptor', 'Rfc')
            tipo_contrato = self._safe_find_text(nomina, './/nomina12:Receptor', 'TipoContrato')
            tipo_jornada = self._safe_find_text(nomina, './/nomina12:Receptor', 'TipoJornada')
            tipo_regimen = self._safe_find_text(nomina, './/nomina12:Receptor', 'TipoRegimen')
            riesgo_puesto = self._safe_find_text(nomina, './/nomina12:Receptor', 'RiesgoPuesto')
            periodicidad_pago = self._safe_find_text(nomina, './/nomina12:Receptor', 'PeriodicidadPago')

            # Get descriptions first (prioritize descriptions over codes)
            tipo_contrato_desc = get_manual_description('tipo_contrato', tipo_contrato)
            tipo_jornada_desc = get_manual_description('tipo_jornada', tipo_jornada)
            tipo_regimen_desc = get_manual_description('tipo_regimen', tipo_regimen)
            riesgo_puesto_desc = get_manual_description('riesgo_puesto', riesgo_puesto)
            periodicidad_pago_desc = get_manual_description('periodicidad_pago', periodicidad_pago)

            # Override with catalog descriptions if available
            if self.catalog_manager.is_loaded():
                tipo_contrato_desc = self.catalog_manager.decode_tipo_contrato(tipo_contrato) or tipo_contrato_desc
                tipo_jornada_desc = self.catalog_manager.decode_tipo_jornada(tipo_jornada) or tipo_jornada_desc
                tipo_regimen_desc = self.catalog_manager.decode_tipo_regimen(tipo_regimen) or tipo_regimen_desc
                riesgo_puesto_desc = self.catalog_manager.decode_riesgo_puesto(riesgo_puesto) or riesgo_puesto_desc
                periodicidad_pago_desc = self.catalog_manager.decode_periodicidad_pago(periodicidad_pago) or periodicidad_pago_desc

            # Extract employee data (versión optimizada - solo campos esenciales)
            employee_data = {
                # Datos básicos del empleado
                'rfc_empleado': rfc_empleado,
                'nombre_empleado': self._safe_find_text(root, './/cfdi:Receptor', 'Nombre'),
                'curp': self._safe_find_text(nomina, './/nomina12:Receptor', 'Curp'),
                'num_seguridad_social': self._safe_find_text(nomina, './/nomina12:Receptor', 'NumSeguridadSocial'),
                'num_empleado': self._safe_find_text(nomina, './/nomina12:Receptor', 'NumEmpleado'),

                # Domicilio fiscal del empleado
                'codigo_postal': self._safe_find_text(root, './/cfdi:Receptor', 'DomicilioFiscalReceptor'),

                # Datos laborales (solo descripciones, sin códigos de referencia)
                'fecha_inicio_rel_laboral': self._safe_find_text(nomina, './/nomina12:Receptor', 'FechaInicioRelLaboral'),
                'antigüedad': self._safe_find_text(nomina, './/nomina12:Receptor', 'Antigüedad'),
                'tipo_contrato': tipo_contrato_desc,  # Solo descripción
                'tipo_jornada': tipo_jornada_desc,    # Solo descripción
                'tipo_regimen': tipo_regimen_desc,    # Solo descripción
                'riesgo_puesto': riesgo_puesto_desc,  # Solo descripción
                'periodicidad_pago': periodicidad_pago_desc,  # Solo descripción
                'salario_diario_integrado': self._safe_find_text(nomina, './/nomina12:Receptor', 'SalarioDiarioIntegrado'),
                'salario_base_cot_apo': self._safe_find_text(nomina, './/nomina12:Receptor', 'SalarioBaseCotApor'),
                'clave_ent_fed': self._safe_find_text(nomina, './/nomina12:Receptor', 'ClaveEntFed'),

                # Datos adicionales del puesto
                'departamento': self._safe_find_text(nomina, './/nomina12:Receptor', 'Departamento'),
                'puesto': self._safe_find_text(nomina, './/nomina12:Receptor', 'Puesto'),
                'sindicalizado': self._safe_find_text(nomina, './/nomina12:Receptor', 'Sindicalizado'),

                # Datos del empleador
                'rfc_empleador': self._safe_find_text(root, './/cfdi:Emisor', 'Rfc'),
                'nombre_empleador': self._safe_find_text(root, './/cfdi:Emisor', 'Nombre'),
                'registro_patronal': self._safe_find_text(nomina, './/nomina12:Emisor', 'RegistroPatronal'),
                'regimen_fiscal_empleador': self._safe_find_text(root, './/cfdi:Emisor', 'RegimenFiscal'),

                # Timestamp de procesamiento
                'fecha_procesamiento': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # Validate required fields
            if not employee_data.get('rfc_empleado') or not employee_data.get('nombre_empleado'):
                logger.warning("Faltan campos requeridos (RFC o nombre del empleado)")
                return None

            return employee_data

        except ET.ParseError as e:
            logger.error(f"Error al parsear XML: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al extraer datos del empleado: {e}")
            return None

    def _find_nomina_element(self, root: ET.Element) -> Optional[ET.Element]:
        """Find the nomina complement element in XML."""
        # Try different paths for nomina complement
        nomina_paths = [
            './/nomina12:Nomina',
            './/cfdi:Complemento//nomina12:Nomina',
            './/cfdi:Complemento/nomina12:Nomina'
        ]

        for path in nomina_paths:
            try:
                element = root.find(path, self.namespaces)
                if element is not None:
                    return element
            except:
                continue

        return None

    def _safe_find_text(self, parent: ET.Element, tag: str, attribute: str) -> Optional[str]:
        """Safely extract text from XML element attribute."""
        try:
            element = parent.find(tag, self.namespaces)
            if element is not None:
                return element.get(attribute, '').strip()
        except:
            pass
        return None

    def _extract_percepciones_details(self, nomina: ET.Element) -> str:
        """Extract details of perception types from XML"""
        try:
            percepciones = []
            perceptions_elements = nomina.findall('.//nomina12:Percepcion', self.namespaces)

            for percep in perceptions_elements:
                concepto = percep.get('Concepto', '').strip()
                tipo = percep.get('TipoPercepcion', '').strip()
                clave = percep.get('Clave', '').strip()

                # Decode tipo if catalog available
                if self.catalog_manager.is_loaded():
                    tipo_desc = self.catalog_manager.decode_tipo_percepcion(tipo)
                else:
                    tipo_desc = tipo

                percepciones.append(f"{concepto} ({clave})")

            return '; '.join(percepciones) if percepciones else ''
        except:
            return ''

    def find_xml_files(self, path: str) -> List[str]:
        """
        Find XML files in a given path (directory or URL)

        Args:
            path: Directory path to search for XML and ZIP files

        Returns:
            List of file paths found
        """
        files_found = []
        try:
            path_obj = Path(path)

            if path_obj.is_dir():
                # Search for XML and ZIP files
                xml_files = list(path_obj.glob("**/*.xml"))
                zip_files = list(path_obj.glob("**/*.zip"))

                files_found = [str(f) for f in xml_files + zip_files]
                logger.info(f"Encontrados {len(xml_files)} XMLs y {len(zip_files)} ZIPs en {path}")

            elif path_obj.is_file() and (path_obj.suffix.lower() in ['.xml', '.zip']):
                files_found = [str(path_obj)]
                logger.info(f"Archivo encontrado: {path}")

            else:
                logger.warning(f"Ruta no válida o no se encontraron archivos: {path}")

        except Exception as e:
            logger.error(f"Error buscando archivos en {path}: {e}")

        return files_found

    def process_xml_files(self, xml_files: List[str]) -> pd.DataFrame:
        """
        Process multiple XML files and create employee database.

        Args:
            xml_files: List of XML file paths

        Returns:
            DataFrame with unique employees
        """
        employees_data = []
        processed_count = 0
        error_count = 0

        logger.info(f"Procesando {len(xml_files)} archivos XML...")

        for file_path in xml_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    xml_content = f.read()

                employee_data = self.extract_employee_data_from_xml(xml_content)
                if employee_data:
                    employees_data.append(employee_data)
                    processed_count += 1
                    logger.info(f"✅ Procesado: {file_path}")
                else:
                    error_count += 1
                    logger.warning(f"⚠️ No se pudo extraer datos del empleado: {file_path}")

            except Exception as e:
                error_count += 1
                logger.error(f"❌ Error procesando {file_path}: {e}")

        if not employees_data:
            logger.warning("No se pudo extraer datos de empleados de ningún archivo")
            return pd.DataFrame()

        # Create DataFrame and remove duplicates
        df = pd.DataFrame(employees_data)

        # Remove duplicates based on RFC del empleado (primary key)
        unique_employees = self._remove_duplicates(df)

        logger.info(f"✅ Procesamiento completado:")
        logger.info(f"   - Archivos procesados: {processed_count}")
        logger.info(f"   - Errores: {error_count}")
        logger.info(f"   - Empleados únicos encontrados: {len(unique_employees)}")

        return unique_employees

    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove duplicate employees based on RFC.
        Keeps the most recent information based on processing date or fecha_inicio_rel_laboral.
        """
        if df.empty:
            return df

        # Convert date columns for proper sorting
        date_columns = ['fecha_inicio_rel_laboral', 'fecha_procesamiento']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # Sort by processing date (most recent first) to keep latest data
        # If no processing date, sort by inicio_rel_laboral
        if 'fecha_procesamiento' in df.columns:
            df_sorted = df.sort_values('fecha_procesamiento', ascending=False, na_position='last')
        elif 'fecha_inicio_rel_laboral' in df.columns:
            df_sorted = df.sort_values('fecha_inicio_rel_laboral', ascending=False, na_position='last')
        else:
            # Keep original order if no date columns available
            df_sorted = df

        # Remove duplicates based on rfc_empleado, keeping first (most recent)
        unique_df = df_sorted.drop_duplicates(subset=['rfc_empleado'], keep='first')

        # Reset index
        unique_df = unique_df.reset_index(drop=True)

        return unique_df