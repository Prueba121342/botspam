import asyncio
from telethon import TelegramClient, events, errors
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator
from config import OWNER_ID

# Límite de reintentos
MAX_REINTENTOS = 3

# Función para verificar si el bot está conectado
async def verificar_conexion(client):
    if not client.is_connected():
        try:
            print("Reconectando...")
            await client.connect()
        except Exception as e:
            print(f"Error al reconectar: {e}")
            return False
    return client.is_connected()

# Función para verificar si un usuario es administrador en un grupo
async def es_admin_en_grupo(client, user_id, group_id):
    try:
        if not await verificar_conexion(client):
            return "No Conectado"
        
        participante = await client(GetParticipantRequest(channel=group_id, user_id=user_id))
        if isinstance(participante.participant, (ChannelParticipantAdmin, ChannelParticipantCreator)):
            return True
        return False
    except errors.ChatAdminRequiredError:
        return "No Permisos"
    except Exception as e:
        print(f"Error al verificar si el usuario es administrador en el grupo {group_id}: {str(e)}")
        return "Error"

# Comando /info para contar los grupos donde el bot está presente
async def comando_info(client, event):
    if event.sender_id != OWNER_ID:
        return

    if not await verificar_conexion(client):
        await client.send_message(OWNER_ID, "El bot no está conectado. Intentando reconectar...")
        return

    count_groups = 0
    dialogs = await client.get_dialogs()

    # Contar el número de grupos donde el bot está presente
    for dialog in dialogs:
        if dialog.is_group:
            count_groups += 1

    mensaje = f"El bot está presente en {count_groups} grupo(s)."
    await client.send_message(OWNER_ID, mensaje)

# Comando /admins para listar los grupos donde el usuario es admin
async def comando_admins(client, event, user_id):
    if event.sender_id != OWNER_ID:
        return

    if not await verificar_conexion(client):
        await client.send_message(OWNER_ID, "El bot no está conectado. Intentando reconectar...")
        return

    grupos_admin = []
    dialogs = await client.get_dialogs()

    # Verificar si el usuario es administrador en los grupos
    for dialog in dialogs:
        if dialog.is_group:
            estado = await es_admin_en_grupo(client, user_id, dialog.id)
            if estado == True:
                grupos_admin.append(dialog.name)
    
    if grupos_admin:
        mensaje = (
            f"El usuario {user_id} es administrador en los siguientes grupos:\n\n" +
            "\n".join(grupos_admin)
        )
    else:
        mensaje = f"El usuario {user_id} no es administrador en ningún grupo."

    await client.send_message(OWNER_ID, mensaje)

# Función para manejar advertencias y generar informe
async def manejar_advertencia(client, event, tipo_advertencia, mensaje, usuario):
    if not await verificar_conexion(client):
        print("No se puede enviar advertencia, bot desconectado.")
        return

    grupo = event.chat.title if event.is_group else "Desconocido"
    advertencia = (
        f"⚠️ {tipo_advertencia} en el grupo: {grupo}\n"
        f"Usuario: {usuario.first_name} (@{usuario.username})\n"
        f"Mensaje: {mensaje}"
    )
    await client.send_message(OWNER_ID, advertencia)

# Función para manejar menciones y respuestas al bot o al owner
async def manejar_mencion_y_respuesta(event, reintentos=0):
    try:
        if event.is_group:
            if not await verificar_conexion(event.client):
                print("No se puede manejar menciones y respuestas, bot desconectado.")
                return

            # Obtener el usuario que envió el mensaje
            usuario = await event.get_sender()
            if not usuario:
                print(f"No se pudo obtener el usuario. Chat ID: {event.chat_id}, Message ID: {event.message.id}")
                return

            mensaje = event.message.message
            bot_id = await event.client.get_me()

            # Verificar si el bot ha sido mencionado
            if event.message.mentioned:
                if event.message.entities and (
                        OWNER_ID in [e.user_id for e in event.message.entities if hasattr(e, 'user_id')] or 
                        bot_id.id in [e.user_id for e in event.message.entities if hasattr(e, 'user_id')]):
                    await manejar_advertencia(event.client, event, "Mención", mensaje, usuario)

            # Verificar si es una respuesta al bot o al owner
            elif event.message.is_reply:
                original_message = await event.message.get_reply_message()
                if original_message and (original_message.sender_id == OWNER_ID or original_message.sender_id == bot_id.id):
                    await manejar_advertencia(event.client, event, "Respuesta", mensaje, usuario)

    except errors.FloodWaitError as e:
        if reintentos < MAX_REINTENTOS:
            print(f"FloodWaitError: Esperando {e.seconds} segundos antes de continuar. Reintento {reintentos + 1}/{MAX_REINTENTOS}")
            await asyncio.sleep(e.seconds)
            await manejar_mencion_y_respuesta(event, reintentos + 1)  # Reintentar después de esperar
        else:
            print("Se alcanzó el número máximo de reintentos debido a FloodWaitError. Ignorando este evento.")
    except Exception as e:
        print(f"Error inesperado en manejar_mencion_y_respuesta: {e}")

# Función para manejar muteo o baneo del bot en un grupo
async def manejar_muteo_baneo(event, reintentos=0):
    try:
        if event.user_added == 'me' or event.user_kicked == 'me':
            if not await verificar_conexion(event.client):
                print("No se puede manejar muteo o baneo, bot desconectado.")
                return

            usuario = await event.get_sender()
            if not usuario:
                print(f"No se pudo obtener el usuario. Chat ID: {event.chat_id}, Message ID: {event.message.id}")
                return

            if event.user_kicked == 'me':
                await manejar_advertencia(event.client, event, "Baneo", "El bot ha sido expulsado", usuario)
            elif event.user_muted == 'me':
                await manejar_advertencia(event.client, event, "Muteo", "El bot ha sido silenciado", usuario)

    except errors.FloodWaitError as e:
        if reintentos < MAX_REINTENTOS:
            print(f"FloodWaitError: Esperando {e.seconds} segundos antes de continuar. Reintento {reintentos + 1}/{MAX_REINTENTOS}")
            await asyncio.sleep(e.seconds)
            await manejar_muteo_baneo(event, reintentos + 1)  # Reintentar después de esperar
        else:
            print("Se alcanzó el número máximo de reintentos debido a FloodWaitError. Ignorando este evento.")
    except Exception as e:
        print(f"Error inesperado en manejar_muteo_baneo: {e}")

# Función principal para manejar comandos y eventos
async def manejar_comando(event):
    if event.is_private and event.sender_id == OWNER_ID:
        mensaje = event.message.message
        if mensaje.startswith('/info'):
            await comando_info(event.client, event)
        elif mensaje.startswith('/admins'):
            partes = mensaje.split(' ', 1)
            if len(partes) > 1:
                user = partes[1].strip()
                await comando_admins(event.client, event, user)
            else:
                await event.client.send_message(OWNER_ID, "Uso incorrecto del comando /admins. Formato: /admins <user_id>")
    
    # Manejar menciones y respuestas
    await manejar_mencion_y_respuesta(event)

# Función para iniciar los manejadores de eventos
def iniciar_manejador_antiban(client: TelegramClient):
    @client.on(events.NewMessage(incoming=True))
    async def mensaje_handler(event):
        await manejar_comando(event)

    @client.on(events.ChatAction)
    async def action_handler(event):
        await manejar_muteo_baneo(event)
