import os
import time
import json
import pymongo
import motor.motor_asyncio
from bson.objectid import ObjectId
from bson.errors import InvalidId
from FileStream.server.exceptions import FIleNotFound

# Ruta del archivo local
LOCAL_DB_FILE = "local_db.json"

def load_local_db():
    if os.path.exists(LOCAL_DB_FILE):
        try:
            with open(LOCAL_DB_FILE, "r") as f:
                return json.load(f)
        except:
            return {"users": [], "blacklist": [], "files": []}
    return {"users": [], "blacklist": [], "files": []}

def save_local_db(data):
    with open(LOCAL_DB_FILE, "w") as f:
        json.dump(data, f)

class Database:
    def __init__(self, uri=None, database_name="FileStream"):
        self.use_local = not uri or uri.lower() in ("true", "false", "none", "")
        
        if self.use_local:
            print("⚠ No MongoDB URI found — using local JSON database.")
            self.local_data = load_local_db()
        else:
            self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
            self.db = self._client[database_name]
            self.col = self.db.users
            self.black = self.db.blacklist
            self.file = self.db.file

    # ------------------ USERS ------------------ #
    def new_user(self, id):
        return dict(id=id, join_date=time.time(), Links=0)

    async def add_user(self, id):
        if self.use_local:
            if not any(u["id"] == id for u in self.local_data["users"]):
                self.local_data["users"].append(self.new_user(id))
                save_local_db(self.local_data)
        else:
            await self.col.insert_one(self.new_user(id))

    async def get_user(self, id):
        if self.use_local:
            return next((u for u in self.local_data["users"] if u["id"] == id), None)
        return await self.col.find_one({'id': int(id)})

    async def total_users_count(self):
        if self.use_local:
            return len(self.local_data["users"])
        return await self.col.count_documents({})

    async def is_user_banned(self, id):
        if self.use_local:
            return any(b["id"] == id for b in self.local_data["blacklist"])
        return bool(await self.black.find_one({"id": int(id)}))

    async def ban_user(self, id):
        if self.use_local:
            if not any(b["id"] == id for b in self.local_data["blacklist"]):
                self.local_data["blacklist"].append({"id": id, "ban_date": time.time()})
                save_local_db(self.local_data)
        else:
            await self.black.insert_one({"id": id, "ban_date": time.time()})

    async def unban_user(self, id):
        if self.use_local:
            self.local_data["blacklist"] = [b for b in self.local_data["blacklist"] if b["id"] != id]
            save_local_db(self.local_data)
        else:
            await self.black.delete_one({'id': int(id)})

    # ------------------ FILES ------------------ #
    async def add_file(self, file_info):
        file_info["time"] = time.time()
        if self.use_local:
            self.local_data["files"].append(file_info)
            save_local_db(self.local_data)
            return str(len(self.local_data["files"]) - 1)
        else:
            return (await self.file.insert_one(file_info)).inserted_id

    async def get_file(self, _id):
        if self.use_local:
            try:
                idx = int(_id)
                return self.local_data["files"][idx]
            except (ValueError, IndexError):
                raise FIleNotFound
        else:
            try:
                file_info = await self.file.find_one({"_id": ObjectId(_id)})
                if not file_info:
                    raise FIleNotFound
                return file_info
            except InvalidId:
                raise FIleNotFound

    async def total_files(self):
        if self.use_local:
            return len(self.local_data["files"])
        return await self.file.count_documents({})

    async def delete_one_file(self, _id):
        if self.use_local:
            try:
                idx = int(_id)
                del self.local_data["files"][idx]
                save_local_db(self.local_data)
            except (ValueError, IndexError):
                pass
        else:
            await self.file.delete_one({'_id': ObjectId(_id)})
