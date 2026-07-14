import re
import json
import os
import gspread
import requests
from datetime import datetime
from fastapi import FastAPI, Request, Form
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

class EntradaQR(BaseModel):
    texto_qr: str

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
        response = requests.post(WHATSAPP_API_URL, json=payload, headers=headers, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Fallo de conexión con WhatsApp: {str(e)}")
        return False

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

# Procesador de códigos QR con Extracción de KEY Automática para Nuevos Alumnos
@app.post("/registrar-asistencia")
async def registrar_asistencia(data: EntradaQR, request: Request):
    if request.cookies.get(COOKIE_NAME) != CLAVE_SECRETA:
        return {"status": "error", "mensaje": "No autorizado para registrar asistencia."}

    texto = data.texto_qr
    
    # Extraemos el parámetro 'key=' que viene dentro de la URL del QR
    key_match = re.search(r"[?&]key=([^&]+)", texto)
    
    if not key_match:
        return {"status": "error", "mensaje": "Código QR no válido. No contiene un formato oficial de credencial CECYTEC."}
    
    key_alumno = key_match.group(1).strip()
    
    try:
        doc = conectar_sheets()
        pestaña_tutores = doc.worksheet("Directorio_Tutores")
        pestaña_asistencia = doc.worksheet("Asistencia_Diaria")
        
        celda_alumno = pestaña_tutores.find(key_alumno)
        
        # MODIFICACIÓN CLAVE: Si la credencial NO existe, te muestra la Key limpia lista para copiar
        if not celda_alumno:
            return {
                "status": "error", 
                "mensaje": f"Nueva credencial detectada. Copia esta clave para tu Google Sheets:\n\n🔑 {key_alumno}"
            }
        
        fila_alumno = celda_alumno.row
        datos_alumno = pestaña_tutores.row_values(fila_alumno)
        
        num_control = datos_alumno[0]
        alumno = datos_alumno[1]
        telefono_tutor = datos_alumno[2] if len(datos_alumno) >= 3 else None
        status = datos_alumno[3] if len(datos_alumno) >= 4 else "ACTIVO"
        
        if "BAJA" in status.upper() or "NO VIGENTE" in status.upper():
            return {
                "status": "alerta",
                "mensaje": f"ACCESO DENEGADO: El alumno {alumno} tiene estatus de {status.upper()}."
            }
        
        ahora = datetime.now()
        fecha_registro = ahora.strftime("%Y-%m-%d")
        hora_registro = ahora.strftime("%I:%M %p")
        
        registros_hoy = pestaña_asistencia.get_all_values()
        tipo_evento = "ENTRADA"
        
        for fila in registros_hoy:
            if len(fila) >= 4 and fila[0].startswith(fecha_registro) and fila[1] == num_control:
                if fila[3] == "ENTRADA":
                    tipo_evento = "SALIDA"

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
        
        return {
            "status": "exito",
            "mensaje": f"Acceso Registrado ({tipo_evento}): {alumno} a las {hora_registro}."
        }
        
    except Exception as e:
        return {"status": "error", "mensaje": f"Error al conectar con Google Sheets: {str(e)}"}
