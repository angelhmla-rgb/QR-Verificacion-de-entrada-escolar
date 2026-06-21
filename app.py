import re
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Modelo de datos que espera recibir el servidor desde el celular
class EntradaQR(BaseModel):
    texto_qr: str

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Sirve la página web del escáner
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/registrar-asistencia")
async def registrar_asistencia(data: EntradaQR):
    texto = data.texto_qr
    
    # Expresiones regulares para segmentar los datos de las credenciales del CECYTEC
    nombre_match = re.search(r"NOMBRE DEL ALUMNO:\s*(.*)", texto)
    control_match = re.search(r"NUMERO DE CONTROL:\s*(\d+)", texto)
    status_match = re.search(r"STATUS:\s*(.*)", texto)
    
    if nombre_match and control_match:
        alumno = nombre_match.group(1).strip()
        num_control = control_match.group(1).strip()
        status = status_match.group(1).strip() if status_match else "ACTIVO"
        
        hora_actual = datetime.now().strftime("%I:%M %p")
        
        # 1. Filtro de Seguridad Duradero (Alumnos dados de baja)
        if "BAJA" in status.upper() or "NO VIGENTE" in status.upper():
            return {
                "status": "alerta",
                "mensaje": f"ACCESO DENEGADO: El alumno {alumno} tiene estatus de BAJA DEFINITIVA."
            }
        
        # 2. TODO: Aquí añadirás la conexión a Google Sheets para guardar la fila
        # registrar_en_sheets(num_control, alumno, hora_actual)
        
        # 3. TODO: Aquí añadirás el envío del mensaje de WhatsApp al tutor
        # enviar_whatsapp(num_control, f"Su hijo(a) {alumno} ingresó al plantel a las {hora_actual}")
        
        return {
            "status": "exito",
            "mensaje": f"Acceso Permitido: {alumno} registrado a las {hora_actual}."
        }
        
    return {"status": "error", "mensaje": "Código QR no válido o datos incompletos."}
