# api/index.py

from http.server import BaseHTTPRequestHandler
from urllib import parse

class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        """
        Maneja las solicitudes GET.
        Este método se ejecuta cuando alguien accede a la URL de tu función.
        """
        # Obtenemos la URL completa de la solicitud
        s = self.path
        # Parseamos los parámetros de la consulta (lo que viene después del '?')
        query_params = dict(parse.parse_qsl(parse.urlsplit(s).query))

        # Intentamos obtener el valor del parámetro 'name'.
        # Si no se proporciona, usamos 'Mundo' por defecto.
        name = query_params.get('name', 'Mundo')

        # Creamos el mensaje de respuesta
        message = f"¡Hola, {name} desde Vercel con Python!"

        # Configuramos la respuesta HTTP
        self.send_response(200) # Código de estado HTTP 200 (OK)
        self.send_header('Content-type', 'text/plain; charset=utf-8') # Tipo de contenido como texto plano y codificación UTF-8
        self.end_headers()

        # Escribimos el mensaje en el cuerpo de la respuesta
        # Asegúrate de codificar el mensaje a bytes
        self.wfile.write(message.encode('utf-8'))

    def do_POST(self):
        """
        Maneja las solicitudes POST.
        Puedes añadir lógica aquí para procesar datos enviados en el cuerpo de la solicitud.
        """
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write("¡Recibida una solicitud POST! (Este ejemplo no procesa el cuerpo)".encode('utf-8'))
