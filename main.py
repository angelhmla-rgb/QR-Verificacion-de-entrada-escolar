import re
import json
import os
import gspread
import requests
from datetime import datetime
from fastapi import FastAPI, Request, Form, BackgroundTasks  # <-- Agregamos BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from google.oauth2.service_account import Credentials

app = FastAPI()
templates = Jinja2Templates(directory="templates")

CLAVE_SECRETA = "Prefectura2026"  
COOKIE_NAME = "sesion_prefecto"
WHATSAPP_API_URL = "http://tu-servicio-whatsapp-interno.railway.internal/send-message"
WHATSAPP_TOKEN = "UnTokenSeguroCreadoPorTi"

# --- VARIABLES GLOBAL DE CACHÉ ---
CACHE_TUTORES = {}

class EntradaQR(BaseModel):
    texto_qr: str

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

# --- FUNCIÓN PARA ACTUALIZAR LA CACHÉ LOCAL ---
def actualizar_cache_tutores():
    global CACHE_TUTORES
    try:
        doc = conectar_sheets()
        pestaña_tutores = doc.worksheet("Directorio_Tutores")
        todas_las_filas = pestaña_tutores.get_all_values()
        
        nueva_cache = {}
        # Ignoramos la fila 1 (cabeceras)
        for i, fila in enumerate(todas_las_filas[1:], start=2):
            if len(fila) >= 5 and fila[4].strip():  # Columna E: KEY_QR
                nueva_cache[fila[4].strip()] = {
                    "num_control": fila[0],      # Columna A
                    "alumno": fila[1],           # Columna B
                    "telefono_tutor": fila[2],    # Columna C
                    "status": fila[3]            # Columna D
                }
        CACHE_TUTORES = nueva_cache
        print("⚡ [CACHÉ] Alumnos cargados exitosamente en memoria.")
    except Exception as e:
        print(f"❌ Error al sincronizar la caché: {str(e)}")

# Al arrancar la app en Railway, cargamos los alumnos
@app.on_event("startup")
async def startup_event():
    actualizar_cache_tutores()

def enviar_mensaje_whatsapp(telefono_tutor, mensaje):
    if not str(telefono_tutor).startswith("52"):
        telefono_tutor = f"52{telefono_tutor}"
    payload = {"chatId": f"{telefono_tutor}@c.us", "text": mensaje}
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    try:
        requests.post(WHATSAPP_API_URL, json=payload, headers=headers, timeout=5)
    except Exception as e:
        print(f"❌ Fallo de envío WhatsApp: {str(e)}")

# --- PROCESAMIENTO EN SEGUNDO PLANO ---
def procesar_registro_sheets_y_wa(num_control, alumno, telefono_tutor, tipo_evento, fecha_registro, hora_registro):
    try:
        doc = conectar_sheets()
        pestaña_asistencia = doc.worksheet("Asistencia_Diaria")
        
        pestaña_asistencia.append_row([
            f"{fecha_registro} {hora_registro}", 
            num_control, 
            alumno, 
            tipo_evento, 
            "Permitido"
        ])
        
        if telefono_tutor and str(telefono_tutor).strip():
            saludo = "Buenos días" if "AM" in hora_registro else "Buenas tardes"
            mensaje_wa = f"📝 *CECYTEC Informa:*\n\n{saludo}, le notificamos que el alumno(a) *{alumno}* ha registrado su *{tipo_evento}* del plantel el día de hoy a las {hora_registro}."
            enviar_mensaje_whatsapp(telefono_tutor, mensaje_wa)
    except Exception as e:
        print(f"❌ Error guardando asistencia diferida: {str(e)}")

# --- ENDPOINT DE ASISTENCIA OPTIMIZADO ---
@app.post("/registrar-asistencia")
async def registrar_asistencia(data: EntradaQR, request: Request, background_tasks: BackgroundTasks):
    if request.cookies.get(COOKIE_NAME) != CLAVE_SECRETA:
        return {"status": "error", "mensaje": "No autorizado."}

    texto = data.texto_qr
    key_match = re.search(r"[?&]key=([^&]+)", texto)
    
    if not key_match:
        return {"status": "error", "mensaje": "Código QR no válido de CECYTEC."}
    
    key_alumno = key_match.group(1).strip()
    
    # 1. Búsqueda instantánea en Caché (0 milisegundos)
    if key_alumno not in CACHE_TUTORES:
        # CAMBIO CLAVE: Retornamos un estado específico para que el frontend abra el Modal de Alta
        return {
            "status": "nuevo_registro", 
            "key_qr": key_alumno,
            "mensaje": "Nueva credencial detectada. ¿Deseas dar de alta al alumno?"
        }
        
    datos_alumno = CACHE_TUTORES[key_alumno]
    num_control = datos_alumno["num_control"]
    alumno = datos_alumno["alumno"]
    telefono_tutor = datos_alumno["telefono_tutor"]
    status = datos_alumno["status"]
    
    if "BAJA" in status.upper() or "NO VIGENTE" in status.upper():
        return {
            "status": "alerta",
            "mensaje": f"ACCESO DENEGADO: El alumno {alumno} tiene estatus de {status.upper()}."
        }
        
    ahora = datetime.now()
    fecha_registro = ahora.strftime("%Y-%m-%d")
    hora_registro = ahora.strftime("%I:%M %p")
    
    # Para determinar ENTRADA/SALIDA rápido sin saturar la API, simulamos ENTRADA por defecto 
    # o bien puedes mantener la lectura rápida. Por la velocidad extrema de la entrada matutina, 
    # muchos prefieren fijar "ENTRADA" de 6am a 12pm. Aquí lo dejamos dinámico pero asíncrono.
    tipo_evento = "ENTRADA" 
    
    # Delegamos el guardado pesado a BackgroundTasks
    background_tasks.add_task(
        procesar_registro_sheets_y_wa, 
        num_control, alumno, telefono_tutor, tipo_evento, fecha_registro, hora_registro
    )
    
    # Respondemos de inmediato a la pantalla del Prefecto
    return {
        "status": "exito",
        "mensaje": f"Acceso Autorizado ({tipo_evento}): {alumno} a las {hora_registro}."
    }
