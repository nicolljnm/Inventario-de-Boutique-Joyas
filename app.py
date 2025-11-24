import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import os

# --- Configuración de Archivos y Credenciales ---
RUTA_ARCHIVO = "inventario_joyas.csv"

# Lectura segura de credenciales
# Estas variables se leerán desde el archivo .streamlit/secrets.toml
try:
    EMAIL_EMISOR = st.secrets["email"]["emisor"]
    PASSWORD_APP = st.secrets["email"]["password_app"]
    EMAIL_RECEPTOR = st.secrets["email"]["receptor"]
except Exception:
    # Caso de emergencia si no se cargan los secretos
    EMAIL_EMISOR = os.environ.get("EMAIL_EMISOR", "nicolljirethnm@gmail.com")
    PASSWORD_APP = os.environ.get("PASSWORD_APP", "tu_password_de_aplicacion")
    EMAIL_RECEPTOR = os.environ.get("EMAIL_RECEPTOR", "carlojoseb05@gmail.com")

SERVIDOR_SMTP = "smtp.gmail.com"
PUERTO_SMTP = 587

COLUMNAS = ['ID', 'Nombre', 'Cantidad', 'Precio_COP', 'Stock_Minimo']

# --- Funciones ---

@st.cache_data
def cargar_datos():
    """Carga los datos del archivo CSV o crea un DataFrame inicial si no existe."""
    try:
        df = pd.read_csv(RUTA_ARCHIVO)
        # Asegura que las columnas numéricas sean integers
        df['Cantidad'] = df['Cantidad'].astype(int)
        df['Precio_COP'] = df['Precio_COP'].astype(int)
        df['Stock_Minimo'] = df['Stock_Minimo'].astype(int)
        return df
    except FileNotFoundError:
        st.error(f"Error: El archivo de datos '{RUTA_ARCHIVO}' no fue encontrado.")
        return pd.DataFrame(columns=COLUMNAS)
    except Exception as e:
        st.error(f"Error al cargar o procesar el CSV: {e}")
        return pd.DataFrame(columns=COLUMNAS)

def guardar_datos(df):
    """Guarda el DataFrame actualizado en el archivo CSV."""
    df.to_csv(RUTA_ARCHIVO, index=False)

def enviar_alerta(productos_df):
    """Envía un correo electrónico con la lista de productos con stock bajo."""
    if productos_df.empty:
        return

    cuerpo = "ALERTA: Stock bajo en los siguientes productos:\n\n"

    for _, p in productos_df.iterrows():
        # Formato del precio con separador de miles (punto)
        precio = f"{int(p['Precio_COP']):,}".replace(",", ".")
        cuerpo += (
            f"{p['Nombre']} - Stock: {p['Cantidad']} "
            f"/ Min: {p['Stock_Minimo']} / ${precio}\n"
        )

    try:
        msg = MIMEText(cuerpo)
        msg["Subject"] = "ALERTA INVENTARIO"
        msg["From"] = EMAIL_EMISOR
        msg["To"] = EMAIL_RECEPTOR

        with smtplib.SMTP(SERVIDOR_SMTP, PUERTO_SMTP) as s:
            s.starttls()
            s.login(EMAIL_EMISOR, PASSWORD_APP)
            s.sendmail(EMAIL_EMISOR, EMAIL_RECEPTOR, msg.as_string())

        st.success("Correo enviado correctamente.")
    except Exception as e:
        st.error(f"Error enviando correo. Asegúrate de que las credenciales son correctas: {e}")

# --- Interfaz de Usuario de Streamlit ---

st.title("Inventario de Joyería")

df_inventario = cargar_datos()

if not df_inventario.empty:
    
    # 1. VISUALIZACIÓN DE DATOS Y FILTROS
    st.header("1. Inventario General")
    
    # Búsqueda
    texto_busqueda = st.text_input("Buscar por Nombre:", "")
    df_filtrado = df_inventario[
        df_inventario['Nombre'].str.contains(texto_busqueda, case=False, na=False)
    ]
    
    # Ordenar
    columna_orden = st.selectbox(
        "Ordenar por:", 
        options=['Nombre', 'Cantidad', 'Precio_COP', 'Stock_Minimo']
    )
    orden_ascendente = st.checkbox("Ascendente", value=True)
    df_filtrado = df_filtrado.sort_values(by=columna_orden, ascending=orden_ascendente)

    # Mostrar la tabla
    st.dataframe(df_filtrado, use_container_width=True)
    
    
    # 2. ALERTA DE STOCK BAJO
    st.header("2. Alertas")
    
    # Filtrar productos con stock bajo
    productos_bajo_stock = df_inventario[
        df_inventario['Cantidad'] <= df_inventario['Stock_Minimo']
    ].sort_values(by='Cantidad')
    
    st.subheader("⚠️ Productos con Stock Bajo")
    if productos_bajo_stock.empty:
        st.success("¡Todo el inventario está en buen nivel de stock!")
    else:
        st.warning(f"Hay {len(productos_bajo_stock)} productos con stock bajo.")
        st.dataframe(productos_bajo_stock, hide_index=True)
        
        if st.button("Enviar Alerta por Correo"):
            enviar_alerta(productos_bajo_stock)
            
    # 3. EDICIÓN Y ACTUALIZACIÓN
    st.header("3. Editar y Actualizar Inventario")
    
    # Usar el editor de datos de Streamlit
    df_editado = st.data_editor(
        df_inventario,
        num_rows="dynamic",
        use_container_width=True
    )
    
    if st.button("Guardar Cambios en Inventario"):
        try:
            # Validación simple antes de guardar
            if not all(col in df_editado.columns for col in COLUMNAS):
                 st.error("Columnas faltantes. Asegúrese de no borrar 'ID', 'Nombre', 'Cantidad', 'Precio_COP', o 'Stock_Minimo'.")
            else:
                # Asegurar tipos de datos correctos
                df_editado['Cantidad'] = pd.to_numeric(df_editado['Cantidad'], errors='coerce').fillna(0).astype(int)
                df_editado['Precio_COP'] = pd.to_numeric(df_editado['Precio_COP'], errors='coerce').fillna(0).astype(int)
                df_editado['Stock_Minimo'] = pd.to_numeric(df_editado['Stock_Minimo'], errors='coerce').fillna(0).astype(int)
                
                guardar_datos(df_editado)
                st.success("¡Inventario actualizado y guardado correctamente!")
                st.cache_data.clear() # Limpiar caché para recargar datos
                st.rerun() # Recargar la app para ver los cambios
                
        except Exception as e:
            st.error(f"Error al guardar: {e}")
