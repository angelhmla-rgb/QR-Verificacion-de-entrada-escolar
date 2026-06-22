import re
import json
import os
import gspread
import requests
from datetime import datetime
from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles  # Soporte para carga de librería local
from pydantic import BaseModel
from google.oauth2.service_account import Credentials
from bs4 import BeautifulSoup

# INICIALIZACIÓN DE LA APLICACIÓN
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# MONTAJE DE ARCHIVOS ESTÁTICOS LOCALES (EVITA BLOQUEOS DE RED EN EL PLANTEL)
app.mount("/static", StaticFiles(directory="static"), name="static")

# CONFIGURACIÓN DE SEGURIDAD
CLAVE_SECRETA = "Prefectura2026"  
COOKIE_NAME = "sesion_prefecto"

# CONFIGURACIÓN DE LA API DE WHATSAPP
WHATSAPP_API_URL = "http://tu-servicio-whatsapp-interno.railway.internal/send-message"
WHATSAPP_TOKEN = "UnTokenSeguroCreadoPorTi"

# VARIABLES GLOBALES DE CACHÉ
CACHE_TUTORES = {}

# MODELOS DE DATOS (PYDANTIC)
class EntradaQR(BaseModel):
    texto_qr: str

class NuevoAlumno(BaseModel):
    key_qr: str
    url_credencial: str
    num_control: str
    alumno: str
    telefono_tutor: str
    curp: str = ""
    especialidad: str = ""
    semestre: str = ""
    plantel: str = ""
    imss: str = ""

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

# Sincronización en memoria RAM
def actualizar_cache_tutores():
    global CACHE_TUTORES
    try:
        doc = conectar_sheets()
        pestaña_tutores = doc.worksheet("Directorio_Tutores")
        todas_las_filas = pestaña_tutores.get_all_values()
        
        nueva_cache = {}
        for fila in todas_las_filas[1:]:
            if len(fila) >= 5 and fila[4].strip():
                nueva_cache[fila[4].strip()] = {
                    "num_control": fila[0],
                    "alumno": fila[1],
                    "telefono_tutor": fila[2],
                    "status": fila[3]
                }
        CACHE_TUTORES = nueva_cache
        print("⚡ [CACHÉ] Base de datos sincronizada exitosamente.")
    except Exception as e:
        print(f"❌ Error al inicializar la caché: {str(e)}")

@app.on_event("startup")
async def startup_event():
    actualizar_cache_tutores()

def extraer_datos_cecytec(url: str):
    datos = {
        "num_control": "", "alumno": "", "status": "ACTIVO", 
        "curp": "", "especialidad": "", "semestre": "", 
        "plantel": "", "imss": ""
    }
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        response = requests.get(url, headers=headers, timeout=7)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            texto_pagina = soup.get_text()

            patrones = {
                "alumno": r"NOMBRE DEL ALUMNO:\s*([^\n\r]+)",
                "num_control": r"NUMERO DE CONTROL:\s*([^\n\r]+)",
                "curp": r"CURP:\s*([^\n\r]+)",
                "imss": r"IMSS:\s*([^\n\r]+)",
                "especialidad": r"ESPECIALIDAD:\s*([^\n\r]+)",
                "semestre": r"SEMESTRE ACTUAL:\s*([^\n\r]+)",
                "plantel": r"NOMBRE DEL PLANTEL:\s*([^\n\r]+)",
                "status": r"STATUS:\s*([^\n\r]+)"
            }
            
            for clave, patron in patrones.items():
                match = re.search(patron, texto_pagina, re.IGNORECASE)
                if match:
                    datos[clave] = match.group(1).strip()
    except Exception as scrape_err:
        print(f"⚠️ Alerta durante Scraping: {str(scrape_err)}")
    return datos

def enviar_mensaje_whatsapp(telefono_tutor, mensaje):
    if not str(telefono_tutor).startswith("52"):
        telefono_tutor = f"52{telefono_tutor}"
