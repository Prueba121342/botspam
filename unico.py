import random
import time
import asyncio
import re
from telethon import TelegramClient, events
from telethon.errors import RPCError
from config import OWNER_ID

# Variable global para controlar el estado del manejador único
unico_activo = False

# Diccionario con las palabras clave
palabras_clave = {
    "quien dox?": "dox",
        "descanso": "disney",
    "medico": "perfil",

    "penales": "doxing",
    "alguien me saca info de un numero": "saca info",
    "dni virtual": "dni virtual",
    "c4": "c4",
    "quien c4?": "c4",
    "netflix": "netflix",
    "panel seguidores quien": "seguidores",
    "mpfn": "mpfn",
    "ficha de inscripción": "ficha de inscripción",
    "seguidores": "seguidores",
    "bot doxing": "bot doxing",
    "sbs": "sbs",
    "prime video": "prime video",
    "penal": "antecedente",
    "fiscal": "fiscal",
    "titular": "titular",
    "vpn express": "vpn express",
    "antecedentes": "antecedentes",
    "crunchyrroll": "crunchy",
    "sms": "sms",
    "ficha reniec": "ficha reniec",
    "ficha de inscripcón": "ficha de inscripción",
    "ficha de inscripcion": "ficha de inscripción",
    "arbol": "arbol",
    "migraciones": "migraciones",
    "info venezolanos": "info venezolanos",
    "sueldos": "sbs",
    "bot": "bot dox",
        "seguidores": "instagran",
            "canva": "pro",



}
# Constantes para el grupo específico
TIEMPO_ESPERA_CLAVE = 2  # 90 segundos entre notificaciones para la misma palabra clave por usuario

# Almacena el historial de notificaciones para evitar spam
historial_respuestas = {}

# Expresión regular para detectar emojis y palabras prohibidas
emoji_pattern = re.compile("[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]")
palabras_prohibidas = re.compile(
    r"vendo|quien quiere|gratis|ofrezco|interesado|promoción|compra|USA|me quedan|"
    r"venta|oferta|ganga|quien desea|adquiera|obtenga|dona|@|vendo spotify|gmail|hoy en dia|"
    r"nadie quiere|nord|lleve|desea|soles|so|bin|kuda|quiere|pidan|alguien quiere|"
    r"doxealo|doxeo|colombiano|con la misma|renovar",
    re.IGNORECASE
)

def manejar_sinonimos_y_variantes(mensaje, clave):
    """Maneja variantes de palabras clave permitiendo diferencias en acentos y espacios."""
    patron_clave = re.escape(clave).replace(r"\ ", r"\s*")
    patron_clave = re.sub(r'[aeiou]', r'[aeiouáéíóúü]', patron_clave, flags=re.IGNORECASE)
    regex_clave = re.compile(rf'\b{patron_clave}\b', re.IGNORECASE)
    return regex_clave.search(mensaje)

def contiene_emojis(mensaje):
    """Detecta si el mensaje contiene emojis."""
    return bool(emoji_pattern.search(mensaje))

def contiene_enlace(mensaje):
    """Detecta si el mensaje contiene enlaces."""
    enlace_pattern = re.compile(r'https?://t\.me/[\w_]+/\d+', re.IGNORECASE)
    return enlace_pattern.search(mensaje)

def es_valido_para_procesar(mensaje):
    """Valida si el mensaje es adecuado para ser procesado."""
    # No procesar mensajes con más de 10 palabras o que contengan emojis
    if len(mensaje.split()) > 10 or contiene_emojis(mensaje):
        return False
    # No procesar mensajes con palabras prohibidas o enlaces específicos
    if palabras_prohibidas.search(mensaje) or contiene_enlace(mensaje):
        return False
    return True

