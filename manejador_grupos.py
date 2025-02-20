import sqlite3
from config import DATABASE_FILE

# Conexión a la base de datos
def conectar_db():
    return sqlite3.connect(DATABASE_FILE)

# Función para inicializar la base de datos y crear la tabla 'grupos'
def inicializar_db():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grupos (
            grupo_id INTEGER PRIMARY KEY,
            categoria TEXT NOT NULL,
            tiempo_envio INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Función para agregar o actualizar un grupo en la base de datos
def agregar_grupo(grupo_id, categoria, tiempo_envio=300):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO grupos (grupo_id, categoria, tiempo_envio) VALUES (?, ?, ?)", 
                   (grupo_id, categoria, tiempo_envio))
    conn.commit()
    conn.close()

# Función para obtener grupos por categoría
def obtener_grupos_por_categoria(categoria):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT grupo_id FROM grupos WHERE categoria=?", (categoria,))
    grupos = [{"id": row[0]} for row in cursor.fetchall()]
    conn.close()
    return grupos

# Función para obtener todos los grupos
def obtener_todos_grupos():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT grupo_id, categoria, tiempo_envio FROM grupos")
    grupos = [{"id": row[0], "categoria": row[1], "tiempo_envio": row[2]} for row in cursor.fetchall()]
    conn.close()
    return grupos

# Inicializar la base de datos
inicializar_db()

# Ejemplo de uso: Añadir un grupo a la categoría 'excluido'
grupo_id_excluido = -1910504915  # Reemplaza con el ID real del grupo
agregar_grupo(grupo_id_excluido, 'excluido')

# Ejemplo de uso: Añadir un grupo a la categoría 'diferente'
grupo_id_diferente = -1724620371  # Reemplaza con el ID real del grupo
agregar_grupo(grupo_id_diferente, 'diferente', tiempo_envio=480)  # Puedes especificar un tiempo de envío diferente

# Verificar los grupos añadidos
grupos_excluidos = obtener_grupos_por_categoria('excluido')
print(f"Grupos en la categoría 'excluido': {grupos_excluidos}")

grupos_diferentes = obtener_grupos_por_categoria('diferente')
print(f"Grupos en la categoría 'diferente': {grupos_diferentes}")

# Obtener y mostrar todos los grupos
todos_los_grupos = obtener_todos_grupos()
print(f"Todos los grupos: {todos_los_grupos}")
