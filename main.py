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

# Montaje de estáticos con ruta absoluta para evitar 404
base_dir = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(base_dir, "static")), name="static")

templates = Jinja2Templates(directory="templates")

CLAVE_SECRETA = "Prefectura2026"
COOKIE_NAME = "sesion_prefecto"

# ... (Mantén aquí el resto de tus funciones: conectar_sheets, actualizar_cache, extraer_datos, etc.)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    sesion = request.cookies.get(COOKIE_NAME)
    if sesion == CLAVE_SECRETA:
       return templates.TemplateResponse(
    request=request, name="index.html", context={}
)
    # ... (Tu HTML de login aquí)
