import aiohttp
import jinja2
import urllib.parse
from FileStream.config import Telegram, Server
from FileStream.utils.database import Database
from FileStream.utils.human_readable import humanbytes

# Conexión a la base de datos
db = Database(Telegram.DATABASE_URL, Telegram.SESSION_NAME)

async def render_page(db_id):
    # Obtener datos del archivo desde la base
    file_data = await db.get_file(db_id)

    # Usar BASE_URL si está definida, sino caer en Server.URL
    base_url = getattr(Server, "BASE_URL", Server.URL).rstrip("/")
    src = f"{base_url}/dl/{file_data['_id']}"

    # Datos básicos del archivo
    file_size = humanbytes(file_data['file_size'])
    file_name = file_data['file_name'].replace("_", " ")

    # Seleccionar plantilla según el tipo MIME
    if str((file_data['mime_type']).split('/')[0].strip()) == 'video':
        template_file = "FileStream/template/play.html"
    else:
        template_file = "FileStream/template/dl.html"
        # Obtener tamaño real desde el enlace de descarga
        async with aiohttp.ClientSession() as s:
            async with s.get(src) as u:
                file_size = humanbytes(int(u.headers.get('Content-Length')))

    # Cargar plantilla y renderizar
    with open(template_file) as f:
        template = jinja2.Template(f.read())

    return template.render(
        file_name=file_name,
        file_url=src,      # Enlace público válido
        file_size=file_size
    )
