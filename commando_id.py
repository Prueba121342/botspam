import os
from telethon import events
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import User, Channel, Chat, UserStatusOffline, UserStatusOnline, UserStatusRecently
from telethon.errors import ChannelPrivateError, UserPrivacyRestrictedError, UserBannedInChannelError, UserNotMutualContactError

# Función para obtener información de una entidad (usuario, grupo o canal)
async def obtener_info_entidad(event, client):
    try:
        # Determinar si el comando se ejecutó con una mención, nombre de usuario, enlace, o respuesta a un mensaje
        if event.reply_to_msg_id:
            reply_message = await event.get_reply_message()
            entity = await client.get_entity(reply_message.sender_id)
        elif len(event.message.text.split()) > 1:
            username_or_link = event.message.text.split()[1]
            entity = await client.get_entity(username_or_link)
        else:
            await event.respond("❌ **Error**: Debes proporcionar un nombre de usuario, enlace válido, o responder a un mensaje.")
            return
        
        response = "**Información de la entidad**\n\n"
        response += f"🔹 **ID**: `{entity.id}`\n"
        
        # Si es un grupo o canal
        if isinstance(entity, (Channel, Chat)):
            try:
                full_chat = await client(GetFullChannelRequest(entity))
                response += f"🔹 **Nombre**: `{entity.title}`\n"
                response += f"🔹 **Tipo**: `Grupo o Canal`\n"
                response += f"🔹 **Número de miembros**: `{full_chat.full_chat.participants_count}`\n"
                response += f"🔹 **Descripción**: `{full_chat.full_chat.about}`\n"
                photo_path = await client.download_profile_photo(entity, file=f"{entity.id}_profile_photo.jpg")
            except ChannelPrivateError:
                response += "🔹 **Error**: El canal o grupo es privado.\n"
                photo_path = None
            except Exception as e:
                response += f"🔹 **Error**: No se pudo obtener información adicional del canal/grupo. {str(e)}\n"
                photo_path = None
        
        # Si es un usuario
        elif isinstance(entity, User):
            try:
                full_user = await client(GetFullUserRequest(entity.id))
                
                about = getattr(full_user, 'about', 'No disponible')

                response += f"🔹 **Nombre**: `{entity.first_name} {entity.last_name or ''}`\n"
                response += f"🔹 **Usuario**: `@{entity.username or 'No disponible'}`\n"
                response += f"🔹 **Número de teléfono**: `{entity.phone or 'No disponible'}`\n"
                response += f"🔹 **Bio**: `{about}`\n"
                response += f"🔹 **Es bot**: `{entity.bot}`\n"
                response += f"🔹 **Es verificado**: `{entity.verified}`\n"
                response += f"🔹 **Es restringido**: `{entity.restricted}`\n"

                if isinstance(entity.status, UserStatusOnline):
                    response += f"🔹 **Última vez en línea**: `En línea ahora`\n"
                elif isinstance(entity.status, UserStatusOffline):
                    response += f"🔹 **Última vez en línea**: `{entity.status.was_online}`\n"
                elif isinstance(entity.status, UserStatusRecently):
                    response += f"🔹 **Última vez en línea**: `Recientemente en línea`\n"
                else:
                    response += f"🔹 **Última vez en línea**: `No disponible`\n"

                photo_path = await client.download_profile_photo(entity, file=f"{entity.id}_profile_photo.jpg")

            except UserNotMutualContactError:
                response += "🔹 **Error**: El usuario no es un contacto mutuo, no se puede obtener más información.\n"
                photo_path = None
            except UserPrivacyRestrictedError:
                response += "🔹 **Error**: El usuario tiene restricciones de privacidad, no se puede obtener más información.\n"
                photo_path = None
            except Exception as e:
                response += f"🔹 **Error**: No se pudo obtener información adicional. {str(e)}\n"
                photo_path = None

        else:
            response += "🔹 **Error**: La entidad no es un usuario, grupo o canal válido."
            photo_path = None

        # Enviar la foto de perfil junto con la tarjeta de información
        if photo_path:
            try:
                await client.send_file(event.chat_id, photo_path, caption=response)
                # Eliminar la foto después de enviarla
                os.remove(photo_path)
            except UserBannedInChannelError:
                await event.respond("⚠️ **Restricción**: No puedo enviar imágenes en este chat, pero aquí está la información disponible:")
                await event.respond(response)
            except Exception as e:
                await event.respond(f"❌ **Error** al enviar la imagen: {str(e)}")
        else:
            await event.respond(response)
    
    except IndexError:
        await event.respond("❌ **Error**: Por favor, proporciona un nombre de usuario, enlace válido, o responde a un mensaje.")
    except UserBannedInChannelError:
        await event.respond("⚠️ **Restricción**: No puedo enviar mensajes en este chat.")
    except Exception as e:
        await event.respond(f"❌ **Error**: Ocurrió un problema al obtener la información. {str(e)}")

# Registro de los manejadores de eventos
def iniciar_manejador_id(client, owner_id):
    @client.on(events.NewMessage(pattern='/id'))
    async def id_handler(event):
        # Verifica si el mensaje es en un chat privado y proviene del OWNER_ID
        if event.is_private and event.sender_id == owner_id:
            await obtener_info_entidad(event, client)
        else:
            await event.respond("❌ **Error**: No tienes permiso para usar este comando.")
