import json
import os
import time
from bson.objectid import ObjectId
from bson.errors import InvalidId
from FileStream.server.exceptions import FIleNotFound

try:
    import motor.motor_asyncio
    USE_DB = True
except ImportError:
    USE_DB = False

class Database:
    def __init__(self, uri=None, database_name="FileStream"):
        self.use_db = bool(uri) and USE_DB
        if self.use_db:
            self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
            self.db = self._client[database_name]
            self.col = self.db.users
            self.black = self.db.blacklist
            self.file = self.db.file
        else:
            # Ruta del archivo JSON local
            self.json_path = os.path.join(os.path.dirname(__file__), "database.json")
            # Cargar datos o crear estructura inicial
            if os.path.exists(self.json_path):
                with open(self.json_path, "r") as f:
                    self.local_data = json.load(f)
            else:
                self.local_data = {
                    "users": [],
                    "blacklist": [],
                    "files": []
                }
                self._save_json()

    def _save_json(self):
        with open(self.json_path, "w") as f:
            json.dump(self.local_data, f, indent=4)

    # ----------------- [USUARIOS] ------------------ #
    def new_user(self, id):
        return dict(
            id=id,
            join_date=time.time(),
            Links=0
        )

    async def add_user(self, id):
        if self.use_db:
            user = self.new_user(id)
            await self.col.insert_one(user)
        else:
            if not any(u["id"] == id for u in self.local_data["users"]):
                self.local_data["users"].append(self.new_user(id))
                self._save_json()

    async def get_user(self, id):
        if self.use_db:
            return await self.col.find_one({"id": int(id)})
        else:
            for u in self.local_data["users"]:
                if u["id"] == id:
                    return u
            return None

    async def total_users_count(self):
        if self.use_db:
            return await self.col.count_documents({})
        else:
            return len(self.local_data["users"])

    async def get_all_users(self):
        if self.use_db:
            return self.col.find({})
        else:
            return self.local_data["users"]

    async def delete_user(self, user_id):
        if self.use_db:
            await self.col.delete_many({"id": int(user_id)})
        else:
            self.local_data["users"] = [u for u in self.local_data["users"] if u["id"] != user_id]
            self._save_json()

    # --------------- [USUARIOS BLOQUEADOS] -------------- #
    def black_user(self, id):
        return dict(
            id=id,
            ban_date=time.time()
        )

    async def ban_user(self, id):
        if self.use_db:
            user = self.black_user(id)
            await self.black.insert_one(user)
        else:
            if not any(b["id"] == id for b in self.local_data["blacklist"]):
                self.local_data["blacklist"].append(self.black_user(id))
                self._save_json()

    async def unban_user(self, id):
        if self.use_db:
            await self.black.delete_one({"id": int(id)})
        else:
            self.local_data["blacklist"] = [b for b in self.local_data["blacklist"] if b["id"] != id]
            self._save_json()

    async def is_user_banned(self, id):
        if self.use_db:
            user = await self.black.find_one({"id": int(id)})
            return True if user else False
        else:
            return any(b["id"] == id for b in self.local_data["blacklist"])

    async def total_banned_users_count(self):
        if self.use_db:
            return await self.black.count_documents({})
        else:
            return len(self.local_data["blacklist"])

    # --------------- [ARCHIVOS] ------------------- #
    async def add_file(self, file_info):
        if self.use_db:
            file_info["time"] = time.time()
            fetch_old = await self.get_file_by_fileuniqueid(file_info["user_id"], file_info["file_unique_id"])
            if fetch_old:
                return fetch_old["_id"]
            await self.count_links(file_info["user_id"], "+")
            return (await self.file.insert_one(file_info)).inserted_id
        else:
            file_info["time"] = time.time()
            for f in self.local_data["files"]:
                if f["user_id"] == file_info["user_id"] and f["file_unique_id"] == file_info["file_unique_id"]:
                    return f["_id"]
            file_info["_id"] = str(ObjectId())
            self.local_data["files"].append(file_info)
            await self.count_links(file_info["user_id"], "+")
            self._save_json()
            return file_info["_id"]

    async def get_file(self, _id):
        if self.use_db:
            try:
                file_info = await self.file.find_one({"_id": ObjectId(_id)})
                if not file_info:
                    raise FIleNotFound
                return file_info
            except InvalidId:
                raise FIleNotFound
        else:
            for idx, f in enumerate(self.local_data["files"]):
                if f["_id"] == _id:
                    return f
            raise FIleNotFound

    async def get_file_by_fileuniqueid(self, id, file_unique_id, many=False):
        if self.use_db:
            if many:
                return self.file.find({"file_unique_id": file_unique_id})
            else:
                file_info = await self.file.find_one({"user_id": id, "file_unique_id": file_unique_id})
            if file_info:
                return file_info
            return False
        else:
            if many:
                return [f for f in self.local_data["files"] if f["file_unique_id"] == file_unique_id]
            else:
                for f in self.local_data["files"]:
                    if f["user_id"] == id and f["file_unique_id"] == file_unique_id:
                        return f
                return False

    async def total_files(self, id=None):
        if self.use_db:
            if id:
                return await self.file.count_documents({"user_id": id})
            return await self.file.count_documents({})
        else:
            if id:
                return len([f for f in self.local_data["files"] if f["user_id"] == id])
            return len(self.local_data["files"])

    async def delete_one_file(self, _id):
        if self.use_db:
            await self.file.delete_one({"_id": ObjectId(_id)})
        else:
            self.local_data["files"] = [f for f in self.local_data["files"] if f["_id"] != _id]
            self._save_json()

    async def update_file_ids(self, _id, file_ids: dict):
        if self.use_db:
            await self.file.update_one({"_id": ObjectId(_id)}, {"$set": {"file_ids": file_ids}})
        else:
            for f in self.local_data["files"]:
                if f["_id"] == _id:
                    f["file_ids"] = file_ids
                    self._save_json()
                    break

    async def count_links(self, id, operation: str):
        if self.use_db:
            if operation == "-":
                await self.col.update_one({"id": id}, {"$inc": {"Links": -1}})
            elif operation == "+":
                await self.col.update_one({"id": id}, {"$inc": {"Links": 1}})
        else:
            for u in self.local_data["users"]:
                if u["id"] == id:
                    if operation == "-":
                        u["Links"] = max(0, u.get("Links", 0) - 1)
                    elif operation == "+":
                        u["Links"] = u.get("Links", 0) + 1
                    self._save_json()
                    break
