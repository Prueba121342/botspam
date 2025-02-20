import os
import json
import random
from telethon import errors
import asyncio

# Función para cargar los anuncios desde el archivo JSON
def cargar_anuncios_json(json_file):
    with open(json_file, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data['anuncios']

# Enviar un anuncio a un grupo (debe ser asincrónica)
async def enviar_anuncio(client, chat_id, grupo_name, anuncio, intentos=3):
    for intento in range(intentos):
        try:
            # Verificar si el cliente está conectado y reconectar si es necesario
            if not client.is_connected():
                print(f"Cliente desconectado. Intentando reconectar...")
                await client.connect()

            if 'imagen' in anuncio and os.path.exists(anuncio['imagen']):
                try:
                    # Intentar enviar la imagen con el texto
                    await client.send_message(chat_id, file=anuncio['imagen'], message=anuncio['texto'])
                except (errors.ChatSendMediaForbiddenError, errors.RPCError) as e:
                    if "CHAT_SEND_PHOTOS_FORBIDDEN" in str(e):
                        print(f"No se puede enviar fotos en el grupo {grupo_name} (ID: {chat_id}). Enviando solo texto.")
                        # Enviar solo el texto si no se permite enviar imágenes
                        await client.send_message(chat_id, anuncio['texto'])
                    else:
                        raise  # Re-lanzar la excepción si no es el error de permisos para enviar imágenes
            else:
                # Enviar solo texto si no hay imagen o el archivo de imagen no existe
                await client.send_message(chat_id, anuncio['texto'])

            print(f"Enviado a {grupo_name} (ID: {chat_id}) - {anuncio['texto'][:50]}...")
            return True  # Retornar True si se envió con éxito

        except errors.FloodWaitError as e:
            if intento < intentos - 1:
                print(f"Esperando {e.seconds} segundos debido a restricciones de Telegram. Reintento {intento + 1}/{intentos}")
                await asyncio.sleep(e.seconds)
            else:
                print(f"Máximo de intentos alcanzado para {grupo_name} (ID: {chat_id}). Saltando al siguiente grupo.")
                return False  # Retornar False si se agotaron los intentos

        except errors.UserBannedInChannelError:
            print(f"El bot está baneado en el grupo {grupo_name} (ID: {chat_id}). Saltando al siguiente grupo.")
            return False

        except errors.ChatWriteForbiddenError:
            print(f"No tiene permiso para escribir en el grupo {grupo_name} (ID: {chat_id}). Saltando al siguiente grupo.")
            return False

        except Exception as e:
            print(f"Error al enviar anuncio al grupo {grupo_name} (ID: {chat_id}): {str(e)}")
            return False

# Función para enviar anuncios a todos los grupos, esperar un intervalo y repetir
async def enviar_anuncios_a_todos_los_grupos(client, anuncios, bot_activo, owner_id):
    while bot_activo:
        grupos = await client.get_dialogs()  # Obtener todos los chats
        enviados = 0
        no_enviados = 0
        no_permitidos = 0

        for grupo in grupos:
            if not bot_activo:
                break  # Detener el envío si el bot está desactivado

            if grupo.is_group:
                try:
                    anuncio = random.choice(anuncios)  # Seleccionar un anuncio al azar
                    enviado = await enviar_anuncio(client, grupo.id, grupo.title, anuncio)
                    if enviado:
                        enviados += 1
                    else:
                        no_enviados += 1
                except Exception as e:
                    no_enviados += 1
                    print(f"Error en el grupo {grupo.title} (ID: {grupo.id}): {str(e)}")

                # Esperar entre 50 a 120 segundos antes de enviar al siguiente grupo
                espera_aleatoria = random.randint(10, 60)
                print(f"Esperando {espera_aleatoria} segundos antes de enviar al siguiente grupo...")
                await asyncio.sleep(espera_aleatoria)
        
        # Enviar resumen al owner
        mensaje_resumen = (
            f"📢 **Resumen de envíos de anuncios** 📢\n\n"
            f"✅ Anuncios enviados exitosamente: {enviados} grupos\n"
            f"❌ No se pudo enviar a: {no_enviados} grupos\n"
            f"🚫 No permitido para enviar: {no_permitidos} grupos\n"
            f"🎯 Total de grupos procesados: {enviados + no_enviados + no_permitidos}\n"
        )
        await client.send_message(owner_id, mensaje_resumen)

        # Esperar 10 minutos antes de comenzar el siguiente ciclo
        print("Esperando 3 minutos con 20 segundos antes de comenzar el siguiente ciclo de envío...")
        await asyncio.sleep(200)  # 10 minutos

# Ejemplo de uso
async def main():
    # Asume que 'client' es una instancia de TelegramClient ya inicializada
    client = ...  # Inicializar el cliente de Telethon
    json_file = 'anuncios.json'
    anuncios = cargar_anuncios_json(json_file)
    bot_activo = True  # Condición para mantener el bot activo
    owner_id = 6799147188  # Reemplazar con el ID del propietario del bot

    # Iniciar el envío de anuncios
    await enviar_anuncios_a_todos_los_grupos(client, anuncios, bot_activo, owner_id)

# Ejecutar el script
if __name__ == "__main__":
    asyncio.run(main())
