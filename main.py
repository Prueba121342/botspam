import asyncio
from telethon import TelegramClient, events, errors
from config import API_ID, API_HASH, PHONE_NUMBER, OWNER_ID

# Importar el módulo de anuncio
from anuncio import cargar_anuncios_json, enviar_anuncios_a_todos_los_grupos

# Importar los manejadores personalizados
from unico import iniciar_manejador_unico, detener_manejador_unico
from antiban import iniciar_manejador_antiban
from respuestas import iniciar_manejador_privado
from commando_id import iniciar_manejador_id

# Definir el cliente antes de usarlo
client = TelegramClient('session_name', API_ID, API_HASH)

# Variables globales para controlar el estado del bot
bot_activo = False
unico_activo = False
tasks = {}

# Cargar los anuncios desde el archivo JSON al iniciar
anuncios = cargar_anuncios_json('anuncio.json')

# Función para manejar el inicio de anuncios periódicos y responder a comandos
@client.on(events.NewMessage(incoming=True, from_users=[OWNER_ID]))
async def comando_handler(event):
    global bot_activo, unico_activo

    if event.text == '/start':
        if not bot_activo:
            bot_activo = True
            # Verificar si una tarea está en ejecución y agregar un retraso de 1 segundo
            if any(task for task in tasks.values() if not task.done()):
                await asyncio.sleep(1)  # Retraso de 1 segundo si hay una tarea en ejecución
            tasks['spameo'] = asyncio.create_task(enviar_anuncios_a_todos_los_grupos(client, anuncios, bot_activo, OWNER_ID))
            await event.respond("🚀 Spameo iniciado.")
        else:
            await event.respond("El bot ya está activo.")
    
    elif event.text == '/stop':
        if bot_activo:
            bot_activo = False
            if 'spameo' in tasks and not tasks['spameo'].done():
                tasks['spameo'].cancel()
                try:
                    await tasks['spameo']  # Asegurar que la tarea cancelada finalice correctamente
                except asyncio.CancelledError:
                    print("La tarea de spameo ha sido cancelada correctamente.")
            await event.respond("🛑 Spameo detenido.")
        else:
            await event.respond("El bot ya está detenido.")

    elif event.text == '/startunico':
        if not unico_activo:
            unico_activo = True
            # Verificar si una tarea está en ejecución y agregar un retraso de 1 segundo
            if any(task for task in tasks.values() if not task.done()):
                await asyncio.sleep(1)  # Retraso de 1 segundo si hay una tarea en ejecución
            iniciar_manejador_unico(client)
            await event.respond("🚀 Manejador único iniciado.")
        else:
            await event.respond("El manejador único ya está activo.")
    
    elif event.text == '/stopunico':
        if unico_activo:
            unico_activo = False
            detener_manejador_unico(client)
            await event.respond("🛑 Manejador único detenido.")
        else:
            await event.respond("El manejador único ya está detenido.")

# Iniciar los otros manejadores personalizados
iniciar_manejador_antiban(client)  # Maneja eventos relacionados con baneos y permisos
iniciar_manejador_privado(client)  # Maneja mensajes privados
iniciar_manejador_id(client, OWNER_ID)  # Maneja comandos relacionados con ID

# Función principal para iniciar el bot y manejar errores globales
async def iniciar_bot():
    retries = 0  # Contador de reintentos
    max_retries = 10  # Máximo número de reintentos
    backoff_factor = 2  # Factor de crecimiento exponencial

    while retries < max_retries:
        try:
            # Iniciar el bot
            await client.start(PHONE_NUMBER)
            print("Bot iniciado correctamente.")
            await client.run_until_disconnected()
        except errors.FloodWaitError as e:
            print(f"FloodWaitError: Esperando {e.seconds} segundos antes de continuar...")
            await asyncio.sleep(e.seconds)
        except errors.InvalidBufferError as e:
            retries += 1
            wait_time = min(60, backoff_factor ** retries)
            print(f"InvalidBufferError (429): Esperando {wait_time} segundos antes de reintentar... (Reintento {retries}/{max_retries})")
            await asyncio.sleep(wait_time)
        except Exception as e:
            print(f"Error inesperado: {e}. Reiniciando bot en 5 segundos...")
            await asyncio.sleep(5)
        else:
            # Resetear el contador de reintentos si el ciclo se completó sin errores
            retries = 0

    print("Se alcanzó el número máximo de reintentos. Deteniendo bot.")

if __name__ == "__main__":
    asyncio.run(iniciar_bot())
