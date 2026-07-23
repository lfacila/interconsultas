import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

st.set_page_config(page_title="Interconsultas · Cardiología", page_icon="🫀", layout="wide")

# 1. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Cargar datos desde las pestañas
try:
    df_registro = conn.read(worksheet="Registro", ttl=0).dropna(how="all")
    df_listas = conn.read(worksheet="Listas", ttl=0).dropna(how="all")
except Exception as e:
    st.error(f"Error técnico exacto: {e}")
    st.stop()

# Convertir columnas de listas a listas de Python, limpiando nulos
listas = {
    'centro': df_listas['centro'].dropna().astype(str).tolist() if 'centro' in df_listas.columns else [],
    'medico': df_listas['medico'].dropna().astype(str).tolist() if 'medico' in df_listas.columns else [],
    'especialidad': df_listas['especialidad'].dropna().astype(str).tolist() if 'especialidad' in df_listas.columns else []
}

MOTIVOS = [
    "Dolor torácico", "Disnea / Insuficiencia cardíaca", "Palpitaciones / Arritmia", "Síncope / Presíncope", "Edemas",
    "ECG alterado", "Ecocardiograma", "Prueba de esfuerzo", "Holter / MAPA", "Soplo cardíaco",
    "Cardiopatía isquémica", "Fibrilación auricular", "Insuficiencia cardíaca", "Valvulopatía", "HTA de difícil control", "Miocardiopatía", "Riesgo cardiovascular alto",
    "Preoperatorio cardiológico", "Seguimiento", "Otro motivo"
]

st.title("🫀 Registro de Interconsultas · Cardiología")

tab1, tab2, tab3, tab4 = st.tabs(["➕ Nueva", "📋 Registro", "📊 Estadísticas", "⚙️ Listas"])

# ══════════════ NUEVA INTERCONSULTA ══════════════
with tab1:
    st.header("Nueva interconsulta")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fecha = st.date_input("Fecha", datetime.today())
        tipo = st.selectbox("Tipo de origen", ["Atención Primaria", "Especialidad Hospitalaria", "Urgencias", "Otro"])
        
        especialidad = ""
        if tipo == "Especialidad Hospitalaria":
            especialidad = st.selectbox("Especialidad remitente", [""] + listas['especialidad'])
            
        centro = st.selectbox("Centro / Hospital", [""] + listas['centro'])
        medico = st.selectbox("Médico remitente", [""] + listas['medico'])

    with col2:
        motivo = st.selectbox("Motivo principal", [""] + MOTIVOS)
        motivo_otro = ""
        if motivo == "Otro motivo":
            motivo_otro = st.text_input("Especificar motivo")
            
        urgencia = st.selectbox("Urgencia", ["Normal", "Preferente", "Urgente"])
        notas = st.text_area("Notas / Observaciones", height=100)

    if st.button("💾 Guardar interconsulta", type="primary"):
        if not centro or not medico or not motivo:
            st.error("Por favor, completa Centro, Médico y Motivo.")
        else:
            motivo_final = motivo_otro if motivo == "Otro motivo" and motivo_otro else motivo
            nueva_ic = pd.DataFrame([{
                "id": str(datetime.now().timestamp()),
                "fecha": fecha.strftime("%Y-%m-%d"),
                "tipo": tipo,
                "centro": centro,
                "especialidad": especialidad,
                "medico": medico,
                "motivo": motivo_final,
                "urgencia": urgencia,
                "notas": notas
            }])
            
            # Unir y guardar en Sheets
            df_actualizado = pd.concat([df_registro, nueva_ic], ignore_index=True)
            conn.update(worksheet="Registro", data=df_actualizado)
            st.success("Interconsulta guardada correctamente en Google Sheets.")
            st.rerun()

# ══════════════ REGISTRO ══════════════
with tab2:
    st.header("Registro de Interconsultas")
    
    if df_registro.empty:
        st.info("No hay registros todavía.")
    else:
        # Filtros
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            buscar = st.text_input("🔍 Buscar texto")
        with f_col2:
            filtro_tipo = st.selectbox("Filtrar por Tipo", ["Todos"] + df_registro['tipo'].unique().tolist())
        with f_col3:
            filtro_urgencia = st.selectbox("Filtrar por Urgencia", ["Todas", "Normal", "Preferente", "Urgente"])

        # Aplicar filtros
        df_filtrado = df_registro.copy()
        if buscar:
            df_filtrado = df_filtrado[df_filtrado.apply(lambda row: row.astype(str).str.contains(buscar, case=False).any(), axis=1)]
        if filtro_tipo != "Todos":
            df_filtrado = df_filtrado[df_filtrado['tipo'] == filtro_tipo]
        if filtro_urgencia != "Todas":
            df_filtrado = df_filtrado[df_filtrado['urgencia'] == filtro_urgencia]

        st.dataframe(df_filtrado.drop(columns=['id'], errors='ignore'), use_container_width=True, hide_index=True)

# ══════════════ ESTADÍSTICAS ══════════════
with tab3:
    st.header("Estadísticas de Derivaciones")
    
    if df_registro.empty:
        st.warning("No hay datos suficientes para mostrar estadísticas.")
    else:
        total = len(df_registro)
        urgentes = len(df_registro[df_registro['urgencia'] == 'Urgente'])
        pct_primaria = round((len(df_registro[df_registro['tipo'] == 'Atención Primaria']) / total) * 100, 1) if total > 0 else 0
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Interconsultas", total)
        kpi2.metric("Atención Primaria", f"{pct_primaria}%")
        kpi3.metric("Derivaciones Urgentes", urgentes)
        kpi4.metric("Centros distintos", df_registro['centro'].nunique())
        st.divider()

        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("Por tipo de origen")
            fig_tipo = px.pie(df_registro, names='tipo', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_tipo, use_container_width=True)

        with col_chart2:
            st.subheader("Urgencia")
            fig_urg = px.pie(df_registro, names='urgencia', color_discrete_sequence=['#2ecc71', '#f1c40f', '#e74c3c'])
            st.plotly_chart(fig_urg, use_container_width=True)

# ══════════════ LISTAS ══════════════
with tab4:
    st.header("Gestión de Catálogos")
    st.write("Añade elementos para los menús desplegables.")
    
    l_col1, l_col2, l_col3 = st.columns(3)
    
    def manage_list(col, title, dict_key, placeholder):
        with col:
            st.subheader(title)
            new_item = st.text_input(placeholder, key=f"input_{dict_key}")
            if st.button("➕ Añadir", key=f"btn_{dict_key}"):
                if new_item and new_item not in listas[dict_key]:
                    listas[dict_key].append(new_item)
                    # Reconstruir DataFrame de listas
                    max_len = max(len(listas['centro']), len(listas['medico']), len(listas['especialidad']))
                    
                    df_actualizado = pd.DataFrame({
                        'centro': listas['centro'] + [''] * (max_len - len(listas['centro'])),
                        'medico': listas['medico'] + [''] * (max_len - len(listas['medico'])),
                        'especialidad': listas['especialidad'] + [''] * (max_len - len(listas['especialidad']))
                    })
                    conn.update(worksheet="Listas", data=df_actualizado)
                    st.success("Añadido correctamente.")
                    st.rerun()
            
            st.write("Elementos actuales:")
            for item in listas[dict_key]:
                if str(item).strip() != "":
                    st.write(f"- {item}")

    manage_list(l_col1, "🏥 Centros", "centro", "Añadir centro...")
    manage_list(l_col2, "👨‍⚕️ Médicos", "medico", "Añadir médico...")
    manage_list(l_col3, "🔬 Especialidades", "especialidad", "Añadir especialidad...")
