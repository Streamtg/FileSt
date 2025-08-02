import os
import json
import logging

class FIleNotFound(Exception):
    pass

class Database:
    def __init__(self, db_url=None, session_name="FileStreamBot"):
        self.session_name = session_name

        # Si no hay DATABASE_URL, usar JSON local
        if not db_url or db_url.strip() == "":
            # Ruta local por defecto dentro de utils
            self.db_path = os.path.join(
                os.path.dirname(__file__), "database.json"
            )
            self.use_local = True
        else:
            # Si es MongoDB u otro backend
            self.db_path = db_url
            self.use_local = False

        self.local_data = {}
        self.load_local()

    # ---------------------------------------------------------------------
    # Carga la base de datos local (JSON)
    # ---------------------------------------------------------------------
    def load_local(self):
        if self.use_local:
            if not os.path.exists(self.db_path):
                logging.warning(f"[DB] No existe {self.db_path}, creando nuevo archivo...")
                with open(self.db_path, "w") as f:
                    json.dump({"users": [], "files": {}, "blacklist": []}, f, indent=4)

            try:
                with open(self.db_path, "r") as f:
                    self.local_data = json.load(f)
            except json.JSONDecodeError:
                logging.error(f"[DB] Archivo {self.db_path} corrupto, recreando...")
                self.local_data = {"users": [], "files": {}, "blacklist": []}
                self.save_local()

    # ---------------------------------------------------------------------
    def save_local(self):
        if self.use_local:
            with open(self.db_path, "w") as f:
                json.dump(self.local_data, f, indent=4)

    # ---------------------------------------------------------------------
    # Métodos para usuarios
    # ---------------------------------------------------------------------
    async def add_user(self, user_id):
        if self.use_local:
            if user_id not in self.local_data["users"]:
                self.local_data["users"].append(user_id)
                self.save_local()

    async def get_user(self, user_id):
        if self.use_local:
            return user_id in self.local_data.get("users", [])
        return False

    async def is_user_banned(self, user_id):
        if self.use_local:
            return user_id in self.local_data.get("blacklist", [])
        return False

    # ---------------------------------------------------------------------
    # Métodos para archivos
    # ---------------------------------------------------------------------
    async def add_file(self, file_info: dict):
        """
        Guarda un archivo en la base de datos local.
        Genera un ID interno (_id) único para cada archivo.
        """
        if self.use_local:
            # Generar un _id simple
            _id = str(len(self.local_data["files"]) + 1)
            file_info["_id"] = _id
            self.local_data["files"][_id] = file_info
            self.save_local()
            return _id

    async def get_file(self, _id: str):
        if self.use_local:
            if _id in self.local_data["files"]:
                return self.local_data["files"][_id]
            raise FIleNotFound
        raise FIleNotFound

    async def update_file_ids(self, _id: str, file_ids: dict):
        if self.use_local and _id in self.local_data["files"]:
            self.local_data["files"][_id]["file_ids"] = file_ids
            self.save_local()
