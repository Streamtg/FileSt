import os
import json
import asyncio

class FIleNotFound(Exception):
    pass

DB_FILE_PATH = os.path.join(os.path.dirname(__file__), "database.json")

DEFAULT_DB_STRUCTURE = {
    "users": [],
    "files": {},
    "blacklist": []
}

class Database:
    def __init__(self, database_url=None, session_name=None):
        # Ignoramos database_url y session_name para el almacenamiento local JSON
        self.db_file = DB_FILE_PATH
        # Crear base de datos si no existe o está corrupta
        if not os.path.exists(self.db_file):
            with open(self.db_file, "w") as f:
                json.dump(DEFAULT_DB_STRUCTURE, f, indent=2)
        else:
            try:
                with open(self.db_file, "r") as f:
                    json.load(f)  # Verificar que JSON sea válido
            except (json.JSONDecodeError, ValueError):
                with open(self.db_file, "w") as f:
                    json.dump(DEFAULT_DB_STRUCTURE, f, indent=2)

        # Cargar datos en memoria
        with open(self.db_file, "r") as f:
            self.local_data = json.load(f)

    async def _save(self):
        # Guardar local_data en JSON (bloqueante, se puede adaptar a async si quieres)
        with open(self.db_file, "w") as f:
            json.dump(self.local_data, f, indent=2)

    async def get_file(self, _id: str):
        # Busca el archivo por _id dentro de files
        files = self.local_data.get("files", {})
        # files es dict con keys = id, values = file info dict
        file_info = files.get(_id)
        if not file_info:
            raise FIleNotFound
        return file_info

    async def add_file(self, file_info: dict):
        # Añade un archivo nuevo con un id único (ejemplo: usar file_unique_id como clave)
        file_id = file_info.get("file_unique_id")
        if not file_id:
            raise ValueError("El archivo debe tener 'file_unique_id' para usarlo como ID")

        if "files" not in self.local_data:
            self.local_data["files"] = {}

        # Evitar duplicados: si ya existe un archivo igual (por user_id y unique_id), devolver la key existente
        for k, f in self.local_data["files"].items():
            if isinstance(f, dict) and f.get("user_id") == file_info.get("user_id") and f.get("file_unique_id") == file_info.get("file_unique_id"):
                return k

        # Añadir nuevo
        self.local_data["files"][file_id] = file_info
        await self._save()
        return file_id

    async def update_file_ids(self, file_id: str, file_ids: dict):
        if "files" not in self.local_data:
            self.local_data["files"] = {}

        if file_id not in self.local_data["files"]:
            raise FIleNotFound

        self.local_data["files"][file_id]["file_ids"] = file_ids
        await self._save()

    async def is_user_banned(self, user_id: int) -> bool:
        blacklist = self.local_data.get("blacklist", [])
        # blacklist puede ser lista simple de ids o dicts con "id" keys, según tu esquema
        for banned in blacklist:
            if isinstance(banned, dict) and banned.get("id") == user_id:
                return True
            if banned == user_id:
                return True
        return False

    async def get_user(self, user_id: int):
        users = self.local_data.get("users", [])
        for user in users:
            # Suponiendo user es dict con clave "id"
            if isinstance(user, dict) and user.get("id") == user_id:
                return user
        return None

    async def add_user(self, user_info: dict):
        if "users" not in self.local_data:
            self.local_data["users"] = []

        # Evitar duplicados
        for user in self.local_data["users"]:
            if isinstance(user, dict) and user.get("id") == user_info.get("id"):
                return

        self.local_data["users"].append(user_info)
        await self._save()

    async def ban_user(self, user_id: int):
        if "blacklist" not in self.local_data:
            self.local_data["blacklist"] = []
        if user_id not in self.local_data["blacklist"]:
            self.local_data["blacklist"].append(user_id)
            await self._save()

    async def unban_user(self, user_id: int):
        if "blacklist" in self.local_data and user_id in self.local_data["blacklist"]:
            self.local_data["blacklist"].remove(user_id)
            await self._save()
