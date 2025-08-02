import json
import os
import asyncio
from typing import Optional


class Database:
    def __init__(self, mongo_uri: Optional[str], session_name: str):
        self.mongo_uri = mongo_uri
        self.session_name = session_name
        self.local_path = os.path.join(os.path.dirname(__file__), "database.json")

        if not os.path.exists(self.local_path):
            self.local_data = {
                "users": [],
                "files": {},
                "blacklist": []
            }
            self._save_local()
        else:
            with open(self.local_path, "r", encoding="utf-8") as f:
                try:
                    self.local_data = json.load(f)
                except Exception:
                    self.local_data = {
                        "users": [],
                        "files": {},
                        "blacklist": []
                    }
                    self._save_local()

        # Garantiza que existan todas las claves necesarias
        if "users" not in self.local_data:
            self.local_data["users"] = []
        if "files" not in self.local_data:
            self.local_data["files"] = {}
        if "blacklist" not in self.local_data:
            self.local_data["blacklist"] = []
        self._save_local()

    def _save_local(self):
        with open(self.local_path, "w", encoding="utf-8") as f:
            json.dump(self.local_data, f, indent=2, ensure_ascii=False)

    # ---------------------- USER METHODS ----------------------
    async def add_user(self, user_id: int):
        if user_id not in self.local_data["users"]:
            self.local_data["users"].append(user_id)
            self._save_local()

    async def get_user(self, user_id: int):
        return user_id if user_id in self.local_data["users"] else None

    # ---------------------- FILE METHODS ----------------------
    async def add_file(self, file_info: dict):
        _id = str(file_info["file_unique_id"])
        self.local_data["files"][_id] = file_info
        self._save_local()
        return _id

    async def get_file(self, _id: str):
        if _id in self.local_data["files"]:
            return self.local_data["files"][_id]
        raise FileNotFoundError

    async def update_file_ids(self, _id: str, file_ids: dict):
        if _id in self.local_data["files"]:
            self.local_data["files"][_id]["file_ids"] = file_ids
            self._save_local()

    # ---------------------- BAN METHODS ----------------------
    async def is_user_banned(self, user_id: int):
        return user_id in self.local_data["blacklist"]

    async def ban_user(self, user_id: int):
        if user_id not in self.local_data["blacklist"]:
            self.local_data["blacklist"].append(user_id)
            self._save_local()

    async def unban_user(self, user_id: int):
        if user_id in self.local_data["blacklist"]:
            self.local_data["blacklist"].remove(user_id)
            self._save_local()
