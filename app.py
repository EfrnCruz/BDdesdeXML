import streamlit as st
import pandas as pd
import os
import zipfile
import tempfile
from pathlib import Path
import logging
from io import BytesIO

from employee_extractor import EmployeeDatabaseExtractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Streamlit page
st.set_page_config(
    page_title="Generador de Base de Datos de Empleados XML",
    page_icon="📂",  # Icono de portafolio con colores que combinan mejor con el verde
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #0d1117 0%, #06752e 50%, #0d1117 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(6, 117, 46, 0.3);
        border: 1px solid rgba(6, 117, 46, 0.3);
    }
    .success-box {
        background-color: rgba(6, 117, 46, 0.1);
        border: 1px solid #06752e;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
        color: #1a7f37;
    }
    .warning-box {
        background-color: rgba(255, 193, 7, 0.1);
        border: 1px solid #ffc107;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
        color: #997404;
    }
    .error-box {
        background-color: rgba(220, 53, 69, 0.1);
        border: 1px solid #dc3545;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
        color: #dc3545;
    }
    .stats-card {
        background: rgba(13, 17, 23, 0.8);
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin: 0.5rem 0;
        border-left: 4px solid #06752e;
        color: #c9d1d9;
    }
    .feature-highlight {
        background: rgba(6, 117, 46, 0.05);
        border: 1px solid rgba(6, 117, 46, 0.2);
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        color: #e6edf3;
    }
    .metric-value {
        color: #1a7f37 !important;
        font-weight: bold;
    }
    .stMetric > div > div > div {
        color: #1a7f37 !important;
    }
    .stButton > button {
        background-color: #06752e;
        color: white;
        border: 1px solid #06752e;
        border-radius: 6px;
        transition: all 0.3s ease;
        font-weight: 500;
    }
    .stButton > button:hover {
        background-color: #0a8c3d;
        border-color: #0a8c3d;
        box-shadow: 0 2px 8px rgba(6, 117, 46, 0.4);
    }
    .stDownloadButton > button {
        background-color: #06752e;
        color: white;
        border: 1px solid #06752e;
        border-radius: 6px;
        font-weight: 500;
    }
    .stDownloadButton > button:hover {
        background-color: #0a8c3d;
        border-color: #0a8c3d;
        box-shadow: 0 2px 8px rgba(6, 117, 46, 0.4);
    }
    .streamlit-expanderHeader {
        background-color: rgba(13, 17, 23, 0.6);
        border-radius: 6px;
        border: 1px solid rgba(6, 117, 46, 0.2);
    }
    /* Dark theme enhancements */
    .stSelectbox > div > div > div {
        background-color: rgba(13, 17, 23, 0.8);
        border: 1px solid rgba(6, 117, 46, 0.3);
    }
    .stMultiSelect > div > div > div {
        background-color: rgba(13, 17, 23, 0.8);
        border: 1px solid rgba(6, 117, 46, 0.3);
    }
    .stDataFrame {
        background-color: rgba(13, 17, 23, 0.8);
    }
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(13, 17, 23, 0.8);
    }
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(6, 117, 46, 0.2);
        color: #e6edf3;
    }
    .element-container {
        background-color: transparent;
    }
