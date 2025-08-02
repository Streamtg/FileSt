import pymongo
import time
import motor.motor_asyncio
from bson.objectid import ObjectId
from bson.errors import InvalidId
from FileStream.server.exceptions import FIleNotFound
import os
import json


class Database:
    def __init__(self, uri=None, database_name="filestream"):
        self.use_json = False

        if uri and uri != "true":
            try:
                self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
                self.db = self._client[database_name]
                self.col = self.db.users
                self.black = self.db.blacklist
                self.file = self.db.file
            except Exception:
                print("⚠ Error conectando a MongoDB — usando base de datos JSON local.")
                self.use_json = True
        else:
            print("⚠ No MongoDB URI found — using local JSON database.")
            self.use_json = True

        if self.use_json:
            self.json_path = "database.json"
            if not os.path.exists(self.json_path):
                with open(self.json_path, "w") as f:
                    json.dump({"users": [], "blacklist": [], "files": []}, f)
            with open(self.json_path, "r") as f:
                self.local_data = json.load(f)

    # -------------------[ JSON Helpers ]------------------- #
    def save_json(self):
        if self.use_json:
            with open(self.json_path, "w") as f:
                json.dump(self.local_data, f, indent=2)

    # -------------------[ USERS ]------------------- #
    def new_user(self, id):
        return dict(id=id, join_date=time.time(), Links=0)

    async def add_user(self, id):
        if self.use_json:
            if not any(u["id"] == id for u in self.local_data["users"]):
                self.local_data["users"].append(self.new_user(id))
                self.save_json()
        else:
            await self.col.insert_one(self.new_user(id))

    async def get_user(self, id):
        if self.use_json:
            return next((u for u in self.local_data["users"] if u["id"] == id), None)
        return await self.col.find_one({"id": int(id)})

    async def total_users_count(self):
        if self.use_json:
            return len(self.local_data["users"])
        return await self.col.count_documents({})

    async def delete_user(self, id):
        if self.use_json:
            self.local_data["users"] = [u for u in self.local_data["users"] if u["id"] != id]
            self.save_json()
        else:
            await self.col.delete_many({"id": int(id)})

    # -------------------[ BANS ]------------------- #
    def black_user(self, id):
        return dict(id=id, ban_date=time.time())

    async def ban_user(self, id):
        if self.use_json:
            if not any(b["id"] == id for b in self.local_data["blacklist"]):
                self.local_data["blacklist"].append(self.black_user(id))
                self.save_json()
        else:
            await self.black.insert_one(self.black_user(id))

    async def unban_user(self, id):
        if self.use_json:
            self.local_data["blacklist"] = [b for b in self.local_data["blacklist"] if b["id"] != id]
            self.save_json()
        else:
            await self.black.delete_one({"id": int(id)})

    async def is_user_banned(self, id):
        if self.use_json:
            return any(b["id"] == id for b in self.local_data["blacklist"])
        return bool(await self.black.find_one({"id": int(id)}))

    # -------------------[ FILES ]------------------- #
    async def add_file(self, file_info):
        file_info["time"] = time.time()

        if self.use_json:
            # Evita duplicados usando file_unique_id
            for idx, f in enumerate(self.local_data["files"]):
                if f.get("file_unique_id") == file_info.get("file_unique_id") and f.get("user_id") == file_info.get("user_id"):
                    return idx  # Devuelve el índice existente

            self.local_data["files"].append(file_info)
            self.save_json()
            return len(self.local_data["files"]) - 1  # Nuevo índice
        else:
            old_file = await self.file.find_one({
                "user_id": file_info["user_id"],
                "file_unique_id": file_info["file_unique_id"]
            })
            if old_file:
                return old_file["_id"]

            return (await self.file.insert_one(file_info)).inserted_id

    async def get_file(self, _id):
        if self.use_json:
            try:
                idx = int(_id)
                if idx < 0 or idx >= len(self.local_data["files"]):
                    raise FIleNotFound
                return self.local_data["files"][idx]
            except (ValueError, TypeError):
                raise FIleNotFound
        else:
            try:
                file_info = await self.file.find_one({"_id": ObjectId(_id)})
                if not file_info:
                    raise FIleNotFound
                return file_info
            except InvalidId:
                raise FIleNotFound

    # -------------------[ Extra Helpers ]------------------- #
    async def total_files(self, id=None):
        if self.use_json:
            if id:
                return sum(1 for f in self.local_data["files"] if f["user_id"] == id)
            return len(self.local_data["files"])
        if id:
            return await self.file.count_documents({"user_id": id})
        return await self.file.count_documents({})
