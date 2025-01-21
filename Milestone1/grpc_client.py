import grpc
import example_pb2
import example_pb2_grpc

def run():
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = example_pb2_grpc.ExampleServiceStub(channel)
        response = stub.GetMessage(example_pb2.RequestMessage(id="world"))
        print(f"Response: {response.message}")

if __name__ == "__main__":
    run()
