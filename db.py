from motor.motor_asyncio import AsyncIOMotorClient

# Aapki di hui MongoDB details
DB_URL = "mongodb+srv://asvm:incorrectasvm@cluster0.v2z8vnw.mongodb.net/?appName=Cluster0"
DB_NAME = "PosterBot"

class Database:
    def __init__(self, uri, database_name):
        self._client = AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.users = self.db.users

    async def add_user(self, user_id):
        user = await self.users.find_one({"_id": user_id})
        if not user:
            await self.users.insert_one({"_id": user_id})
            return True
        return False

# Initialize DB connection
db = Database(DB_URL, DB_NAME)
