import json
import os
import asyncio
import uuid

class FIleNotFound(Exception):
    pass

class Database:
    def __init__(self, db_path, session_name):
        self.db_path = db_path
        self.session_name = session_name
        self.local_data = {"files": {}, "users": {}, "blacklist": []}
        self.load_local()

    def load_local(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self.local_data = json.load(f)
            except Exception as e:
                print(f"Error loading database JSON: {e}")
                self.local_data = {"files": {}, "users": {}, "blacklist": []}
        else:
            self.save_local()

    def save_local(self):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self.local_data, f, indent=4)

    async def get_file(self, _id):
        files = self.local_data.get("files", {})
        file_info = files.get(_id)
        if not file_info:
            raise FIleNotFound(f"Archivo con id {_id} no encontrado")
        return file_info

    async def add_file(self, file_info: dict):
        _id = str(uuid.uuid4())
        files = self.local_data.setdefault("files", {})
        files[_id] = file_info
        self.save_local()
        return _id

    async def update_file_ids(self, _id, file_ids):
        files = self.local_data.get("files", {})
        if _id in files:
            files[_id]["file_ids"] = file_ids
            self.save_local()

    async def get_user(self, user_id):
        users = self.local_data.get("users", {})
        return users.get(str(user_id), None)

    async def add_user(self, user_id):
        users = self.local_data.setdefault("users", {})
        if str(user_id) not in users:
            users[str(user_id)] = {"id": user_id}
            self.save_local()

    async def is_user_banned(self, user_id):
        return str(user_id) in self.local_data.get("blacklist", [])

    # ... Puedes agregar aquí otros métodos que necesites
