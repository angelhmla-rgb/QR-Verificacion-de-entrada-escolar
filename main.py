import re
import json
import os
import gspread
import requests
from datetime import datetime
from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google.oauth2.service_account import Credentials
from bs4 import BeautifulSoup

app = FastAPI()

# 1. Montaje de estáticos con ruta absoluta para evitar 404
base_dir = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(base_dir, "static")), name="static")

templates = Jinja2Templates(directory="templates")

# Configuración
CLAVE_SECRETA = "Prefectura2026"
COOKIE_NAME = "sesion_prefecto"

class EntradaQR(BaseModel):
    texto_qr: str

# --- MANTÉN AQUÍ TUS FUNCIONES EXISTENTES (conectar_sheets, actualizar_cache, etc.) ---
# ... (asegúrate de que no tengan espacios invisibles al pegar) ...

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    sesion = request.cookies.get(COOKIE_NAME)
    if sesion == CLAVE_SECRETA:
        # CORRECCIÓN: Usamos la nueva sintaxis para evitar el error de dict
        return templates.TemplateResponse(request=request, name="index.html", context={})
    
    # Aquí iría tu lógica de login (formulario inicial)
    return HTMLResponse("<h1>Página de Login</h1>")

@app.post("/registrar-asistencia")
async def registrar_asistencia(data: EntradaQR, request: Request, background_tasks: BackgroundTasks):
    # Verificación de seguridad
    if request.cookies.get(COOKIE_NAME) != CLAVE_SECRETA:
        return {"status": "error", "mensaje": "No autorizado."}
    
    # Lógica de procesamiento de asistencia
    # ... (tu lógica aquí) ...
    return {"status": "exito", "mensaje": "Asistencia registrada correctamente"}

# Función de diagnóstico para descartar errores de rutas
@app.get("/debug-routes")
async def debug_routes():
    return {"rutas": [route.path for route in app.routes]}
