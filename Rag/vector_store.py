import chromadb
from chromadb.config import Settings
from config import VECTOR_DB_DIR, COLLECTION_NAME

client = chromadb.Client(Settings(persist_directory=VECTOR_DB_DIR))

collection = client.get_or_create_collection(name=COLLECTION_NAME)
