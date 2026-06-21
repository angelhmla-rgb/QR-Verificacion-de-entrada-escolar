import re
from datetime import datetime
from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# CONFIGURACIÓN DE SEGURIDAD
CLAVE_SECRETA = "Prefectura2026"  # Puedes cambiar esta contraseña por la que gustes
COOKIE_NAME = "sesion_prefecto"

class EntradaQR(BaseModel):
    texto_qr: str

# 1. Pantalla de inicio de sesión / Filtro de seguridad
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Verificar si el celular ya tiene la cookie de acceso autorizada
    sesion = request.cookies.get(COOKIE_NAME)
    if sesion == CLAVE_SECRETA:
        return templates.TemplateResponse("index.html", {"request": request})
    
    # Si no está autorizado, se muestra la pantalla bonita de bloqueo
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
            .error { color: #c0392b; font-size: 14px; margin-top: 10px; }
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

# 2. Procesar la contraseña ingresada
@app.post("/login")
async def login(clave: str = Form(...)):
    if clave == CLAVE_SECRETA:
        response = RedirectResponse(url="/", status_code=303)
        # Guardamos la cookie para que el celular no pida la clave a cada rato
        response.set_cookie(key=COOKIE_NAME, value=CLAVE_SECRETA, max_age=28800) # Expira en 8 horas (un turno escolar)
        return response
    
    # Si la clave es incorrecta, redirige de nuevo con una alerta simple
    return HTMLResponse(content="<script>alert('Contraseña Incorrecta'); window.location='/';</script>")

# 3. El procesador de los códigos QR (Solo responde si viene del escáner autorizado)
@app.post("/registrar-asistencia")
async def registrar_asistencia(data: EntradaQR, request: Request):
    # Doble validación: asegurar que la petición post tiene la cookie correcta
    if request.cookies.get(COOKIE_NAME) != CLAVE_SECRETA:
        return {"status": "error", "mensaje": "No autorizado para registrar asistencia."}

    texto = data.texto_qr
    nombre_match = re.search(r"NOMBRE DEL ALUMNO:\s*(.*)", texto)
    control_match = re.search(r"NUMERO DE CONTROL:\s*(\d+)", texto)
    status_match = re.search(r"STATUS:\s*(.*)", texto)
    
    if nombre_match and control_match:
        alumno = nombre_match.group(1).strip()
        num_control = control_match.group(1).strip()
        status = status_match.group(1).strip() if status_match else "ACTIVO"
        
        hora_actual = datetime.now().strftime("%I:%M %p")
        
        # Filtro de Seguridad de Alumnos Dados de Baja
        if "BAJA" in status.upper() or "NO VIGENTE" in status.upper():
            return {
                "status": "alerta",
                "mensaje": f"ACCESO DENEGADO: El alumno {alumno} tiene estatus de BAJA DEFINITIVA."
            }
        
        # Próximos pasos: Google Sheets y WhatsApp
        return {
            "status": "exito",
            "mensaje": f"Acceso Permitido: {alumno} registrado a las {hora_actual}."
        }
        
    return {"status": "error", "mensaje": "Código QR no válido o datos incompletos."}
