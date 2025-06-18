from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import settings

client: AsyncIOMotorClient = None
db: AsyncIOMotorDatabase = None

async def connect_to_mongo():
    global client, db
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    print(f"Connected to MongoDB: {settings.MONGODB_URL}, Database: {settings.DATABASE_NAME}")

async def close_mongo_connection():
    global client
    if client:
        client.close()
        print("MongoDB connection closed.")

def get_database() -> AsyncIOMotorDatabase:
    if db is None:
        # This case should ideally not happen if connect_to_mongo is called at startup
        # Consider raising an error or ensuring connect_to_mongo is always called first.
        raise RuntimeError("Database not initialized. Call connect_to_mongo first.")
    return db

# Example usage (optional, for direct testing of this module)
# if __name__ == "__main__":
#     import asyncio
#     async def main():
#         await connect_to_mongo()
#         # Perform database operations here
#         print(f"DB Name: {get_database().name}")
#         collections = await get_database().list_collection_names()
#         print(f"Collections: {collections}")
#         await close_mongo_connection()
#     asyncio.run(main())