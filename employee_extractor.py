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

            # Extract employee data
            employee_data = {}

            # Basic employee information
            receptor = root.find('.//cfdi:Receptor', self.namespaces)
            if receptor is not None:
                employee_data['rfc_empleado'] = receptor.get('Rfc', '')
                employee_data['nombre_empleado'] = receptor.get('Nombre', '')
                employee_data['uso_cfdi_empleado'] = receptor.get('UsoCFDI', '')

            # Extract from Nomina complement
            employee_data.update(self._extract_nomina_data(nomina))

            # Add processing metadata
            timbre = root.find('.//tfd:TimbreFiscalDigital', self.namespaces)
            if timbre is not None:
                employee_data['fecha_timbrado'] = timbre.get('FechaTimbrado', '')
                employee_data['uuid'] = timbre.get('UUID', '')

            # Add XML file info
            comprobante = root
            if comprobante is not None:
                employee_data['fecha_pago'] = comprobante.get('Fecha', '')
                employee_data['folio'] = comprobante.get('Folio', '')

            return employee_data

        except ET.ParseError as e:
            logger.error(f"Error parseando XML: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extrayendo datos del XML: {e}")
            return None

    def _find_nomina_element(self, root: ET.Element) -> Optional[ET.Element]:
        """Find the Nomina complement in different versions"""
        # Try Nomina1.2
        nomina = root.find('.//nomina12:Nomina', self.namespaces)
        if nomina is not None:
            return nomina

        # Try other versions if needed
        return None

    def _extract_nomina_data(self, nomina: ET.Element) -> Dict[str, Any]:
        """Extract specific data from Nomina complement"""
        data = {}

        # Basic nomina data
        data['version_nomina'] = nomina.get('Version', '')
        data['tipo_nomina'] = nomina.get('TipoNomina', '')
        data['fecha_pago_nomina'] = nomina.get('FechaPago', '')
        data['fecha_inicial_pago'] = nomina.get('FechaInicialPago', '')
        data['fecha_final_pago'] = nomina.get('FechaFinalPago', '')
        data['num_dias_pagados'] = nomina.get('NumDiasPagados', '')
        data['total_percepciones'] = nomina.get('TotalPercepciones', '')
        data['total_deducciones'] = nomina.get('TotalDeducciones', '')
        data['total_otras_deducciones'] = nomina.get('TotalOtrasDeducciones', '')

        # Empleado data
        empleado = nomina.find('.//nomina12:Empleado', self.namespaces)
        if empleado is not None:
            data.update(self._extract_empleado_data(empleado))

        return data

    def _extract_empleado_data(self, empleado: ET.Element) -> Dict[str, Any]:
        """Extract employee specific data"""
        data = {}

        data['curp'] = empleado.get('Curp', '')
        data['num_seguridad_social'] = empleado.get('NumSeguridadSocial', '')
        data['fecha_inicio_rel_laboral'] = empleado.get('FechaInicioRelLaboral', '')
        data['antiguedad'] = empleado.get('Antiguedad', '')
        data['tipo_contrato'] = empleado.get('TipoContrato', '')
        data['sindicalizado'] = empleado.get('Sindicalizado', '')
        data['tipo_jornada'] = empleado.get('TipoJornada', '')
        data['tipo_regimen'] = empleado.get('TipoRegimen', '')
        data['num_empleado'] = empleado.get('NumEmpleado', '')
        data['departamento'] = empleado.get('Departamento', '')
        data['puesto'] = empleado.get('Puesto', '')
        data['riesgo_puesto'] = empleado.get('RiesgoPuesto', '')
        data['periodicidad_pago'] = empleado.get('PeriodicidadPago', '')
        data['banco'] = empleado.get('Banco', '')
        data['cuenta_bancaria'] = empleado.get('CuentaBancaria', '')
        data['salario_base_cot_apor'] = empleado.get('SalarioBaseCotApor', '')
        data['salario_diario_integrado'] = empleado.get('SalarioDiarioIntegrado', '')
        data['clave_ent_fed'] = empleado.get('ClaveEntFed', '')

        # Decode coded fields using catalogs
        data['tipo_contrato_desc'] = self.catalog_manager.get_description('TipoContrato', data['tipo_contrato'])
        data['tipo_jornada_desc'] = self.catalog_manager.get_description('TipoJornada', data['tipo_jornada'])
        data['periodicidad_pago_desc'] = self.catalog_manager.get_description('PeriodicidadPago', data['periodicidad_pago'])
        data['riesgo_puesto_desc'] = self.catalog_manager.get_description('RiesgoPuesto', data['riesgo_puesto'])

        return data

    def process_xml_files(self, xml_files: List[str]) -> pd.DataFrame:
        """
        Process a list of XML files and extract employee data.

        Args:
            xml_files: List of XML file paths

        Returns:
            DataFrame with employee data
        """
        all_employees = []

        for xml_file in xml_files:
            try:
                logger.info(f"Procesando archivo: {xml_file}")

                with open(xml_file, 'r', encoding='utf-8') as f:
                    xml_content = f.read()

                employee_data = self.extract_employee_data_from_xml(xml_content)
                if employee_data:
                    # Add file metadata
                    employee_data['archivo_origen'] = os.path.basename(xml_file)
                    employee_data['ruta_archivo'] = xml_file
                    employee_data['fecha_procesamiento'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    all_employees.append(employee_data)

            except Exception as e:
                logger.error(f"Error procesando archivo {xml_file}: {e}")
                continue

        if not all_employees:
            logger.warning("No se extrajo información de empleados de ningún archivo")
            return pd.DataFrame()

        # Create DataFrame
        df = pd.DataFrame(all_employees)

        # Remove duplicates
        df = self._remove_duplicates(df)

        self.employees_df = df
        logger.info(f"Se procesaron {len(xml_files)} archivos y se encontraron {len(df)} empleados únicos")

        return df

    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove duplicate employees, keeping the most recent record.

        Args:
            df: DataFrame with employee data

        Returns:
            DataFrame with duplicates removed
        """
        if df.empty:
            return df

        # Sort by date fields to get most recent records first
        df_sorted = df.copy()

        # Try different date columns for sorting
        date_columns = ['fecha_pago', 'fecha_pago_nomina', 'fecha_procesamiento']
        sort_column = None

        for col in date_columns:
            if col in df_sorted.columns:
                try:
                    df_sorted[col] = pd.to_datetime(df_sorted[col], errors='coerce')
                    df_sorted = df_sorted.sort_values(col, ascending=False, na_position='last')
                    sort_column = col
                    break
                except:
                    continue

        if sort_column:
            logger.info(f"Ordenando por fecha: {sort_column}")

        # Remove duplicates based on RFC (primary key for employees)
        if 'rfc_empleado' in df_sorted.columns:
            initial_count = len(df_sorted)
            df_unique = df_sorted.drop_duplicates(subset=['rfc_empleado'], keep='first')
            removed_count = initial_count - len(df_unique)
            logger.info(f"Se eliminaron {removed_count} registros duplicados")
            return df_unique

        logger.warning("No se encontró RFC para eliminar duplicados")
        return df_sorted

    def add_descriptions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add descriptions to coded fields using catalogs.

        Args:
            df: DataFrame with employee data

        Returns:
            DataFrame with descriptions added
        """
        if df.empty:
            return df

        df_desc = df.copy()

        # Add descriptions for coded fields
        coded_fields = [
            ('tipo_contrato', 'tipo_contrato_desc'),
            ('tipo_jornada', 'tipo_jornada_desc'),
            ('periodicidad_pago', 'periodicidad_pago_desc'),
            ('riesgo_puesto', 'riesgo_puesto_desc')
        ]

        for code_field, desc_field in coded_fields:
            if code_field in df_desc.columns and desc_field not in df_desc.columns:
                df_desc[desc_field] = df_desc[code_field].apply(
                    lambda x: self.catalog_manager.get_description(
                        code_field.replace('_', '').replace('tipo', '').replace('pago', ''),
                        str(x)
                    )
                )

        return df_desc

    def find_xml_files(self, directory: str) -> List[str]:
        """
        Find all XML files in a directory.

        Args:
            directory: Directory path to search

        Returns:
            List of XML file paths
        """
        if not os.path.exists(directory):
            logger.error(f"Directorio no existe: {directory}")
            return []

        xml_files = []

        # Find XML files
        for ext in ['*.xml', '*.XML']:
            xml_files.extend(glob.glob(os.path.join(directory, ext)))

        # Find ZIP files and extract XMLs (if needed)
        # This could be extended to handle ZIP files

        logger.info(f"Se encontraron {len(xml_files)} archivos XML en {directory}")
        return xml_files

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the processed data.

        Returns:
            Dictionary with statistics
        """
        if self.employees_df is None or self.employees_df.empty:
            return {}

        stats = {
            'total_empleados': len(self.employees_df),
            'rfc_unicos': self.employees_df['rfc_empleado'].nunique() if 'rfc_empleado' in self.employees_df.columns else 0,
            'curp_validas': self.employees_df['curp'].notna().sum() if 'curp' in self.employees_df.columns else 0,
            'con_nss': self.employees_df['num_seguridad_social'].notna().sum() if 'num_seguridad_social' in self.employees_df.columns else 0,
            'empleadores_unicos': self.employees_df['rfc_empleador'].nunique() if 'rfc_empleador' in self.employees_df.columns else 0,
        }

        return stats