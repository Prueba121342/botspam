import random
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.types import ChannelParticipantsAdmins
from config import OWNER_ID
from manejador_grupos import obtener_todos_grupos
import asyncio

# Diccionario para rastrear la última vez que se respondió a un usuario
ultimo_mensaje = {}

# Diccionario con respuestas automáticas para mensajes privados basados en palabras clave
respuestas_privadas = {
    "ayuda": ["Hola! ¿En qué puedo ayudarte?", "Escríbeme los detalles y te ayudo con gusto."],
    "info": ["¿Qué tipo de información necesitas?", "Puedes consultarme sobre cualquier duda que tengas."],
    "precio": ["Los precios varían, ¿qué es lo que te interesa?", "Contáctame en privado para más detalles sobre precios @reigenpe."],
    "gracias": ["¡De nada!", "¡Siempre a tu servicio!"],
    "dox": ["Claro, ¿qué información necesitas? Escribe 'dosing' para ver la lista", "Soy el mejor para esto. Escribe 'dosing' para ver la lista."],
    "netflix": ["Claro, un perfil para un dispositivo cuesta 8 soles y un perfil para dos dispositivos cuesta 13 soles. Cuenta completa plan premium a 30", "Sí, tengo amigo, para un dispositivo cuesta 8 soles y para dos dispositivos cuesta 13 soles. Ten en cuenta que son perfiles."],
    "cuenta completa netflix": ["Claro amigo", "Sí, tengo."],
    "prime video": ["El perfil cuesta 6 soles", "Sí, tengo."],
    "servicios": ["🌟 *¡Servicios disponibles!* 🌟\n🎬 **Netflix Premium**\n🎥 **Prime Video**\n🕵️‍♂️ **Doxing**\n🤖 **Bot para Doxing**\n👍 **Seguidores, Likes, Vistas y Más**\n💥 **Bot para Spam**\n💻 **Programación Personalizada**\n📺 **YouTube Premium**\n💳 **Curso de Carding y Método Marathon**\n🎯 **Grupo de Fijas VIP y Grupo VIP**\n🔐 **Cuenta Completa Netflix**\n✨ *¡Contáctame para más información!* ✨"],
    "dosing": ["🔍 *Servicios de Información y Doxing* 🔍\n📄 **C4 Azul**\n📝 **Ficha de Inscripción**\n⚖️ **Antecedentes Judiciales, Penales y Policiales**\n🆔 **DNI Virtual (Ambas Caras)**\n📞 **Información de Números**\n🔍 **Búsqueda de Números por DNI**\n⚖️ **Casos MPFN**\n🏠 **Personas que Viven en un Hogar**\n🌳 **Árbol Genealógico**\n📸 **Fotos e Información de Personas**\n📲 **Titular de Números**\n🛠️ **Y Otros Servicios de Investigación**\n✨ *¡Consulta para más detalles!* ✨"]
}

# Función para verificar el estado del usuario en los grupos donde el bot está presente
async def verificar_usuario_en_grupos(client, user_id):
    grupos = obtener_todos_grupos()
    num_admin = 0
    num_no_admin = 0

    for grupo in grupos:
        try:
            # Obtener lista de administradores del grupo
            administradores = await client.get_participants(grupo["id"], filter=ChannelParticipantsAdmins)

            # Verificar si el usuario es administrador en el grupo
            es_admin = any(admin.id == user_id for admin in administradores)
            if es_admin:
                num_admin += 1
            else:
                num_no_admin += 1
        except Exception as e:
            print(f"No se pudo obtener información del grupo {grupo.get('name', 'Desconocido')}: {str(e)}")
            continue

    return num_admin, num_no_admin

# Función para enviar la notificación al owner
async def enviar_notificacion_al_owner(client, owner_id, mensaje, detalles_usuario, estado_resumen):
    notificacion = (
        f"📩 **Nuevo mensaje recibido** 📩\n\n"
        f"🔹 *Mensaje:* {mensaje}\n\n"
        f"🔹 *Detalles del usuario:* \n{detalles_usuario}\n\n"
        f"🔹 *Estado en los grupos:* \n{estado_resumen}"
    )
    try:
        await client.send_message(owner_id, notificacion)
    except Exception as e:
        print(f"Error al enviar la notificación al owner: {str(e)}")

# Función para manejar mensajes privados
async def manejar_mensaje_privado(event):
    user_id = event.sender_id
    mensaje = event.message.message.lower().strip()
    ahora = datetime.now()

    # Si el mensaje es del owner, no responder automáticamente
    if user_id == OWNER_ID:
        return

    # Verificar si han pasado al menos 8 minutos desde la última respuesta
    if user_id not in ultimo_mensaje or (ahora - ultimo_mensaje[user_id]) >= timedelta(minutes=8):
        # Actualizar el tiempo de la última respuesta
        ultimo_mensaje[user_id] = ahora

        # Agregar un retraso de 2 segundos antes de responder
        await asyncio.sleep(2)

        # Responder al usuario con el mensaje inicial
        await event.reply("Espero que tengas un buen día. Espera un momento que ahora @reigenpe te escribirá o escríbele directamente. Aquí están sus referencias: @RefsLegacy. ¿Qué se le ofrece o qué servicio desea? ")
        
        # Obtener detalles del usuario
        try:
            usuario = await event.client.get_entity(user_id)
            detalles_usuario = f"ID: {usuario.id}\nUsername: @{usuario.username if usuario.username else 'No disponible'}\nNombre: {usuario.first_name if usuario.first_name else 'No disponible'}\n"
        except Exception as e:
            detalles_usuario = f"No se pudo obtener detalles del usuario: {str(e)}"

        # Verificar estado del usuario en todos los grupos
        num_admin, num_no_admin = await verificar_usuario_en_grupos(event.client, user_id)
        estado_resumen = f"Es admin en {num_admin} grupo(s) y no es admin en {num_no_admin} grupo(s)."

        # Enviar notificación al owner
        await enviar_notificacion_al_owner(event.client, OWNER_ID, mensaje, detalles_usuario, estado_resumen)

       # Responder según palabras clave, incluso si ya se envió el mensaje predefinido
    for clave, respuestas in respuestas_privadas.items():
        if clave in mensaje:
            if clave == "pago":
                # Enviar el QR con el mensaje
                qr_file_path = "qr.png"  # Ruta donde está almacenada la imagen QR
                texto_adicional = "Escanea esto con tu billetera digital, verifica nombre y monta y paga."
                await event.reply(texto_adicional)
                await event.reply(file=qr_file_path)
            else:
                respuesta = random.choice(respuestas)
                await asyncio.sleep(3)  # Añadir un retraso de 3 segundos antes de responder
                await event.reply(respuesta)
            break

# Conectar el manejador al evento de mensajes privados
def iniciar_manejador_privado(client: TelegramClient):
    @client.on(events.NewMessage(incoming=True))
    async def nuevo_mensaje_privado(event):
        if event.is_private:
            await manejar_mensaje_privado(event)
