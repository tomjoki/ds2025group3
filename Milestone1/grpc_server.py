from concurrent import futures
import grpc
import example_pb2
import example_pb2_grpc

from pymongo import MongoClient
from confluent_kafka import Producer

client = MongoClient("mongodb://root:example@localhost:27017/")
db = client["example_db"]
collection = db["messages"]

producer = Producer({'bootstrap.servers': 'localhost:9092'})

class ExampleService(example_pb2_grpc.ExampleServiceServicer):
    def GetMessage(self, request, context):
        producer.produce('example_topic', key=request.id, value="gRPC request received")
        producer.flush()
        record = collection.find_one({"id": request.id})
        return example_pb2.ResponseMessage(message=record["message"] if record else "Message not found!")



def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    example_pb2_grpc.add_ExampleServiceServicer_to_server(ExampleService(), server)
    server.add_insecure_port('[::]:50051')
    print("gRPC server is running on port 50051...")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
