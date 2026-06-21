import requests

# CONFIGURACIÓN DE LA API DE WHATSAPP (Auto-hospedada en Railway)
# Cuando montes el segundo contenedor, Railway te dará una URL interna
WHATSAPP_API_URL = "http://tu-servicio-whatsapp-interno.railway.internal/send-message"
WHATSAPP_TOKEN = "UnTokenSeguroCreadoPorTi"

def enviar_mensaje_whatsapp(telefono_tutor, mensaje):
    """
    Función encargada de comunicarse con el contenedor de Baileys/Waha
    para enviar el mensaje de texto al padre de familia de forma gratuita.
    """
    # Nos aseguramos de que el teléfono tenga el formato internacional básico (+52 para México)
    # Si en tu Google Sheets los guardas a 10 dígitos (ej: 8781234567), le pegamos el '52'
    if not telefono_tutor.startswith("52"):
        telefono_tutor = f"52{telefono_tutor}"
        
    payload = {
        "chatId": f"{telefono_tutor}@c.us", # Formato estándar que pide WhatsApp/Baileys
        "text": mensaje
    }
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        # Enviamos la petición al contenedor encargado de WhatsApp Web
        response = requests.post(WHATSAPP_API_URL, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            print(f"📩 WhatsApp enviado con éxito a {telefono_tutor}")
            return True
        else:
            print(f"⚠️ Error al enviar WhatsApp: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Fallo de conexión con el servicio de WhatsApp: {str(e)}")
        return False
