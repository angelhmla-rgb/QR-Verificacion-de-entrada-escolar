<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CECYTEC - Control de Acceso</title>
    <script src="https://unpkg.com/html5-qrcode"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f6f9;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .container {
            max-width: 500px;
            width: 100%;
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
        }
        h2 { color: #2c3e50; margin-bottom: 5px; }
        p { color: #7f8c8d; margin-top: 0; font-size: 14px; }
        #reader {
            width: 100%;
            border-radius: 8px;
            overflow: hidden;
            border: 2px solid #bdc3c7;
        }
        #resultado {
            margin-top: 20px;
            padding: 15px;
            border-radius: 8px;
            font-weight: bold;
            display: none;
        }
        .exito { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alerta { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    </style>
</head>
<body>

<div class="container">
    <h2>CECYTEC Norte</h2>
    <p>Escáner de Credenciales Oficiales</p>
    
    <div id="reader"></div>
    
    <div id="resultado"></div>
</div>

<script>
    function onScanSuccess(decodedText, decodedResult) {
        // Pausar el escáner momentáneamente para no procesar el mismo QR mil veces
        html5QrcodeScanner.clear();
        
        const resultadoDiv = document.getElementById('resultado');
        resultadoDiv.style.display = 'block';
        resultadoDiv.className = 'exito';
        resultadoDiv.innerText = "Procesando datos del alumno...";

        // Enviar el texto plano del QR al backend en Railway
        fetch('/registrar-asistencia', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ texto_qr: decodedText })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === "alerta") {
                resultadoDiv.className = 'alerta';
                resultadoDiv.innerText = "🚨 " + data.mensaje;
            } else if (data.status === "exito") {
                resultadoDiv.className = 'exito';
                resultadoDiv.innerText = "✅ " + data.mensaje;
            } else {
                resultadoDiv.className = 'alerta';
                resultadoDiv.innerText = "❌ " + data.mensaje;
            }
            // Reiniciar el escáner después de 3 segundos para el siguiente alumno
            setTimeout(inicializarEscaner, 3000);
        })
        .catch(error => {
            resultadoDiv.className = 'alerta';
            resultadoDiv.innerText = "Error de conexión con el servidor.";
            setTimeout(inicializarEscaner, 3000);
        });
    }

    function inicializarEscaner() {
        window.html5QrcodeScanner = new Html5QrcodeScanner("reader", { fps: 10, qrbox: 250 });
        html5QrcodeScanner.render(onScanSuccess);
    }

    // Arrancar la cámara al abrir la página
    inicializarEscaner();
</script>

</body>
</html>
