# api/index.py

import json
import os
from http.server import BaseHTTPRequestHandler
from urllib import parse
import psycopg2
from vercel_blob import list_blobs, put_blob, get_blob_by_url

# --- Configuración de Vercel Postgres ---
# Vercel automáticamente inyecta la URL de Postgres como una variable de entorno
POSTGRES_URL = os.environ.get('POSTGRES_URL')

def get_db_connection():
    """Establece y retorna una conexión a la base de datos PostgreSQL."""
    if not POSTGRES_URL:
        raise ValueError("La variable de entorno POSTGRES_URL no está configurada.")
    return psycopg2.connect(POSTGRES_URL)

def init_db():
    """Inicializa la tabla 'messages' si no existe y un mensaje por defecto."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL
            );
        """)
        # Insertar un mensaje por defecto si la tabla está vacía
        cur.execute("INSERT INTO messages (content) SELECT '¡Hola desde Postgres!' WHERE NOT EXISTS (SELECT 1 FROM messages);")
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"Error al inicializar la base de datos: {e}")
        # En un entorno de producción, podrías querer registrar esto o notificar.
    finally:
        if conn:
            conn.close()

# Llamar a init_db una vez al inicio del runtime para asegurar que la tabla existe.
# En un entorno serverless, esto puede ejecutarse cada vez que una instancia de la función se "calienta".
init_db()

# --- Clase Handler para la API ---
class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        """
        Maneja las solicitudes GET.
        Recupera un mensaje de Postgres y lista/lee un blob.
        """
        response_data = {}
        
        # --- Interacción con Vercel Postgres ---
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT content FROM messages ORDER BY id ASC LIMIT 1;")
            message_from_db = cur.fetchone()
            if message_from_db:
                response_data['postgres_message'] = message_from_db[0]
            else:
                response_data['postgres_message'] = "No hay mensajes en Postgres."
            cur.close()
        except Exception as e:
            response_data['postgres_error'] = f"Error al leer de Postgres: {e}"
        finally:
            if conn:
                conn.close()

        # --- Interacción con Vercel Blob ---
        try:
            # Lista los blobs en tu almacenamiento
            list_result = list_blobs()
            response_data['blob_files'] = [blob['pathname'] for blob in list_result['blobs']]

            # Intenta leer un blob específico si existe
            target_blob_name = "mi_texto_simple.txt"
            blob_found_url = next((b['url'] for b in list_result['blobs'] if b['pathname'] == target_blob_name), None)

            if blob_found_url:
                blob_content_obj = get_blob_by_url(blob_found_url)
                # get_blob_by_url devuelve un objeto respuesta, necesitamos leer su texto
                response_data['blob_content'] = blob_content_obj.text
            else:
                response_data['blob_content'] = f"Blob '{target_blob_name}' no encontrado. Intenta hacer un POST."

        except Exception as e:
            response_data['blob_error'] = f"Error al interactuar con Vercel Blob: {e}"


        # --- Enviar la Respuesta ---
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))

    def do_POST(self):
        """
        Maneja las solicitudes POST.
        Guarda un mensaje en Postgres y sube contenido a Vercel Blob.
        """
        content_length = int(self.headers['Content-Length'])
        post_body = self.rfile.read(content_length).decode('utf-8')
        
        response_data = {}

        # --- Interacción con Vercel Postgres (guardar mensaje) ---
        conn = None
        try:
            data = json.loads(post_body)
            new_message = data.get('message', 'Mensaje vacío')

            conn = get_db_connection()
            cur = conn.cursor()
            # Eliminar mensajes anteriores si solo queremos uno simple
            cur.execute("DELETE FROM messages;")
            cur.execute("INSERT INTO messages (content) VALUES (%s);", (new_message,))
            conn.commit()
            cur.close()
            response_data['postgres_status'] = f"Mensaje guardado en Postgres: '{new_message}'"
        except json.JSONDecodeError:
            response_data['postgres_status'] = "Cuerpo POST inválido (no es JSON)."
        except Exception as e:
            response_data['postgres_error'] = f"Error al guardar en Postgres: {e}"
        finally:
            if conn:
                conn.close()

        # --- Interacción con Vercel Blob (subir archivo de texto) ---
        try:
            # Puedes subir el mismo contenido del POST como un blob
            blob_name = "mi_texto_simple.txt" # Nombre fijo para este ejemplo
            # Puedes usar 'data.get('blob_content', 'default_blob_content')'
            # si esperas un campo específico en el JSON para el blob
            uploaded_blob = put_blob(blob_name, post_body)
            response_data['blob_status'] = f"Blob '{uploaded_blob['pathname']}' subido exitosamente."
            response_data['blob_url'] = uploaded_blob['url']
        except Exception as e:
            response_data['blob_error'] = f"Error al subir a Vercel Blob: {e}"

        # --- Enviar la Respuesta ---
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
