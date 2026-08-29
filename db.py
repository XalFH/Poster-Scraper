from motor.motor_asyncio import AsyncIOMotorClient

DB_URL = "mongodb+srv://asvm:incorrectasvm@cluster0.v2z8vnw.mongodb.net/?appName=Cluster0"
DB_NAME = "PosterBot"

class Database:
    def __init__(self, uri, database_name):
        self._client = AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.users = self.db.users
        self.settings = self.db.settings

    async def add_user(self, user_id):
        user = await self.users.find_one({"_id": user_id})
        if not user:
            await self.users.insert_one({"_id": user_id})
            return True # Naya user hai
        return False # Purana user hai

    async def get_all_users(self):
        return self.users.find({})

    async def total_users(self):
        return await self.users.count_documents({})

    # --- ADVANCED SETTINGS LOGIC ---
    async def get_settings(self):
        config = await self.settings.find_one({"_id": "bot_config"})
        if not config:
            default = {
                "_id": "bot_config", 
                "fsub_id": None, 
                "fsub_link": None, 
                "log_channel": None, 
                "auth_groups": []
            }
            await self.settings.insert_one(default)
            return default
        return config

    async def update_setting(self, key, value):
        await self.settings.update_one({"_id": "bot_config"}, {"$set": {key: value}}, upsert=True)

    async def add_auth_group(self, group_id):
        await self.settings.update_one({"_id": "bot_config"}, {"$addToSet": {"auth_groups": group_id}}, upsert=True)

db = Database(DB_URL, DB_NAME)
