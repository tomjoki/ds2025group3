from fastapi import FastAPI
from pydantic import BaseModel
from pymongo import MongoClient
from confluent_kafka import Consumer
import asyncio

app = FastAPI()

# MongoDB Setup
client = MongoClient("mongodb://root:example@localhost:27017/")
db = client["example_db"]
collection = db["messages"]

# Kafka Consumer Setup
consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'example_group',
    'auto.offset.reset': 'earliest'
})
consumer.subscribe(['example_topic'])

# Pydantic Model
class Message(BaseModel):
    id: str
    message: str

# CRUD Endpoints
@app.get("/messages/{id}")
async def read_message(id: str):
    record = collection.find_one({"id": id})
    return record or {"error": "Message not found"}

@app.post("/messages/")
async def create_message(msg: Message):
    collection.insert_one(msg.dict())
    return {"status": "Message created"}

@app.put("/messages/{id}")
async def update_message(id: str, msg: Message):
    collection.update_one({"id": id}, {"$set": msg.dict()})
    return {"status": "Message updated"}

@app.delete("/messages/{id}")
async def delete_message(id: str):
    collection.delete_one({"id": id})
    return {"status": "Message deleted"}

# Kafka Consumer Task
async def consume_messages():
    while True:
        msg = consumer.poll(1.0)
        if msg is not None and msg.value() is not None:
            print(f"Received message: {msg.value().decode('utf-8')}")
        await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(consume_messages())
