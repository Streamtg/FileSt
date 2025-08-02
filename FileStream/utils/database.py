import os
import json
import uuid
import asyncio

from FileStream.server.exceptions import FIleNotFound


class Database:
    def __init__(self, db_url=None, session_name=None):
        self.db_path = os.path.join(
            os.path.dirname(__file__), "database.json"
        )

        # Crea database.json si no existe
        if not os.path.exists(self.db_path):
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump({"files": [], "users": [], "blacklist": []}, f, indent=2)

        # Carga datos locales
        with open(self.db_path, "r", encoding="utf-8") as f:
            try:
                self.local_data = json.load(f)
            except json.JSONDecodeError:
                # Si está corrupto, reinicia el JSON
                self.local_data = {"files": [], "users": [], "blacklist": []}
                self._save()

        # Asegurar estructura correcta
        if "files" not in self.local_data:
            self.local_data["files"] = []
        if "users" not in self.local_data:
            self.local_data["users"] = []
        if "blacklist" not in self.local_data:
            self.local_data["blacklist"] = []

        self._save()

    def _save(self):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self.local_data, f, indent=2)

    # ---------------------------
    # USERS
    # ---------------------------
    async def get_user(self, user_id):
        for u in self.local_data["users"]:
            if u.get("id") == int(user_id):
                return u
        return None

    async def add_user(self, user_id):
        if not await self.get_user(user_id):
            self.local_data["users"].append({"id": int(user_id)})
            self._save()
            return True
        return False

    async def is_user_banned(self, user_id):
        return any(bid == int(user_id) for bid in self.local_data["blacklist"])

    async def ban_user(self, user_id):
        if int(user_id) not in self.local_data["blacklist"]:
            self.local_data["blacklist"].append(int(user_id))
            self._save()
            return True
        return False

    async def unban_user(self, user_id):
        if int(user_id) in self.local_data["blacklist"]:
            self.local_data["blacklist"].remove(int(user_id))
            self._save()
            return True
        return False

    # ---------------------------
    # FILES
    # ---------------------------
    async def get_file(self, _id):
        for f in self.local_data["files"]:
            if f.get("_id") == _id:
                return f
        raise FIleNotFound

    async def add_file(self, file_info):
        # Si ya existe, devuelve su _id
        for f in self.local_data["files"]:
            if (
                f.get("user_id") == file_info.get("user_id")
                and f.get("file_unique_id") == file_info.get("file_unique_id")
            ):
                return f["_id"]

        # Asegura un _id único
        file_info["_id"] = str(uuid.uuid4())

        # Guarda en la base
        self.local_data["files"].append(file_info)
        self._save()
        return file_info["_id"]

    async def update_file_ids(self, _id, file_ids):
        for f in self.local_data["files"]:
            if f.get("_id") == _id:
                f["file_ids"] = file_ids
                self._save()
                return True
        return False
