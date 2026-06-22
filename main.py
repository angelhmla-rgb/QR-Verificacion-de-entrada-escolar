import re
import json
import os
import gspread
import requests
from datetime import datetime
from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from google.oauth2.service_account import Credentials

# 1. INICIALIZACIÓN DE LA APLICACIÓN
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# CONFIGURACIÓN DE SEGURIDAD
CLAVE_SECRETA = "Prefectura2026"  
COOKIE_NAME = "sesion_prefecto"

# CONFIGURACIÓN DE LA API DE WHATSAPP
WHATSAPP_API_URL = "http://tu-servicio-whatsapp-interno.railway.internal/send-message"
WHATSAPP_TOKEN = "UnTokenSeguroCreadoPorTi"

# --- VARIABLES GLOBALES DE CACHÉ ---
CACHE_TUTORES = {}

# MODELOS DE DATOS (PYDANTIC)
class EntradaQR(BaseModel):
    texto_qr: str

class NuevoAlumno(BaseModel):
    key_qr: str
    num_control: str
    alumno: str
    telefono_tutor: str

# Conexión Segura con Google Sheets
def conectar_sheets():
    creds_json = os.environ.get("GOOGLE_CREDS")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    if creds_json:
        try:
            info = json.loads(creds_json)
            creds = Credentials.from_service_account_info(info, scopes=scope)
        except Exception as json_err:
            raise RuntimeError(f"Error al procesar el formato JSON de GOOGLE_CREDS: {str(json_err)}")
    else:
        creds = Credentials.from_service_account_file("cecytec-acceso-170202a5fd9f.json", scopes=scope)
        
    client = gspread.authorize(creds)
    return client.open_by_url("https://docs.google.com/spreadsheets/d/193NV0p1OQsZAZy-f-gtOQZE743lh6yC6GgtlYzTHTkY/edit?usp=sharing")

# Función para sincronizar la base de datos completa a la memoria RAM del servidor
def actualizar_cache_tutores():
    global CACHE_TUTORES
    try:
        doc = conectar_sheets()
        pestaña_tutores = doc.worksheet("Directorio_Tutores")
        todas_las_filas = pestaña_tutores.get_all_values()
        
        nueva_cache = {}
        # Estructura estricta: A: NUM_CONTROL, B: ALUMNO, C: TEL_TUTOR, D: STATUS, E: KEY_QR
        for fila in todas_las_filas[1:]:
            if len(fila) >= 5 and fila[4].strip():  # Validar que tenga KEY_QR en columna E
                nueva_cache[fila[4].strip()] = {
                    "num_control": fila[0],
                    "alumno": fila[1],
                    "telefono_tutor": fila[2],
                    "status": fila[3]
                }
        CACHE_TUTORES = nueva_cache
        print("⚡ [CACHÉ] Base de datos sincronizada en memoria con éxito.")
    except Exception as e:
        print(f"❌ Error crítico al inicializar la caché: {str(e)}")

# Evento de inicio: Carga los alumnos al arrancar el contenedor en Railway
@app.on_event("startup")
async def startup_event():
    actualizar_cache_tutores()

# Función para enviar las notificaciones a los tutores
def enviar_mensaje_whatsapp(telefono_tutor, mensaje):
    if not str(telefono_tutor).startswith("52"):
        telefono_tutor = f"52{telefono_tutor}"
        
    payload = {
        "chatId": f"{telefono_tutor}@c.us",
        "text": mensaje
    }
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        requests.post(WHATSAPP_API_URL, json=payload, headers=headers, timeout=5)
    except Exception as e:
        print(f"❌ Fallo de conexión con WhatsApp: {str(e)}")

# Proceso asíncrono en segundo plano para no retrasar la fila de alumnos en la entrada
def procesar_asistencia_en_segundo_plano(num_control, alumno, telefono_tutor, fecha_registro, hora_registro):
    try:
        doc = conectar_sheets()
        pestaña_asistencia = doc.worksheet("Asistencia_Diaria")
        
        # Determinación inteligente de ENTRADA/SALIDA leyendo la hoja de forma diferida
        registros_hoy = pestaña_asistencia.get_all_values()
        tipo_evento
