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
from bs4 import BeautifulSoup

app = FastAPI()
templates = Jinja2Templates(directory="templates")

CLAVE_SECRETA = "Prefectura2026"  
COOKIE_NAME = "sesion_prefecto"

WHATSAPP_API_URL = "http://tu-servicio-whatsapp-interno.railway.internal/send-message"
WHATSAPP_TOKEN = "UnTokenSeguroCreadoPorTi"

CACHE_TUTORES = {}

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
    """
    Visita silenciosamente la URL de CECYTEC y hace scraping de los campos de texto
    basado en las etiquetas de la estructura HTML oficial.
    """
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

            # Mapeo por expresiones regulares buscando los patrones visuales de la tarjeta
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
        
    payload = {"chatId": f"{telefono_tutor}@c.us", "text": mensaje}
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    try:
        requests.post(WHATSAPP_API_URL, json=payload, headers=headers, timeout=5)
    except Exception as e:
        print(f"❌ Fallo de conexión con WhatsApp: {str(e)}")

def procesar_asistencia_en_segundo_plano(num_control, alumno, telefono_tutor, fecha_registro, hora_registro):
    try:
        doc = conectar_sheets()
        pestaña_asistencia = doc.worksheet("Asistencia_Diaria")
        registros_hoy = pestaña_asistencia.get_all_values()
        tipo_evento = "ENTRADA"
        
        for fila in registros_hoy:
            if len(fila) >= 4 and fila[0].startswith(fecha_registro) and fila[1] == num_control:
                if fila[3] == "ENTRADA":
                    tipo_evento = "SALIDA"

        pestaña_asistencia.append_row([
            f"{fecha_registro} {hora_registro}", num_control, alumno, tipo_evento, "Permitido"
        ])
        
        if telefono_tutor and str(telefono_tutor).strip():
            saludo = "Buenos días" if "AM" in hora_registro else "Buenas tardes"
            mensaje_wa = f"📝 *CECYTEC Informa:*\n\n{saludo}, le notificamos que el alumno(a) *{alumno}* ha registrado su *{tipo_evento}* del plantel el día de hoy a las {hora_registro}."
            enviar_mensaje_whatsapp(telefono_tutor, mensaje_wa)
    except Exception as e:
        print(f"❌ Error en tarea asíncrona: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if request.cookies.get(COOKIE_NAME) == CLAVE_SECRETA:
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
            <p>Uso exclusivo para personal autorizado en la puerta del plantel.</p>
            <form method="post" action="/login">
                <input type="password" name="clave" placeholder="Contraseña de Prefectura" required>
                <button type="submit">Iniciar Escáner</button>
            </form>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_login)

@app.post("/login")
async def login(clave: str = Form(...)):
    if clave == CLAVE_SECRETA:
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key=COOKIE_NAME, value=CLAVE_SECRETA, max_age=28800)
        return response
    return HTMLResponse(content="<script>alert('Contraseña Incorrecta'); window.location='/';</script>")

@app.post("/registrar-asistencia")
async def registrar_asistencia(data: EntradaQR, request: Request, background_tasks: BackgroundTasks):
    if request.cookies.get(COOKIE_NAME) != CLAVE_SECRETA:
        return {"status": "error", "mensaje": "No autorizado."}

    texto = data.texto_qr
    key_match = re.search(r"[?&]key=([^&]+)", texto)
    
    if not key_match:
        return {"status": "error", "mensaje": "Código QR no válido. Formato no oficial."}
    
    key_alumno = key_match.group(1).strip()
    
    if key_alumno not in CACHE_TUTORES:
        # ¡NUEVO!: Intentamos el scraping en vivo antes de mandar el modal
        print(f"🔍 Buscando datos en portal institucional para Key: {key_alumno}")
        datos_extraidos = extraer_datos_cecytec(texto)
        
        return {
            "status": "nuevo_registro", 
            "key_qr": key_alumno,
            "url_completa": texto,
            "datos_scraped": datos_extraidos, # Retorna todo prellenado desde la web
            "mensaje": "Nueva credencial detectada."
        }
    
    datos_alumno = CACHE_TUTORES[key_alumno]
    num_control = datos_alumno["num_control"]
    alumno = datos_alumno["alumno"]
    telefono_tutor = datos_alumno["telefono_tutor"]
    status = datos_alumno["status"]
    
    if "BAJA" in status.upper() or "NO VIGENTE" in status.upper():
        return {"status": "alerta", "mensaje": f"ACCESO DENEGADO: {alumno} está de {status.upper()}."}
    
    ahora = datetime.now()
    fecha_registro = ahora.strftime("%Y-%m-%d")
    hora_registro = ahora.strftime("%I:%M %p")

    background_tasks.add_task(
        procesar_asistencia_en_segundo_plano,
        num_control, alumno, telefono_tutor, fecha_registro, hora_registro
    )
    return {"status": "exito", "mensaje": f"Procesando acceso para: {alumno}."}

@app.post("/dar-de-alta")
async def dar_de_alta(alumno_data: NuevoAlumno, request: Request):
    if request.cookies.get(COOKIE_NAME) != CLAVE_SECRETA:
        return {"status": "error", "mensaje": "No autorizado."}
    
    try:
        doc = conectar_sheets()
        pestaña_tutores = doc.worksheet("Directorio_Tutores")
        
        # Insertamos las 11 columnas completas en Google Sheets
        pestaña_tutores.append_row([
            alumno_data.num_control.strip(),
            alumno_data.alumno.strip().upper(),
            alumno_data.telefono_tutor.strip(),
            "ACTIVO",
            alumno_data.key_qr.strip(),
            alumno_data.url_credencial.strip(),
            alumno_data.curp.strip().upper(),
            alumno_data.especialidad.strip().upper(),
            alumno_data.semestre.strip().upper(),
            alumno_data.plantel.strip().upper(),
            alumno_data.imss.strip()
        ])
        
        actualizar_cache_tutores()
        return {"status": "exito", "mensaje": f"Perfil completo de {alumno_data.alumno} almacenado."}
    except Exception as e:
        return {"status": "error", "mensaje": f"Fallo al escribir en Sheets: {str(e)}"}
