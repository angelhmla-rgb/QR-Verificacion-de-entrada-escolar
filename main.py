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
            if len(fila) >= 5 and fila[4].strip():
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
        tipo_evento = "ENTRADA"
        
        for fila in registros_hoy:
            if len(fila) >= 4 and fila[0].startswith(fecha_registro) and fila[1] == num_control:
                if fila[3] == "ENTRADA":
                    tipo_evento = "SALIDA"

        # Escritura en Google Sheets
        pestaña_asistencia.append_row([
            f"{fecha_registro} {hora_registro}", 
            num_control, 
            alumno, 
            tipo_evento, 
            "Permitido"
        ])
        
        # Envío del mensaje de WhatsApp
        if telefono_tutor and str(telefono_tutor).strip():
            saludo = "Buenos días" if "AM" in hora_registro else "Buenas tardes"
            mensaje_wa = f"📝 *CECYTEC Informa:*\n\n{saludo}, le notificamos que el alumno(a) *{alumno}* ha registrado su *{tipo_evento}* del plantel el día de hoy a las {hora_registro}."
            enviar_mensaje_whatsapp(telefono_tutor, mensaje_wa)
            
        print(f"✅ Asistencia registrada de fondo para {alumno} ({tipo_evento})")
    except Exception as e:
        print(f"❌ Error en tarea asíncrona de Sheets/WhatsApp: {str(e)}")

# Pantalla de inicio de sesión / Filtro de seguridad
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    sesion = request.cookies.get(COOKIE_NAME)
    if sesion == CLAVE_SECRETA:
        return templates.TemplateResponse("index.html", {"request": request})
    
    html_login = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Acceso Restringido - CECYTEC</title>
        <style>
            body { font-family: sans-serif; background: #f4f6f9; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); text-align: center; max-width: 360px; width: 90%; }
            h2 { color: #2c3e50; margin-bottom: 10px; }
            p { color: #7f8c8d; font-size: 14px; margin-bottom: 20px; }
            input[type="password"] { width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; font-size: 16px; }
            button { width: 100%; padding: 12px; background: #00875a; color: white; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; font-weight: bold; }
            button:hover { background: #006c48; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>⚠️ Control de Acceso</h2>
            <p>Esta página es de uso exclusivo para el personal autorizado en la puerta del plantel.</p>
            <form method="post" action="/login">
                <input type="password" name="clave" placeholder="Contraseña de Prefectura" required>
                <button type="submit">Iniciar Escáner</button>
            </form>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_login)

# Procesar la contraseña ingresada
@app.post("/login")
async def login(clave: str = Form(...)):
    if clave == CLAVE_SECRETA:
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key=COOKIE_NAME, value=CLAVE_SECRETA, max_age=28800)
        return response
    return HTMLResponse(content="<script>alert('Contraseña Incorrecta'); window.location='/';</script>")

# Procesador de códigos QR con Búsqueda Ultra Rápida en RAM
@app.post("/registrar-asistencia")
async def registrar_asistencia(data: EntradaQR, request: Request, background_tasks: BackgroundTasks):
    if request.cookies.get(COOKIE_NAME) != CLAVE_SECRETA:
        return {"status": "error", "mensaje": "No autorizado para registrar asistencia."}

    texto = data.texto_qr
    key_match = re.search(r"[?&]key=([^&]+)", texto)
    
    if not key_match:
        return {"status": "error", "mensaje": "Código QR no válido. No contiene un formato oficial de credencial CECYTEC."}
    
    key_alumno = key_match.group(1).strip()
    
    # BÚSQUEDA INSTANTÁNEA EN MEMORIA CACHÉ
    if key_alumno not in CACHE_TUTORES:
        return {
            "status": "nuevo_registro", 
            "key_qr": key_alumno,
            "mensaje": "Nueva credencial detectada. ¿Deseas dar de alta al alumno en el sistema?"
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

    # Lanzamos el proceso pesado en segundo plano
    background_tasks.add_task(
        procesar_asistencia_en_segundo_plano,
        num_control, alumno, telefono_tutor, fecha_registro, hora_registro
    )
    
    return {
        "status": "exito",
        "mensaje": f"Procesando acceso para: {alumno}. ¡Siguiente en la fila!"
    }

# NUEVO ENDPOINT: Registra alumnos nuevos y actualiza la caché al instante
@app.post("/dar-de-alta")
async def dar_de_alta(alumno_data: NuevoAlumno, request: Request):
    if request.cookies.get(COOKIE_NAME) != CLAVE_SECRETA:
        return {"status": "error", "mensaje": "No autorizado para realizar esta acción."}
    
    try:
        doc = conectar_sheets()
        pestaña_tutores = doc.worksheet("Directorio_Tutores")
        
        # Insertar en orden estricto de columnas (A-E)
        pestaña_tutores.append_row([
            alumno_data.num_control.strip(),
            alumno_data.alumno.strip().upper(),
            alumno_data.telefono_tutor.strip(),
            "ACTIVO",
            alumno_data.key_qr.strip()
        ])
        
        # Forzar la recarga de la caché en memoria RAM
        actualizar_cache_tutores()
        
        return {"status": "exito", "mensaje": f"El alumno {alumno_data.alumno} fue registrado de forma exitosa y ya está ACTIVO."}
    except Exception as e:
        return {"status": "error", "mensaje": f"Fallo al escribir en Google Sheets: {str(e)}"}
