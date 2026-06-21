# 3. El procesador de los códigos QR (Con retorno de depuración de texto)
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
        hora_registro = ahora.strftime("%I:%M %p")
        
        # Filtro de Seguridad de Alumnos Dados de Baja
        if "BAJA" in status.upper() or "NO VIGENTE" in status.upper():
            return {
                "status": "alerta",
                "mensaje": f"ACCESO DENEGADO: El alumno {alumno} tiene estatus de BAJA DEFINITIVA."
            }
        
        try:
            doc = conectar_sheets()
            pestaña_tutores = doc.worksheet("Directorio_Tutores")
            pestaña_asistencia = doc.worksheet("Asistencia_Diaria")
            
            celda_alumno = pestaña_tutores.find(num_control)
            
            if not celda_alumno:
                return {"status": "error", "mensaje": f"El número de control {num_control} no está registrado en el Directorio."}
            
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
            
            fila_alumno = celda_alumno.row
            telefono_tutor = pestaña_tutores.cell(fila_alumno, 3).value
            
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
        
    return {"status": "error", "mensaje": f"Texto detectado en el QR: {texto}"}
