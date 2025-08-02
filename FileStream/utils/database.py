import os
import time
import json
import random
import string
from bson.errors import InvalidId
from FileStream.server.exceptions import FIleNotFound

try:
    import motor.motor_asyncio
    import pymongo
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False


class Database:
    def __init__(self, uri=None, database_name="filestreambot"):
        self.use_mongo = bool(uri and uri.strip() and MONGO_AVAILABLE)

        if self.use_mongo:
            # Conexión MongoDB
            self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
            self.db = self._client[database_name]
            self.col = self.db.users
            self.black = self.db.blacklist
            self.file = self.db.file
        else:
            # Base de datos local en JSON
            self.local_db_path = "local_db.json"
            if not os.path.exists(self.local_db_path):
                with open(self.local_db_path, "w") as f:
                    json.dump({"users": [], "blacklist": [], "files": []}, f)
            self._load_local_db()

    # ------------------ MODO LOCAL ------------------ #

    def _load_local_db(self):
        with open(self.local_db_path, "r") as f:
            self.local_data = json.load(f)

    def _save_local_db(self):
        with open(self.local_db_path, "w") as f:
            json.dump(self.local_data, f, indent=4)

    def _generate_id(self):
        """Genera un ID único tipo ObjectId de Mongo"""
        return ''.join(random.choices('0123456789abcdef', k=24))

    # ------------------ USUARIOS ------------------ #

    def new_user(self, id):
        return dict(id=id, join_date=time.time(), Links=0)

    async def add_user(self, id):
        if self.use_mongo:
            await self.col.insert_one(self.new_user(id))
        else:
            if not any(u["id"] == id for u in self.local_data["users"]):
                self.local_data["users"].append(self.new_user(id))
                self._save_local_db()

    async def get_user(self, id):
        if self.use_mongo:
            return await self.col.find_one({"id": int(id)})
        else:
            return next((u for u in self.local_data["users"] if u["id"] == id), None)

    async def is_user_banned(self, id):
        if self.use_mongo:
            return bool(await self.black.find_one({"id": int(id)}))
        else:
            return any(b["id"] == id for b in self.local_data["blacklist"])

    # ------------------ ARCHIVOS ------------------ #

    async def add_file(self, file_info):
        file_info["time"] = time.time()
        if self.use_mongo:
            return (await self.file.insert_one(file_info)).inserted_id
        else:
            file_info["_id"] = self._generate_id()
            self.local_data["files"].append(file_info)
            self._save_local_db()
            return file_info["_id"]

    async def get_file(self, _id):
        if self.use_mongo:
            try:
                from bson import ObjectId
                file_info = await self.file.find_one({"_id": ObjectId(_id)})
                if not file_info:
                    raise FIleNotFound
                return file_info
            except InvalidId:
                raise FIleNotFound
        else:
            for f in self.local_data["files"]:
                if str(f.get("_id")) == str(_id):
                    return f
            raise FIleNotFound

    # ------------------ BANEOS ------------------ #

    async def ban_user(self, id):
        if self.use_mongo:
            await self.black.insert_one({"id": id, "ban_date": time.time()})
        else:
            if not any(b["id"] == id for b in self.local_data["blacklist"]):
                self.local_data["blacklist"].append({"id": id, "ban_date": time.time()})
                self._save_local_db()

    async def unban_user(self, id):
        if self.use_mongo:
            await self.black.delete_one({"id": int(id)})
        else:
            self.local_data["blacklist"] = [b for b in self.local_data["blacklist"] if b["id"] != id]
            self._save_local_db()
