from locust import HttpUser, task, between
from pymongo import MongoClient
import subprocess
import re

class MongoUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """
        Called when a simulated user starts executing the tasks.
        """
        ip, port = self.get_nginx_infos()
        self.client = MongoClient(f"mongodb://{ip}:{port}/")
        self.db = self.client.test

    def get_mongo_host_info(self):
        """
        Get the MongoDB server's hostname and IP address.
        """
        try:
            host_info = self.client.admin.command("hostInfo")
            hostname = host_info["system"]["hostname"]
            ip_address = host_info["system"]["currentOpTime"]["ts"]["$timestamp"]["t"]
            return hostname, ip_address
        except Exception as e:
            return f"Unknown (Error: {e})", "Unknown"

    @task
    def ping_mongo(self):
        """
        Simulate a user sending a ping request to MongoDB.
        """
        try:
            hostname, ip_address = self.get_mongo_host_info()

            result = self.db.command("ping")
            print(f"Ping successful: {result}")
            print(f"  Server Hostname: {hostname}")
            print(f"  Server IP: {ip_address}")
            print("-" * 40)
        except Exception as e:
            print(f"Ping failed: {e}")

    @task(3)  # This task will run 3 times more often than others
    def insert_document(self):
        """
        Simulate a user inserting a document into MongoDB.
        """
        try:
            hostname, ip_address = self.get_mongo_host_info()

            result = self.db.test_collection.insert_one({"test": "data"})
            print(f"Document inserted: {result.inserted_id}")
            print(f"  Server Hostname: {hostname}")
            print(f"  Server IP: {ip_address}")
            print("-" * 40)
        except Exception as e:
            print(f"Insert failed: {e}")

    def on_stop(self):
        """
        Called when a simulated user stops executing the tasks.
        """
        self.client.close()
    
    def get_nginx_infos():
        try:
            port_regex = re.compile(r"nginx-service.*\d+:(?P<port>\d+)/TCP")
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