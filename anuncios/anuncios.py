import os
import random
import sqlite3
from datetime import datetime, timedelta
from telethon import TelegramClient, events, types
import asyncio
from config import API_ID, API_HASH, PHONE_NUMBER, DATABASE_FILE, OWNER_ID

# Definir el cliente antes de usarlo
client = TelegramClient('session_name', API_ID, API_HASH)

# Conexión a la base de datos
def conectar_db():
    return sqlite3.connect(DATABASE_FILE)

# Crear tablas si no existen
def crear_tablas():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anuncios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archivo TEXT NOT NULL,
            imagen TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS palabras_clave (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anuncio_id INTEGER,
            palabra_clave TEXT NOT NULL,
            FOREIGN KEY(anuncio_id) REFERENCES anuncios(id)
        )
    """)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grupos (
            grupo_id INTEGER PRIMARY KEY,
            categoria TEXT NOT NULL,
            tiempo_envio INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Función para agregar un anuncio con sus palabras clave
def agregar_anuncio(archivo, imagen=None, palabras_clave=None):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO anuncios (archivo, imagen) VALUES (?, ?)", (archivo, imagen))
    anuncio_id = cursor.lastrowid

    if palabras_clave:
        for palabra in palabras_clave:
            cursor.execute("INSERT INTO palabras_clave (anuncio_id, palabra_clave) VALUES (?, ?)", (anuncio_id, palabra))
    
    conn.commit()
    conn.close()

# Cargar anuncios y palabras clave desde la base de datos
def cargar_anuncios():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, archivo, imagen FROM anuncios")
    anuncios = {row[0]: {"archivo": row[1], "imagen": row[2]} for row in cursor.fetchall()}

    for anuncio_id in anuncios:
        cursor.execute("SELECT palabra_clave FROM palabras_clave WHERE anuncio_id=?", (anuncio_id,))
        anuncios[anuncio_id]["palabras_clave"] = [row[0] for row in cursor.fetchall()]

    conn.close()
    return anuncios

# Enviar un anuncio a un grupo (debe ser asincrónica)
async def enviar_anuncio(client, chat_id, mensaje, imagen=None):
    print(f"Preparando para enviar anuncio al grupo {chat_id}...")
    if imagen and os.path.exists(imagen):
        print(f"Enviando anuncio con imagen: {imagen} al grupo {chat_id}")
        await client.send_message(chat_id, file=imagen, message=mensaje)
    else:
        print(f"Enviando anuncio sin imagen al grupo {chat_id}")
        await client.send_message(chat_id, mensaje)
    print(f"Anuncio enviado al grupo {chat_id}")

# Manejar palabras clave y enviar anuncio correspondiente (debe ser asincrónica)
async def manejar_palabras_clave(event, anuncios, mensajes_respondidos, max_respuestas=5, intervalo_minutos=10):
    mensaje = event.message.message.lower()
    palabras_prohibidas = ["www", "http", "precio", "envío", "oferta", "contacto"]
    max_palabras = 10

    # Verificar si se ha alcanzado el límite de respuestas en el intervalo de tiempo
    ahora = datetime.now()
    mensajes_respondidos = [t for t in mensajes_respondidos if ahora - t < timedelta(minutes=intervalo_minutos)]
    if len(mensajes_respondidos) >= max_respuestas:
        print("Límite de respuestas alcanzado.")
        return False

    # Si el mensaje es muy largo, contiene enlaces, es un anuncio o es de un bot, no responder
    if (len(mensaje.split()) > max_palabras or 
        any(palabra in mensaje for palabra in palabras_prohibidas) or
        event.message.entities or
        event.message.media or
        event.sender is None or
        event.sender.bot):
        print("Condiciones para no responder cumplidas.")
        return False

    for anuncio_id, detalles in anuncios.items():
        for palabra in detalles["palabras_clave"]:
            if palabra in mensaje:
                with open(detalles["archivo"], 'r', encoding='utf-8') as file:
                    texto = file.read()
                print(f"Palabra clave '{palabra}' detectada. Enviando anuncio relacionado.")
                await enviar_anuncio(event.client, event.chat_id, texto, detalles.get("imagen"))
                mensajes_respondidos.append(ahora)
                return True  # Retorna True si se manejó alguna palabra clave

    print("No se manejó ninguna palabra clave.")
    return False  # Retorna False si no se manejó ninguna palabra clave

# Seleccionar un anuncio al azar y enviarlo a un grupo (debe ser asincrónica)
async def enviar_anuncio_aleatorio(client, chat_id, anuncios):
    anuncio_id = random.choice(list(anuncios.keys()))
    detalles = anuncios[anuncio_id]

    with open(detalles["archivo"], 'r', encoding='utf-8') as file:
        texto = file.read()
    print(f"Enviando anuncio aleatorio al grupo {chat_id}: {texto}")
    await enviar_anuncio(client, chat_id, texto, detalles.get("imagen"))

# Función para enviar anuncios periódicamente
async def enviar_anuncios_a_todos_los_grupos(client, anuncios):
    grupos_permitidos = obtener_grupos_por_categoria('todos') + obtener_grupos_por_categoria('diferente')
    grupos_excluidos = obtener_grupos_por_categoria('excluido')

    for grupo in grupos_permitidos:
        if grupo in grupos_excluidos:
            continue

        try:
            entity = await client.get_entity(grupo['id'])

            # Evitar enviar anuncios a canales, grupos privados o cerrados
            if isinstance(entity, types.Channel) and not entity.megagroup:
                print(f"Omitiendo {entity.title} (ID: {grupo['id']}), es un canal.")
                continue
            if isinstance(entity, types.Chat) and entity.left:
                print(f"Omitiendo {entity.title} (ID: {grupo['id']}), es un grupo privado.")
                continue

            nombre_grupo = entity.title if hasattr(entity, 'title') else str(grupo['id'])
            print(f"Enviando anuncio al grupo {nombre_grupo} (ID: {grupo['id']})")
            await enviar_anuncio_aleatorio(client, grupo['id'], anuncios)
        except Exception as e:
            print(f"Error al enviar anuncio al grupo {grupo['id']}: {str(e)}")
            await client.send_message(OWNER_ID, f"Error al enviar anuncio al grupo {grupo['id']}: {str(e)}")

        # Esperar el tiempo especificado para cada grupo antes de enviar al siguiente
        await asyncio.sleep(grupo['tiempo_envio'])

# Función para obtener grupos por categoría
def obtener_grupos_por_categoria(categoria):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT grupo_id, tiempo_envio FROM grupos WHERE categoria=?", (categoria,))
    grupos = [{"id": row[0], "tiempo_envio": row[1]} for row in cursor.fetchall()]
    conn.close()
    return grupos

# Crear las tablas si no existen
crear_tablas()

# Ejemplo de agregar un anuncio
agregar_anuncio(
    archivo="anuncios/anuncio1.txt", 
    imagen="anuncios/express.jpg", 
    palabras_clave=["quien vpn?", "vpn express"]
)
agregar_anuncio(
    archivo="anuncios/anuncio2.txt", 
    imagen="anuncios/agora.jpg", 
    palabras_clave=["agora", "quien agora", "agora pay"]
)

# Cargar los anuncios al iniciar
anuncios = cargar_anuncios()

# Lista para rastrear respuestas
mensajes_respondidos = []

# Función para manejar el inicio de anuncios periódicos y responder a comandos
@client.on(events.NewMessage(incoming=True, from_users=[OWNER_ID]))
async def comando_handler(event):
    if event.text == '/start':
        asyncio.create_task(enviar_anuncios_a_todos_los_grupos(client, anuncios))
        await event.respond("🚀 Spameo iniciado.")
    elif event.text == '/stop':
        for task in asyncio.all_tasks():
            if task.get_name() == "enviar_anuncios_a_todos_los_grupos":
                task.cancel()
        await event.respond("🛑 Spameo detenido.")

# Manejar palabras clave
@client.on(events.NewMessage(incoming=True))
async def manejador_evento(event):
    await manejar_palabras_clave(event, anuncios, mensajes_respondidos)

# Iniciar el bot
client.start(PHONE_NUMBER)
client.run_until_disconnected()
