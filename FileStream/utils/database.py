import os
import json
import time
import pymongo
import motor.motor_asyncio
from bson.objectid import ObjectId
from bson.errors import InvalidId
from FileStream.server.exceptions import FIleNotFound

class Database:
    def __init__(self, uri, database_name):
        self.use_json = False
        self.local_file = "local_db.json"
        self.local_data = {"users": [], "blacklist": [], "files": []}

        # Si no hay URI o es "true", usar JSON local
        if not uri or uri.lower() == "true":
            print("⚠ No MongoDB URI found — using local JSON database.")
            self.use_json = True
            self._load_local()
        else:
            try:
                self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
                self.db = self._client[database_name]
                self.col = self.db.users
                self.black = self.db.blacklist
                self.file = self.db.file
            except Exception as e:
                print(f"⚠ Error connecting to MongoDB: {e}")
                print("⚠ Switching to local JSON database.")
                self.use_json = True
                self._load_local()

    # ---------------- JSON MODE ---------------- #
    def _load_local(self):
        if os.path.exists(self.local_file):
            try:
                with open(self.local_file, "r") as f:
                    self.local_data = json.load(f)
            except:
                self.local_data = {"users": [], "blacklist": [], "files": []}

    def _save_local(self):
        with open(self.local_file, "w") as f:
            json.dump(self.local_data, f)

    # ---------------- USER FUNCTIONS ---------------- #
    def new_user(self, id):
        return dict(
            id=id,
            join_date=time.time(),
            Links=0
        )

    async def add_user(self, id):
        if self.use_json:
            if not any(u["id"] == id for u in self.local_data["users"]):
                self.local_data["users"].append(self.new_user(id))
                self._save_local()
        else:
            await self.col.insert_one(self.new_user(id))

    async def get_user(self, id):
        if self.use_json:
            return next((u for u in self.local_data["users"] if u["id"] == id), None)
        else:
            return await self.col.find_one({'id': int(id)})

    async def total_users_count(self):
        if self.use_json:
            return len(self.local_data["users"])
        else:
            return await self.col.count_documents({})

    async def get_all_users(self):
        if self.use_json:
            return self.local_data["users"]
        else:
            return self.col.find({})

    async def delete_user(self, user_id):
        if self.use_json:
            self.local_data["users"] = [u for u in self.local_data["users"] if u["id"] != user_id]
            self._save_local()
        else:
            await self.col.delete_many({'id': int(user_id)})

    # ---------------- BAN FUNCTIONS ---------------- #
    def black_user(self, id):
        return dict(
            id=id,
            ban_date=time.time()
        )

    async def ban_user(self, id):
        if self.use_json:
            if not any(u["id"] == id for u in self.local_data["blacklist"]):
                self.local_data["blacklist"].append(self.black_user(id))
                self._save_local()
        else:
            await self.black.insert_one(self.black_user(id))

    async def unban_user(self, id):
        if self.use_json:
            self.local_data["blacklist"] = [u for u in self.local_data["blacklist"] if u["id"] != id]
            self._save_local()
        else:
            await self.black.delete_one({'id': int(id)})

    async def is_user_banned(self, id):
        if self.use_json:
            return any(u["id"] == id for u in self.local_data["blacklist"])
        else:
            return bool(await self.black.find_one({"id": int(id)}))

    async def total_banned_users_count(self):
        if self.use_json:
            return len(self.local_data["blacklist"])
        else:
            return await self.black.count_documents({})

    # ---------------- FILE FUNCTIONS ---------------- #
    async def add_file(self, file_info):
        file_info["time"] = time.time()

        if self.use_json:
            self.local_data["files"].append(file_info)
            self._save_local()
            return len(self.local_data["files"]) - 1
        else:
            fetch_old = await self.get_file_by_fileuniqueid(file_info["user_id"], file_info["file_unique_id"])
            if fetch_old:
                return fetch_old["_id"]
            await self.count_links(file_info["user_id"], "+")
            return (await self.file.insert_one(file_info)).inserted_id

    async def get_file(self, _id):
        if self.use_json:
            try:
                idx = int(_id)
                return self.local_data["files"][idx]
            except:
                raise FIleNotFound
        else:
            try:
                file_info = await self.file.find_one({"_id": ObjectId(_id)})
                if not file_info:
                    raise FIleNotFound
                return file_info
            except InvalidId:
                raise FIleNotFound

    async def get_file_by_fileuniqueid(self, id, file_unique_id, many=False):
        if self.use_json:
            for f in self.local_data["files"]:
                if f["user_id"] == id and f["file_unique_id"] == file_unique_id:
                    return f
            return False
        else:
            if many:
                return self.file.find({"file_unique_id": file_unique_id})
            else:
                return await self.file.find_one({"user_id": id, "file_unique_id": file_unique_id})

    async def total_files(self, id=None):
        if self.use_json:
            if id:
                return len([f for f in self.local_data["files"] if f["user_id"] == id])
            return len(self.local_data["files"])
        else:
            if id:
                return await self.file.count_documents({"user_id": id})
            return await self.file.count_documents({})

    async def delete_one_file(self, _id):
        if self.use_json:
            try:
                idx = int(_id)
                self.local_data["files"].pop(idx)
                self._save_local()
            except:
                pass
        else:
            await self.file.delete_one({'_id': ObjectId(_id)})

    async def update_file_ids(self, _id, file_ids: dict):
        if self.use_json:
            try:
                idx = int(_id)
                self.local_data["files"][idx]["file_ids"] = file_ids
                self._save_local()
            except:
                pass
        else:
            await self.file.update_one({"_id": ObjectId(_id)}, {"$set": {"file_ids": file_ids}})

    async def count_links(self, id, operation: str):
        if self.use_json:
            for user in self.local_data["users"]:
                if user["id"] == id:
                    if operation == "-":
                        user["Links"] -= 1
                    elif operation == "+":
                        user["Links"] += 1
                    self._save_local()
                    break
        else:
            if operation == "-":
                await self.col.update_one({"id": id}, {"$inc": {"Links": -1}})
            elif operation == "+":
                await self.col.update_one({"id": id}, {"$inc": {"Links": 1}})
