import re
from datetime import datetime

# Simulación del texto que recibes al escanear el QR del CECYTEC
texto_escaneado = """
TIPO DE DOCUMENTO: CREDENCIAL OFICIAL CECYTEC - COAHUILA
NOMBRE DEL PLANTEL: CECYTEC - PIEDRAS NEGRAS NORTE
NOMBRE DEL ALUMNO: RICARDO IRACHETA OROZCO
NUMERO DE CONTROL: 22405070376354
STATUS: BAJA DEFINITIVA
VIGENCIA: NO VIGENTE
"""

def procesar_entrada_alumno(texto):
    # Usamos expresiones regulares para extraer los datos importantes de la credencial
    nombre_match = re.search(r"NOMBRE DEL ALUMNO:\s*(.*)", texto)
    control_match = re.search(r"NUMERO DE CONTROL:\s*(\d+)", texto)
    status_match = re.search(r"STATUS:\s*(.*)", texto)
    
    if nombre_match and control_match:
        alumno = nombre_match.group(1).strip()
        num_control = control_match.group(1).strip()
        status = status_match.group(1).strip() if status_match else "ACTIVO"
        
        # Obtenemos la fecha y hora actual de la entrada/salida
        hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Filtro de seguridad por Status
        if "BAJA" in status or "NO VIGENTE" in status:
            return f"🚨 ALERTA: El alumno {alumno} (Control: {num_control}) cuenta con BAJA DEFINITIVA. Acceso denegado."
        
        # Aquí conectarías tu lógica para registrar en base de datos o Google Sheets
        # Ejemplo: guardar_registro(num_control, alumno, hora_actual)
        
        # Aquí conectarías tu API de WhatsApp para mandar el mensaje al papá
        # Ejemplo: enviar_whatsapp_tutor(num_control, f"{alumno} entró a la escuela a las {hora_actual}")
        
        return f"✅ Registro Exitoso: {alumno} - Ingreso a las {hora_actual}"
    
    return "❌ Error: Código QR no reconocido o dañado."

# Prueba del script
resultado = procesar_entrada_alumno(texto_escaneado)
print(resultado)