</style>
""", unsafe_allow_html=True)

def extract_xml_files(uploaded_files):
    """
    Extract XML files from uploaded files (individual XMLs or ZIP files).

    Returns:
        List of temporary XML file paths
    """
    temp_files = []

    for uploaded_file in uploaded_files:
        try:
            if uploaded_file.name.lower().endswith('.zip'):
                # Handle ZIP file
                with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                    for file_info in zip_ref.filelist:
                        if file_info.filename.lower().endswith('.xml'):
                            # Extract XML content to temporary file
                            with zip_ref.open(file_info) as xml_file:
                                content = xml_file.read().decode('utf-8', errors='ignore')

                                # Create temporary file
                                temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.xml',
                                                                        delete=False, encoding='utf-8')
                                temp_file.write(content)
                                temp_file.close()
                                temp_files.append(temp_file.name)
            elif uploaded_file.name.lower().endswith('.xml'):
                # Handle individual XML file
                content = uploaded_file.read().decode('utf-8', errors='ignore')

                # Create temporary file
                temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.xml',
                                                        delete=False, encoding='utf-8')
                temp_file.write(content)
                temp_file.close()
                temp_files.append(temp_file.name)
        except Exception as e:
            st.error(f"Error procesando {uploaded_file.name}: {str(e)}")
            continue

    return temp_files

def clean_temp_files(temp_files):
    """Clean up temporary files."""
    for temp_file in temp_files:
        try:
            os.unlink(temp_file)
        except:
            pass

def create_excel_download(df):
    """
    Create Excel file for download with formatting.

    Returns:
        BytesIO object with Excel file
    """
    output = BytesIO()

    # Create Excel writer with formatting
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Main employee data
        df.to_excel(writer, sheet_name='Base_Empleados', index=False)

        # Get workbook and worksheet for formatting
        workbook = writer.book
        worksheet = writer.sheets['Base_Empleados']

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#06752e',
            'font_color': 'white',
            'border': 1
        })

        # Apply header formatting
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # Auto-adjust column widths
        for i, col in enumerate(df.columns):
            max_len = max(
                df[col].astype(str).map(len).max(),
                len(col)
            )
            worksheet.set_column(i, i, min(max_len + 2, 50))

    output.seek(0)
    return output

def show_data_summary(df):
    """Display data summary statistics with enhanced styling."""
    col1, col2, col3, col4 = st.columns(4)

    # Custom metric styling
    def styled_metric(label, value, delta=None, help_text=None):
        return st.metric(
            label=label,
            value=value,
            delta=delta,
            help=help_text
        )

    with col1:
        styled_metric(
            label="👥 Total Empleados",
            value=len(df),
            help_text="Número total de empleados únicos procesados"
        )

    with col2:
        # Count unique employers
        unique_employers = df['rfc_empleador'].nunique() if not df.empty else 0
        styled_metric(
            label="🏢 Empleadores Únicos",
            value=unique_employers,
            help_text="Número de empresas distintas"
        )

    with col3:
        # Count employees with complete data
        complete_data = df[
            (df['curp'].notna()) &
            (df['num_seguridad_social'].notna()) &
            (df['fecha_inicio_rel_laboral'].notna())
        ].shape[0] if not df.empty else 0
        percentage = (complete_data / len(df) * 100) if len(df) > 0 else 0
        styled_metric(
            label="✅ Datos Completos",
            value=complete_data,
            delta=f"{percentage:.1f}%",
            help_text="Empleados con CURP, NSS y fecha de inicio"
        )

    with col4:
        # Average salary
        avg_salary = 0
        if not df.empty and 'salario_diario_integrado' in df.columns:
            avg_salary = pd.to_numeric(df['salario_diario_integrado'], errors='coerce').mean()

        styled_metric(
            label="💰 Salario Promedio",
            value=f"${avg_salary:,.2f}" if avg_salary > 0 else "N/A",
            help_text="Salario diario integrado promedio"
        )

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📂 Generador de Base de Datos de Empleados XML</h1>
        <p>Extrae información de empleados desde archivos XML de nómina del SAT</p>
        <p>Elimina duplicados automáticamente y genera archivo Excel estructurado</p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    st.sidebar.markdown("""
    <div style='background: linear-gradient(135deg, #0d1117 0%, #06752e 100%);
                color: white; padding: 1rem; border-radius: 8px; text-align: center;
                margin-bottom: 1rem; box-shadow: 0 4px 8px rgba(0,0,0,0.3); border: 1px solid rgba(6, 117, 46, 0.3);'>
        <h2 style='margin: 0; font-size: 1.2em;'>⚙️ Configuración</h2>
    </div>
    """, unsafe_allow_html=True)

    # Instructions with enhanced dark styling
    with st.sidebar.expander("📖 Instrucciones de Uso", expanded=True):
        st.markdown("""
        <div style='background: rgba(13, 17, 23, 0.6); border: 1px solid rgba(6, 117, 46, 0.3);
                   border-radius: 8px; padding: 1rem; margin: 0.5rem 0;'>
            <h4 style='color: #1a7f37; margin-top: 0;'>🚀 Pasos para usar:</h4>
            <ol style='color: #e6edf3; line-height: 1.6; margin: 0.5rem 0;'>
                <li><strong>Sube archivos:</strong> XML individuales o ZIP con múltiples XML</li>
                <li><strong>O especifica directorio:</strong> Escribe la ruta del directorio con archivos</li>
                <li><strong>Procesa:</strong> Haz clic en "Procesar Archivos"</li>
                <li><strong>Revisa:</strong> Visualiza los datos extraídos</li>
                <li><strong>Descarga:</strong> Exporta a Excel o CSV</li>
            </ol>
        </div>

        <div style='background: rgba(6, 117, 46, 0.1); padding: 0.8rem; border-radius: 6px;
                   border-left: 4px solid #06752e; margin-top: 1rem; border: 1px solid rgba(6, 117, 46, 0.2);'>
            <h5 style='color: #1a7f37; margin-top: 0;'>✅ Formatos soportados:</h5>
            <ul style='margin-bottom: 0; color: #e6edf3; font-size: 0.9em; line-height: 1.4;'>
                <li>📄 XML de nómina del SAT</li>
                <li>🗜️ ZIP con múltiples XML</li>
                <li>🔄 Procesamiento automático</li>
                <li>🔍 Detección inteligente de duplicados</li>
                <li>📊 Generación de estadísticas</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    # File upload section with dark styling
    st.markdown("""
    <div style='background: rgba(13, 17, 23, 0.6); border: 1px solid rgba(6, 117, 46, 0.3);
                padding: 1.5rem; border-radius: 8px; margin-bottom: 1rem;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);'>
        <h2 style='color: #1a7f37; margin-top: 0; margin-bottom: 1rem;'>📁 Carga de Archivos</h2>
    </div>
    """, unsafe_allow_html=True)

    # Tab for different upload methods with enhanced styling
    tab1, tab2 = st.tabs(["📤 Subir Archivos", "📂 Especificar Ruta"])

    with tab1:
        uploaded_files = st.file_uploader(
            "Selecciona archivos XML o ZIP:",
            type=['xml', 'zip'],
            accept_multiple_files=True,
            help="Puedes subir múltiples archivos XML o archivos ZIP que contengan XMLs"
        )

        if uploaded_files:
            st.info(f"Se han cargado {len(uploaded_files)} archivo(s)")

            # Show file details
            file_details = []
            for file in uploaded_files:
                file_details.append({
                    'Archivo': file.name,
                    'Tamaño': f"{file.size / 1024:.1f} KB",
                    'Tipo': 'ZIP' if file.name.lower().endswith('.zip') else 'XML'
                })

            df_files = pd.DataFrame(file_details)
            st.dataframe(df_files, use_container_width=True)

    with tab2:
        # Adapting for Streamlit Cloud - Local file access not available
        st.warning("""
        ⚠️ **Limitación en Streamlit Cloud**

        La búsqueda por ruta no está disponible en la nube. En su lugar, utiliza:
        """)

        st.markdown("""
        ### 📂 **Alternativas para subir archivos:**

        1. **🗜️ Sube un archivo ZIP** con todos tus XMLs
           - Comprime tus archivos XML en un .zip
           - Máximo 200MB por archivo ZIP
           - Usa la pestaña "Subir Archivos"

        2. **📄 Sube archivos XML individuales**
           - Selecciona múltiples archivos XML
           - Arrastra y suelta los archivos

        3. **💡 Procesamiento por lotes**
           - Procesa en grupos de 50-100 archivos
           - Descarga los resultados entre lotes
        """)

        st.info("""
        **📌 Formatos soportados:**
        - ✅ Archivos XML individuales (.xml)
        - ✅ Archivos ZIP con múltiples XMLs (.zip)
        - ✅ Carga por lotes de archivos

        **🚀 Para desarrollo local:**
        Si ejecutas la aplicación localmente, esta función de búsqueda por ruta está disponible.
        """)

        # Optional: Add a section explaining XML format for users
        st.markdown("---")
        st.markdown("### 📋 **Formato de XML aceptado:**")
        st.code("""
Estructura básica del XML de nómina SAT:
- Extensión: .xml
- Con complemento <nomina12:Nomina>
- Contiene datos del empleado: RFC, CURP, NSS
- Información salarial y contractual
        """, language="xml")

    # Enhanced process button with better styling
    has_files = bool(uploaded_files)

    # Add file status indicator with dark theme
    if has_files:
        st.markdown("""
        <div style='background: rgba(6, 117, 46, 0.15); color: #1a7f37; padding: 1rem; border-radius: 6px;
                    border: 1px solid rgba(6, 117, 46, 0.4); text-align: center; margin: 1rem 0;'>
            ✅ <strong>Archivos listos para procesar</strong>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background: rgba(255, 193, 7, 0.15); color: #ffc107; padding: 1rem; border-radius: 6px;
                    border: 1px solid rgba(255, 193, 7, 0.4); text-align: center; margin: 1rem 0;'>
            ⚠️ <strong>Por favor, carga archivos primero</strong>
        </div>
        """, unsafe_allow_html=True)

    # Center the process button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Procesar Archivos", type="primary", disabled=not has_files,
                    use_container_width=True, help="Inicia el procesamiento de los archivos XML"):
            with st.spinner("⏳ Procesando archivos..."):
                try:
                    temp_files = []
                    files_to_process = []

                    # Handle uploaded files
                    if uploaded_files:
                        temp_files = extract_xml_files(uploaded_files)
                        files_to_process.extend(temp_files)

                    if not files_to_process:
                        st.error("❌ No se encontraron archivos XML válidos")
                        return

                    # Process files
                    extractor = EmployeeDatabaseExtractor()
                    employees_df = extractor.process_xml_files(files_to_process)

                    # Clean up temp files (only from uploaded files)
                    clean_temp_files(temp_files)

                    if employees_df.empty:
                        st.error("❌ No se pudo extraer información de empleados de los archivos")
                        return

                    # Add descriptions (already integrated in extractor)
                    # employees_df = extractor.add_descriptions(employees_df)

                    # Enhanced success message with dark styling
                    st.markdown(f"""
                <div style='background: linear-gradient(135deg, rgba(13, 17, 23, 0.8) 0%, rgba(6, 117, 46, 0.2) 100%);
                            color: #1a7f37; padding: 1.5rem; border-radius: 8px;
                            border: 2px solid rgba(6, 117, 46, 0.4); text-align: center; margin: 1rem 0;
                            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);'>
                    <h3 style='margin: 0; font-size: 1.4em; color: #1a7f37;'>🎉 ¡Procesamiento Exitoso!</h3>
                    <p style='margin: 0.5rem 0; font-size: 1.1em; color: #e6edf3;'>Se procesaron exitosamente <strong>{len(employees_df)} empleados únicos</strong></p>
                </div>
                """, unsafe_allow_html=True)

                    # Enhanced catalog status with dark theme
                    if extractor.catalog_manager.is_loaded():
                        st.markdown(f"""
                        <div style='background: rgba(6, 117, 46, 0.1); color: #1a7f37; padding: 1rem; border-radius: 6px;
                                    border-left: 4px solid #06752e; margin: 1rem 0; border: 1px solid rgba(6, 117, 46, 0.2);'>
                            📚 <strong>Catálogos SAT cargados:</strong> {len(extractor.catalog_manager.get_available_catalogs())} catálogos disponibles
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div style='background: rgba(255, 193, 7, 0.1); color: #ffc107; padding: 1rem; border-radius: 6px;
                                    border-left: 4px solid #ffc107; margin: 1rem 0; border: 1px solid rgba(255, 193, 7, 0.2);'>
                            ⚠️ <strong>Nota:</strong> No se cargaron los catálogos SAT. Se usarán catálogos manuales como respaldo.
                        </div>
                        """, unsafe_allow_html=True)

                    # Show data summary
                    st.subheader("📊 Resumen de Datos")
                    show_data_summary(employees_df)

                    # Display data table
                    st.subheader("📋 Vista Previa de Datos")

                    # Column selection for display
                    all_columns = list(employees_df.columns)
                    # Determine default columns (descriptions are now primary values)
                    default_columns = ['rfc_empleado', 'nombre_empleado', 'curp', 'num_seguridad_social']

                    # Add main data columns (descriptions are now primary values)
                    default_columns.extend(['tipo_contrato', 'departamento', 'puesto', 'codigo_postal'])
                    default_columns.extend(['fecha_inicio_rel_laboral', 'antigüedad', 'salario_diario_integrado'])

                    selected_columns = st.multiselect(
                            "Selecciona columnas para mostrar:",
                            options=all_columns,
                            default=default_columns,
                            help="Selecciona las columnas que quieres visualizar. Los códigos ya están decodificados como descripciones legibles."
                        )

                    if selected_columns:
                        display_df = employees_df[selected_columns].copy()
                        st.dataframe(display_df, use_container_width=True, hide_index=True)

                    # Full data expander
                    with st.expander("📊 Ver Todos los Datos"):
                        st.dataframe(employees_df, use_container_width=True, hide_index=True)

                    # Data analysis section
                    st.subheader("📈 Análisis de Datos")

                    col1, col2 = st.columns(2)

                    with col1:
                        # Employers distribution
                        if 'nombre_empleador' in employees_df.columns:
                            st.write("**Distribución por Empleador:**")
                            employer_counts = employees_df['nombre_empleador'].value_counts().head(10)
                            st.bar_chart(employer_counts)

                    with col2:
                        # Contract type distribution
                        if 'tipo_contrato' in employees_df.columns:
                            st.write("**Distribución por Tipo de Contrato:**")
                            contract_counts = employees_df['tipo_contrato'].value_counts()
                            st.bar_chart(contract_counts)

                    # Enhanced download section with dark styling
                    st.markdown("""
                    <div style='background: rgba(13, 17, 23, 0.6); border: 1px solid rgba(6, 117, 46, 0.3);
                                padding: 1.5rem; border-radius: 8px; margin-bottom: 1rem;
                                box-shadow: 0 4px 8px rgba(0,0,0,0.2);'>
                        <h2 style='color: #1a7f37; margin-top: 0; margin-bottom: 1rem;'>💾 Descargar Base de Datos</h2>
                    </div>
                    """, unsafe_allow_html=True)

                    col1, col2 = st.columns(2)

                    with col1:
                        # Enhanced Excel download
                        excel_data = create_excel_download(employees_df)
                        st.markdown("""
                        <div style='text-align: center; padding: 1rem; background: rgba(13, 17, 23, 0.8); border-radius: 6px;
                                    border: 1px solid rgba(6, 117, 46, 0.3); margin-bottom: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>
                            <h4 style='color: #1a7f37; margin-top: 0;'>📊 Formato Excel</h4>
                            <p style='color: #e6edf3; font-size: 0.9em;'>Con formato profesional y estilos</p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.download_button(
                            label="📥 Descargar Excel",
                            data=excel_data,
                            file_name=f"base_empleados_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )

                    with col2:
                        # Enhanced CSV download
                        csv_data = employees_df.to_csv(index=False, encoding='utf-8-sig')
                        st.markdown("""
                        <div style='text-align: center; padding: 1rem; background: rgba(13, 17, 23, 0.8); border-radius: 6px;
                                    border: 1px solid rgba(6, 117, 46, 0.3); margin-bottom: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>
                            <h4 style='color: #1a7f37; margin-top: 0;'>📄 Formato CSV</h4>
                            <p style='color: #e6edf3; font-size: 0.9em;'>Compatibilidad universal</p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.download_button(
                            label="📥 Descargar CSV",
                            data=csv_data,
                            file_name=f"base_empleados_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )

                    # Statistics section
                    st.subheader("📊 Estadísticas Detalladas")

                    # Show data quality metrics
                    quality_metrics = {
                        'Total Registros': len(employees_df),
                        'RFCs Únicos': employees_df['rfc_empleado'].nunique(),
                        'CURPs Válidas': employees_df['curp'].notna().sum(),
                        'NSS Registrados': employees_df['num_seguridad_social'].notna().sum(),
                        'Con Salario Registrado': employees_df['salario_diario_integrado'].notna().sum(),
                        'Con Fecha de Inicio': employees_df['fecha_inicio_rel_laboral'].notna().sum()
                    }

                    metrics_df = pd.DataFrame(list(quality_metrics.items()),
                                                 columns=['Métrica', 'Cantidad'])
                    st.dataframe(metrics_df, use_container_width=True, hide_index=True)

                except Exception as e:
                    st.error(f"❌ Error durante el procesamiento: {str(e)}")
                    logger.error(f"Error processing files: {e}", exc_info=True)

    # Footer with dark theme
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #e6edf3; padding: 20px; border-top: 1px solid rgba(6, 117, 46, 0.3); background: rgba(13, 17, 23, 0.8); border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);'>
        <p style='font-size: 1.1em; margin-bottom: 10px;'>🏢 <strong style='color: #1a7f37;'>Generador de Base de Datos de Empleados XML</strong></p>
        <p style='color: #c9d1d9; margin: 5px 0;'>Procesa XMLs de nómina del SAT para crear una base de datos estructurada de empleados</p>
        <p style='color: #1a7f37; font-weight: 500; margin-top: 10px;'>✨ Características: Eliminación automática de duplicados • Exportación a Excel • Análisis de datos</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()