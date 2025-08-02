import os
import json
import time
import pymongo
import motor.motor_asyncio
from bson.objectid import ObjectId
from bson.errors import InvalidId
from FileStream.server.exceptions import FIleNotFound

LOCAL_DB_FILE = "local_db.json"


class Database:
    def __init__(self, uri, database_name):
        self.use_local = not uri or uri.strip() == ""
        self.local_path = LOCAL_DB_FILE

        if self.use_local:
            # Cargar o crear archivo local
            if not os.path.exists(self.local_path):
                with open(self.local_path, "w", encoding="utf-8") as f:
                    json.dump({"users": [], "blacklist": [], "files": []}, f)
        else:
            # Conexión MongoDB normal
            self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
            self.db = self._client[database_name]
            self.col = self.db.users
            self.black = self.db.blacklist
            self.file = self.db.file

    # ---------------------[ Helpers Local JSON ]--------------------- #
    def _load_local(self):
        with open(self.local_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_local(self, data):
        with open(self.local_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # ---------------------[ NEW USER ]--------------------- #
    def new_user(self, id):
        return dict(id=id, join_date=time.time(), Links=0)

    async def add_user(self, id):
        if self.use_local:
            data = self._load_local()
            if not any(u["id"] == id for u in data["users"]):
                data["users"].append(self.new_user(id))
                self._save_local(data)
        else:
            await self.col.insert_one(self.new_user(id))

    async def get_user(self, id):
        if self.use_local:
            data = self._load_local()
            return next((u for u in data["users"] if u["id"] == id), None)
        else:
            return await self.col.find_one({"id": int(id)})

    async def total_users_count(self):
        if self.use_local:
            return len(self._load_local()["users"])
        else:
            return await self.col.count_documents({})

    # ---------------------[ BAN SYSTEM ]--------------------- #
    def black_user(self, id):
        return dict(id=id, ban_date=time.time())

    async def ban_user(self, id):
        if self.use_local:
            data = self._load_local()
            if not any(b["id"] == id for b in data["blacklist"]):
                data["blacklist"].append(self.black_user(id))
                self._save_local(data)
        else:
            await self.black.insert_one(self.black_user(id))

    async def unban_user(self, id):
        if self.use_local:
            data = self._load_local()
            data["blacklist"] = [b for b in data["blacklist"] if b["id"] != id]
            self._save_local(data)
        else:
            await self.black.delete_one({"id": int(id)})

    async def is_user_banned(self, id):
        if self.use_local:
            return any(b["id"] == id for b in self._load_local()["blacklist"])
        else:
            return bool(await self.black.find_one({"id": int(id)}))

    # ---------------------[ FILE SYSTEM ]--------------------- #
    async def add_file(self, file_info):
        file_info["time"] = time.time()

        if self.use_local:
            data = self._load_local()
            file_id = str(len(data["files"]) + 1)  # ID simple incremental
            file_info["_id"] = file_id
            data["files"].append(file_info)
            self._save_local(data)
            return file_id
        else:
            fetch_old = await self.get_file_by_fileuniqueid(file_info["user_id"], file_info["file_unique_id"])
            if fetch_old:
                return fetch_old["_id"]
            return (await self.file.insert_one(file_info)).inserted_id

    async def get_file(self, _id):
        if self.use_local:
            data = self._load_local()
            file_info = next((f for f in data["files"] if str(f["_id"]) == str(_id)), None)
            if not file_info:
                raise FIleNotFound
            return file_info
        else:
            try:
                file_info = await self.file.find_one({"_id": ObjectId(_id)})
                if not file_info:
                    raise FIleNotFound
                return file_info
            except InvalidId:
                raise FIleNotFound

    async def get_file_by_fileuniqueid(self, id, file_unique_id, many=False):
        if self.use_local:
            files = [f for f in self._load_local()["files"] if f["file_unique_id"] == file_unique_id]
            return files if many else (files[0] if files else False)
        else:
            if many:
                return self.file.find({"file_unique_id": file_unique_id})
            else:
                return await self.file.find_one({"user_id": id, "file_unique_id": file_unique_id})

    async def total_files(self, id=None):
        if self.use_local:
            if id:
                return len([f for f in self._load_local()["files"] if f["user_id"] == id])
            return len(self._load_local()["files"])
        else:
            if id:
                return await self.file.count_documents({"user_id": id})
            return await self.file.count_documents({})

    async def delete_one_file(self, _id):
        if self.use_local:
            data = self._load_local()
            data["files"] = [f for f in data["files"] if str(f["_id"]) != str(_id)]
            self._save_local(data)
        else:
            await self.file.delete_one({"_id": ObjectId(_id)})

    async def update_file_ids(self, _id, file_ids: dict):
        if self.use_local:
            data = self._load_local()
            for f in data["files"]:
                if str(f["_id"]) == str(_id):
                    f["file_ids"] = file_ids
                    break
            self._save_local(data)
        else:
            await self.file.update_one({"_id": ObjectId(_id)}, {"$set": {"file_ids": file_ids}})

    # ---------------------[ COUNT LINKS ]--------------------- #
    async def count_links(self, id, operation: str):
        if self.use_local:
            data = self._load_local()
            for u in data["users"]:
                if u["id"] == id:
                    if operation == "+":
                        u["Links"] += 1
                    elif operation == "-":
                        u["Links"] -= 1
                    break
            self._save_local(data)
        else:
            if operation == "-":
                await self.col.update_one({"id": id}, {"$inc": {"Links": -1}})
            elif operation == "+":
                await self.col.update_one({"id": id}, {"$inc": {"Links": 1}})
