# 3. El procesador de los códigos QR (Modificado para extraer la KEY del enlace oficial)
@app.post("/registrar-asistencia")
async def registrar_asistencia(data: EntradaQR, request: Request):
    if request.cookies.get(COOKIE_NAME) != CLAVE_SECRETA:
        return {"status": "error", "mensaje": "No autorizado para registrar asistencia."}

    texto = data.texto_qr
    
    # Extraemos el parámetro 'key=' que viene dentro de la URL del QR
    key_match = re.search(r"[?&]key=([^&]+)", texto)
    
    if not key_match:
        return {"status": "error", "mensaje": "Código QR no válido. No es una credencial oficial del CECYTEC."}
    
    key_alumno = key_match.group(1).strip()
    
    try:
        doc = conectar_sheets()
        pestaña_tutores = doc.worksheet("Directorio_Tutores")
        pestaña_asistencia = doc.worksheet("Asistencia_Diaria")
        
        # Buscamos la fila del alumno usando la clave única extraída del QR
        celda_alumno = pestaña_tutores.find(key_alumno)
        
        if not celda_alumno:
            return {"status": "error", "mensaje": "Credencial no registrada o alumno no encontrado en el Directorio."}
        
        fila_alumno = celda_alumno.row
        datos_alumno = pestaña_tutores.row_values(fila_alumno)
        
        # Estructura supuesta de Directorio_Tutores (Ajusta los índices según tus columnas):
        # Columna 1: Num_Control, Columna 2: Nombre, Columna 3: Tel_Tutor, Columna 4: Status, Columna 5: Key_QR
        # (Si tu columna Key_QR es la 5ta, gspread la encontrará y sabremos qué fila es)
        
        # Para este ejemplo, supongamos que extraemos los datos de las columnas conocidas de tu fila:
        num_control = datos_alumno[0] # Columna A
        alumno = datos_alumno[1]      # Columna B
        telefono_tutor = datos_alumno[2] # Columna C
        status = datos_alumno[3] if len(datos_alumno) >= 4 else "ACTIVO" # Columna D
        
        # Filtro de Seguridad de Alumnos Dados de Baja (Lógica local protegida)
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
        
        if telefono_tutor:
            saludo = "Buenos días" if "AM" in hora_registro else "Buenas tardes"
            mensaje_wa = f"📝 *CECYTEC Informa:*\n\n{saludo}, le notificamos que el alumno(a) *{alumno}* ha registrado su *{tipo_evento}* del plantel el día de hoy a las {hora_registro}."
            
            enviar_mensaje_whatsapp(telefono_tutor, mensaje_wa)
        
        return {
            "status": "exito",
            "mensaje": f"Acceso Registrado ({tipo_evento}): {alumno} a las {hora_registro}."
        }
        
    except Exception as e:
        return {"status": "error", "mensaje": f"Error al conectar con Google Sheets: {str(e)}"}
