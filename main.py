<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Control de Acceso - CECYTEC</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html5-qrcode/2.3.8/html5-qrcode.min.js" integrity="sha512-r6rDA7W6ZeQhvl8S7nEBzR7sUtSA9ghx4TgAVwpPq6cErmvEWmW9HBq7PR4fWkEDDHU4jM1EqWrcKraMv5shlg==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
    <style>
        :root {
            --primary: #00875a;
            --primary-dark: #006c48;
            --secondary: #2c3e50;
            --danger: #d32f2f;
            --warning: #f57c00;
            --bg: #f4f6f9;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg);
            margin: 0;
            padding: 0;
            color: var(--secondary);
        }

        header {
            background-color: var(--secondary);
            color: white;
            padding: 15px;
            text-align: center;
            font-weight: bold;
            font-size: 1.2rem;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }

        .container {
            max-width: 500px;
            margin: 20px auto;
            padding: 10px;
            box-sizing: border-box;
        }

        #reader {
            width: 100%;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            border: none !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }

        #status-card {
            background: white;
            margin-top: 20px;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            text-align: center;
            transition: all 0.3s ease;
        }

        .status-idle { border-left: 6px solid #ccc; }
        .status-success { border-left: 6px solid var(--primary); background-color: #ebf7f2; }
        .status-error { border-left: 6px solid var(--danger); background-color: #fdf2f2; }
        .status-warning { border-left: 6px solid var(--warning); background-color: #fffaf4; }

        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            overflow-y: auto;
            padding: 20px;
            box-sizing: border-box;
        }

        .modal-content {
            background: white;
            padding: 25px;
            border-radius: 12px;
            width: 100%;
            max-width: 450px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            max-height: 90vh;
            overflow-y: auto;
        }

        .modal-content h3 {
            margin-top: 0;
            color: var(--secondary);
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
        }

        .form-group {
            margin-bottom: 12px;
        }

        .form-group label {
            display: block;
            font-size: 0.85rem;
            font-weight: bold;
            margin-bottom: 4px;
            color: #555;
        }

        .form-group input {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ccc;
            border-radius: 6px;
            box-sizing: border-box;
            font-size: 14px;
        }

        .form-group input:focus {
            border-color: var(--primary);
            outline: none;
        }

        .btn-submit {
            width: 100%;
            padding: 12px;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            margin-top: 10px;
        }

        .btn-submit:hover { background: var(--primary-dark); }
        .btn-close {
            width: 100%;
            padding: 10px;
            background: #e0e0e0;
            color: #333;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            cursor: pointer;
            margin-top: 8px;
        }
    </style>
</head>
<body>

    <header>🛡️ CECYTEC — Control de Prefectura</header>

    <div class="container">
        <div id="reader"></div>

        <div id="status-card" class="status-idle">
            <h3 id="status-title" style="margin:0 0 5px 0;">Listo para escanear</h3>
            <p id="status-desc" style="margin:0; color:#666; font-size:14px;">Coloque el código QR de la credencial frente a la cámara.</p>
        </div>
    </div>

    <div id="registroModal" class="modal">
        <div class="modal-content">
            <h3>📝 Registro de Alumno Nuevo</h3>
            <p style="font-size: 13px; color: #666; margin-top: -10px; margin-bottom: 15px;">
                Se han recuperado datos automáticamente del portal institucional. Por favor, añada el teléfono del tutor.
            </p>
            <form id="formAlta" onsubmit="guardarNuevoAlumno(event)">
                <input type="hidden" id="modalKeyQr">
                <input type="hidden" id="modalUrlCredencial">

                <div class="form-group">
                    <label>Número de Control:</label>
                    <input type="text" id="modalNumControl" required readonly style="background: #f0f0f0;">
                </div>
                <div class="form-group">
                    <label>Nombre del Alumno:</label>
                    <input type="text" id="modalAlumno" required readonly style="background: #f0f0f0;">
                </div>
                <div class="form-group">
                    <label>CURP:</label>
                    <input type="text" id="modalCurp" readonly style="background: #f0f0f0;">
                </div>
                <div class="form-group">
                    <label>Especialidad / Carrera:</label>
                    <input type="text" id="modalEspecialidad" readonly style="background: #f0f0f0;">
                </div>
                <div class="form-group">
                    <label>Semestre Actual:</label>
                    <input type="text" id="modalSemestre" readonly style="background: #f0f0f0;">
                </div>
                <div class="form-group">
                    <label>Plantel:</label>
                    <input type="text" id="modalPlantel" readonly style="background: #f0f0f0;">
                </div>
                <div class="form-group">
                    <label>Número de Seguridad Social (IMSS):</label>
                    <input type="text" id="modalImss" readonly style="background: #f0f0f0;">
                </div>
                <div class="form-group" style="margin-top: 15px; border-top: 1px dashed #ccc; padding-top: 10px;">
                    <label style="color: var(--warning); font-size: 14px;">📞 Teléfono del Tutor (10 dígitos):</label>
                    <input type="tel" id="modalTelefono" placeholder="Ej: 8781234567" required pattern="[0-9]{10}" title="Deben ser exactamente 10 dígitos numéricos">
                </div>

                <button type="submit" class="btn-submit">Guardar Registro en Sheets</button>
                <button type="button" class="btn-close" onclick="cerrarModal()">Cancelar</button>
            </form>
        </div>
    </div>

    <script>
        let html5QrcodeScanner;
        let escanerBloqueado = false;

        function inicializarEscaner() {
            // Aseguramos que la librería exista antes de renderizar para prevenir bloqueos
            if (typeof Html5QrcodeScanner !== "undefined") {
                html5QrcodeScanner = new Html5QrcodeScanner(
                    "reader", 
                    { 
                        fps: 15, 
                        qrbox: { width: 250, height: 250 },
                        rememberLastUsedCamera: true,
                        supportedScanTypes: [Html5QrcodeScanType.SCAN_TYPE_CAMERA]
                    }
                );
                html5QrcodeScanner.render(onScanSuccess, onScanFailure);
            } else {
                console.error("La librería del escáner no cargó correctamente.");
                actualizarInterfaz("⚠️ Error de Inicialización", "Recargue la página para intentar reconectar.", "error");
            }
        }

        async function onScanSuccess(decodedText, decodedResult) {
            if (escanerBloqueado) return;
            
            escanerBloqueado = true;
            actualizarInterfaz("Ejecutando...", "Verificando código en el sistema...", "warning");

            try {
                const response = await fetch('/registrar-asistencia', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ texto_qr: decodedText })
                });
                
                const resultado = await response.json();

                if (resultado.status === "exito") {
                    actualizarInterfaz("✅ Acceso Registrado", resultado.mensaje, "success");
                    reproducirSonido(true);
                    setTimeout(() => { resetearInterfaz(); }, 3000);

                } else if (resultado.status === "alerta") {
                    actualizarInterfaz("🛑 Acceso Denegado", resultado.mensaje, "error");
                    reproducirSonido(false);
                    setTimeout(() => { resetearInterfaz(); }, 5000);

                } else if (resultado.status === "nuevo_registro") {
                    actualizarInterfaz("🔍 Nueva Credencial", "Abriendo formulario de alta...", "warning");
                    abrirModalAlta(resultado);

                } else {
                    actualizarInterfaz("⚠️ Error", resultado.mensaje, "error");
                    setTimeout(() => { resetearInterfaz(); }, 4000);
                }

            } catch (error) {
                actualizarInterfaz("❌ Error de Conexión", "No se pudo comunicar con el servidor local.", "error");
                setTimeout(() => { resetearInterfaz(); }, 4000);
            }
        }

        function onScanFailure(error) {
            // Rastreo silencioso de frames
        }

        function actualizarInterfaz(titulo, descripcion, clase) {
            const card = document.getElementById("status-card");
            const titleElem = document.getElementById("status-title");
            const descElem = document.getElementById("status-desc");

            if(card && titleElem && descElem) {
                card.className = ""; 
                card.classList.add(`status-${clase}`);
                titleElem.innerText = titulo;
                descElem.innerText = descripcion;
            }
        }

        function resetearInterfaz() {
            actualizarInterfaz("Listo para escanear", "Coloque el código QR de la credencial frente a la cámara.", "idle");
            escanerBloqueado = false;
        }

        function abrirModalAlta(datosPeticion) {
            document.getElementById("modalKeyQr").value = datosPeticion.key_qr;
            document.getElementById("modalUrlCredencial").value = datosPeticion.url_completa;
            
            const scraped = datosPeticion.datos_scraped;
            document.getElementById("modalNumControl").value = scraped.num_control || "";
            document.getElementById("modalAlumno").value = scraped.alumno || "";
            document.getElementById("modalCurp").value = scraped.curp || "";
            document.getElementById("modalEspecialidad").value = scraped.especialidad || "";
            document.getElementById("modalSemestre").value = scraped.semestre || "";
            document.getElementById("modalPlantel").value = scraped.plantel || "";
            document.getElementById("modalImss").value = scraped.imss || "";
            
            document.getElementById("modalTelefono").value = "";
            document.getElementById("registroModal").style.display = "flex";
        }

        function cerrarModal() {
            document.getElementById("registroModal").style.display = "none";
            resetearInterfaz();
        }

        async function guardarNuevoAlumno(event) {
            event.preventDefault();

            const payload = {
                key_qr: document.getElementById("modalKeyQr").value,
                url_credencial: document.getElementById("modalUrlCredencial").value,
                num_control: document.getElementById("modalNumControl").value,
                alumno: document.getElementById("modalAlumno").value,
                telefono_tutor: document.getElementById("modalTelefono").value,
                curp: document.getElementById("modalCurp").value,
                especialidad: document.getElementById("modalEspecialidad").value,
                semestre: document.getElementById("modalSemestre").value,
                plantel: document.getElementById("modalPlantel").value,
                imss: document.getElementById("modalImss").value
            };

            try {
                const response = await fetch('/dar-de-alta', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                const res = await response.json();
                if (res.status === "exito") {
                    alert("¡Alumno guardado con éxito! Ya puede pasar su credencial nuevamente para registrar asistencia.");
                    cerrarModal();
                } else {
                    alert("Error: " + res.mensaje);
                }
            } catch (err) {
                alert("Fallo de red al intentar conectar con el servidor.");
            }
        }

        function reproducirSonido(esExito) {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                
                osc.connect(gain);
                gain.connect(ctx.destination);

                if (esExito) {
                    osc.frequency.setValueAtTime(880, ctx.currentTime); 
                    gain.gain.setValueAtTime(0.1, ctx.currentTime);
                    osc.start();
                    osc.stop(ctx.currentTime + 0.15);
                } else {
                    osc.type = 'sawtooth';
                    osc.frequency.setValueAtTime(220, ctx.currentTime); 
                    gain.gain.setValueAtTime(0.1, ctx.currentTime);
                    osc.start();
                    osc.stop(ctx.currentTime + 0.4);
                }
            } catch (e) {
                console.log("AudioContext requiere interacción previa.");
            }
        }

        // Evento seguro: inicializa únicamente cuando toda la estructura HTML ha sido dibujada
        document.addEventListener("DOMContentLoaded", inicializarEscaner);
    </script>
</body>
</html>
