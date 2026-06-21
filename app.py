import json
import os
import gspread
from google.oauth2.service_account import Credentials

# Conexión con Google Sheets usando las variables de entorno de Railway
def conectar_sheets():
    # En Railway crearemos una variable llamada GOOGLE_CREDS con el contenido del JSON
    creds_json = os.environ.get("GOOGLE_CREDS")
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    if creds_json:
        # Si estamos en Railway en producción
        info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(info, scopes=scope)
    else:
        # Por si haces pruebas locales en tu computadora con el archivo descargado
        creds = Credentials.from_service_account_file("credenciales.json", scopes=scope)
        
    client = gspread.authorize(creds)
    # Tu enlace exacto del documento de Google Sheets
    return client.open_by_url("https://docs.google.com/spreadsheets/d/193NV0p1OQsZAZy-f-gtOQZE743lh6yC6GgtlYzTHTkY/edit?usp=sharing")

@app.post("/registrar-asistencia")
async def registrar_asistencia(data: EntradaQR, request: Request):
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
        
        ahora = datetime.now()
        fecha_registro = ahora.strftime("%Y-%m-%d")
        hora_registro = ahora.strftime("%I:%M:%p")
        
        # Filtro de Seguridad de Alumnos Dados de Baja
        if "BAJA" in status.upper() or "NO VIGENTE" in status.upper():
            return {
                "status": "alerta",
                "mensaje": f"ACCESO DENEGADO: El alumno {alumno} tiene estatus de BAJA DEFINITIVA."
            }
        
        try:
            # Conectamos a la base de datos de Google Sheets
            doc = conectar_sheets()
            pestaña_tutores = doc.worksheet("Directorio_Tutores")
            pestaña_asistencia = doc.worksheet("Asistencia_Diaria")
            
            # Buscamos si el número de control existe en el directorio de tutores para validar datos
            celda_alumno = pestaña_tutores.find(num_control)
            
            if not celda_alumno:
                return {"status": "error", "mensaje": f"El número de control {num_control} no está registrado en el Directorio."}
            
            # Lógica inteligente: Revisamos si el alumno ya entró hoy para marcarlo como SALIDA, si no, es ENTRADA
            registros_hoy = pestaña_asistencia.get_all_values()
            tipo_evento = "ENTRADA"
            
            for fila in registros_hoy:
                # Si en las filas de hoy ya coincide la fecha actual y el ID del alumno
                if len(fila) >= 4 and fila[0].startswith(fecha_registro) and fila[1] == num_control:
                    if fila[3] == "ENTRADA":
                        tipo_evento = "SALIDA" # Si ya entró hoy, el siguiente escaneo cuenta como salida

            # Insertamos la nueva fila en la pestaña 'Asistencia_Diaria'
            pestaña_asistencia.append_row([
                f"{fecha_registro} {hora_registro}", 
                num_control, 
                alumno, 
                tipo_evento, 
                "Permitido"
            ])
            
            # Próximo Paso: Disparar la API de WhatsApp utilizando los datos de contacto encontrados
            # telefono_tutor = pestaña_tutores.cell(celda_alumno.row, 3).value
            
            return {
                "status": "exito",
                "mensaje": f"Acceso Registrado ({tipo_evento}): {alumno} a las {hora_registro}."
            }
            
        except Exception as e:
            return {"status": "error", "mensaje": f"Error al conectar con Google Sheets: {str(e)}"}
        
    return {"status": "error", "mensaje": "Código QR no válido o datos incompletos."}
