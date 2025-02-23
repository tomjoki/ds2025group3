from pymongo import MongoClient
import re
import time
import threading
import subprocess
from collections import defaultdict

port_regex = re.compile(r"nginx-service.*\d+:(?P<port>\d+)/TCP")

def get_nginx_infos():
    try:
        ip = subprocess.run(['minikube', 'ip'], capture_output=True, text=True, check=True)
        ip = ip.stdout.strip()
        port = subprocess.run(['kubectl', 'get', 'svc'], capture_output=True, text=True, check=True)
        split_output = port.stdout.split("\n")
        for line in split_output:
            if "nginx-service" in line:
                match = re.match(port_regex, line)
                if match:
                    port = match.group("port")
                    return ip, port
    except subprocess.CalledProcessError as e:
        return

NGINX_SERVICE_IP, NGINX_SERVICE_PORT = get_nginx_infos()
print(f"nginx service and port: {NGINX_SERVICE_IP}:{NGINX_SERVICE_PORT}")


client = MongoClient(f"mongodb://{NGINX_SERVICE_IP}:{NGINX_SERVICE_PORT}/")
db = client.test_db
collection = db.test_collection

# Request number params for test
NUM_REQUESTS_PER_THREAD = 1000
NUM_THREADS = 10

request_counts = defaultdict(int)
request_counts_lock = threading.Lock()


def get_mongo_hostname(client):
    try:
        host_info = client.admin.command("hostInfo")
        return host_info["system"]["hostname"]
    except Exception as e:
        return f"Unknown (Error: {e})"


def perform_operations(thread_id):
    for i in range(NUM_REQUESTS_PER_THREAD):
        try:
            start_time = time.time()
            document = {"thread_id": thread_id, "request_id": i, "timestamp": time.time()}
            insert_result = collection.insert_one(document)
            query_result = collection.find_one({"_id": insert_result.inserted_id})
            end_time = time.time()
            response_time = end_time - start_time

            hostname = get_mongo_hostname(client)

            with request_counts_lock:
                request_counts[hostname] += 1

            print(f"Thread {thread_id}, Request {i+1}:")
            print(f"  Inserted ID: {insert_result.inserted_id}")
            print(f"  Query Result: {query_result}")
            print(f"  Server Hostname: {hostname}")
            print(f"  Response Time: {response_time:.4f} seconds")
            print("-" * 40)
        except Exception as e:
            print(f"Thread {thread_id}, Request {i+1} failed: {e}")

threads = []
for thread_id in range(NUM_THREADS):
    thread = threading.Thread(target=perform_operations, args=(thread_id,))
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()

print("Load testing completed.")
print("Requests per pod:")
for hostname, count in request_counts.items():
    print(f"{hostname}: {count}")