async def manejar_enlaces_telegram(event, mensaje):
    """Maneja mensajes que contienen enlaces a Telegram."""
    enlace_telegram_pattern = re.compile(r'https?://t\.me/[\w_]+/\d+', re.IGNORECASE)
    
    if enlace_telegram_pattern.search(mensaje):
        user_id = event.sender_id
        message_id = event.message.id
        chat_id = event.chat_id
        enlace_detectado = enlace_telegram_pattern.search(mensaje).group()

        # Obtener el @ del usuario (username)
        user = await event.client.get_entity(user_id)
        username = f"@{user.username}" if user.username else f"ID: {user_id}"

        # Generar notificación para el OWNER_ID con el enlace detectado
        notificacion = (
            f"**Enlace de Telegram detectado**\n"
            f"**Grupo ID:** {chat_id}\n"
            f"**Usuario:** {username}\n"
            f"**Enlace:** {enlace_detectado}\n"
            f"**Mensaje:** {mensaje}"
        )
        
        await event.client.send_message(OWNER_ID, notificacion)

async def manejar_mensaje_grupos(event):
    """Maneja los mensajes entrantes en los grupos y notifica al propietario si se detecta una palabra clave o enlace."""
    global unico_activo
    
    chat_id = event.chat_id
    user_id = event.sender_id
    mensaje = event.message.message.lower().strip()

    if not unico_activo:
        return  # Si el manejador no está activo, no hacer nada

    # Validar si el mensaje es procesable o contiene un enlace de Telegram
    if contiene_enlace(mensaje):
        await manejar_enlaces_telegram(event, mensaje)
        return

    if not es_valido_para_procesar(mensaje):
        return

    ahora = time.time()

    # Limita la frecuencia de notificaciones por usuario
    if user_id in historial_respuestas and ahora - historial_respuestas[user_id] < TIEMPO_ESPERA_CLAVE:
        return  # Si el usuario ha sido notificado recientemente, no hacer nada

    # Verificar si el mensaje contiene alguna palabra clave
    for clave, identificador in palabras_clave.items():
        if manejar_sinonimos_y_variantes(mensaje, clave):
            try:
                # Si encuentra una palabra clave, notificar al OWNER_ID
                await notificar_propietario(user_id, mensaje, event.message.id, chat_id, clave, event)
                historial_respuestas[user_id] = ahora
            except RPCError as e:
                print(f"Error de RPC: {str(e)}")
            break

async def notificar_propietario(user_id, mensaje, message_id, chat_id, clave, event):
    """Envía una notificación al OWNER con la información del mensaje que contiene una palabra clave."""
    try:
        # Obtiene el nombre de usuario del grupo
        grupo = await event.client.get_entity(chat_id)
        grupo_username = grupo.username if grupo.username else f"c/{abs(chat_id)}"
        
        # Genera el enlace al mensaje con el formato correcto
        enlace_mensaje = f"https://t.me/{grupo_username}/{message_id}"
        
        # Obtén el @ del usuario (username) usando event.client
        user = await event.client.get_entity(user_id)
        username = f"@{user.username}" if user.username else f"ID: {user_id}"
        
        # Crea el mensaje de notificación
        notificacion = (
            f"**Nuevo mensaje con palabra clave detectada**\n"
            f"**Grupo:** @{grupo_username}\n"
            f"**Usuario:** {username}\n"
            f"**Palabra clave:** {clave}\n"
            f"**Mensaje:** {mensaje}\n"
            f"**Enlace:** [Ver mensaje]({enlace_mensaje})"
        )
        
        # Envía la notificación al propietario (OWNER_ID)
        await event.client.send_message(OWNER_ID, notificacion)
    except RPCError as e:
        print(f"Error de RPC al intentar obtener el usuario o enviar mensaje: {str(e)}")

async def nuevo_mensaje_grupo(event):
    """Revisa si el mensaje viene de un grupo, si es así, llama al manejador."""
    if event.is_group:
        await manejar_mensaje_grupos(event)

def iniciar_manejador_unico(client):
    """Inicia el manejador de mensajes si no está activo."""
    global unico_activo
    if unico_activo:
        print("Manejador único ya está activo.")
        return
    
    unico_activo = True
    client.add_event_handler(nuevo_mensaje_grupo, events.NewMessage(incoming=True))
    print("Manejador único activado.")

def detener_manejador_unico():
    """Detiene el manejador de mensajes si está activo."""
    global unico_activo
    if not unico_activo:
        print("Manejador único ya está desactivado.")
        return
