# db_connect.py - Add SSL configuration
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

def get_database():
    try:
        # Add tlsAllowInvalidCertificates if you're having SSL issues
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000,
            tls=True,
            tlsAllowInvalidCertificates=True  # Remove this in production
        )
        
        # Test the connection
        client.admin.command('ping')
        
        db = client[DB_NAME]
        print(f"✅ Connected to MongoDB database: {DB_NAME}")
        return db
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        raise

if __name__ == "__main__":
    get_database()