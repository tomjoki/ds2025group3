import time
import json
import os
import base64
from openai import OpenAI
from kafka import KafkaProducer
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class MyHandler(FileSystemEventHandler):
    def __init__(self, producer, topic, openai_client):
        self.producer = producer
        self.topic = topic
        self.openai_client = openai_client
        self.file_content_cache = {}  # Cache to store file content for comparison

    def send_event(self, event_type, file_path, old_content=None, new_content=None, ai_response=None, is_binary=False):
        # Ensure file_path is a string (decode if it's bytes)
        if isinstance(file_path, bytes):
            file_path = file_path.decode('utf-8')

        # Create a message to send to Kafka
        event = {
            "event_type": event_type,
            "file_path": file_path,
            "old_content": old_content if not is_binary else "Binary file (content encoded in Base64)",
            "new_content": new_content if not is_binary else "Binary file (content encoded in Base64)",
            "ai_response": ai_response,
            "is_binary": is_binary,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        # Send the message to Kafka
        self.producer.send(self.topic, value=json.dumps(event).encode('utf-8'))
        print(f"Sent event: {event}")

    def read_file_content(self, file_path):
        # Read file content in binary mode and encode it in Base64
        try:
            with open(file_path, 'rb') as file:
                content = file.read()
                return base64.b64encode(content).decode('utf-8')  # Encode in Base64
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None

    def on_modified(self, event):
        if event.is_directory:
            return  # Skip directories

        file_path = event.src_path
        if os.path.exists(file_path):
            new_content = self.read_file_content(file_path)
            if new_content is None:
                return  # Skip if file cannot be read

            old_content = self.file_content_cache.get(file_path, "")
            if old_content != new_content:
                print(f"File {file_path} has been modified")
                self.file_content_cache[file_path] = new_content

                # Ask OpenAI if the behavior is malicious
                prompt = (
                    f"A file was modified. File path: {file_path}. "
                    f"Old content (Base64): {old_content}. New content (Base64): {new_content}. "
                    "Is this behavior malicious? Respond with only 'yes' or 'no'. "
                    "If you cannot make a decision, default to 'no'."
                )
                ai_response = self.ask_openai(prompt)
                print(f"OpenAI response: {ai_response}")

                # Update the Kafka message with the AI response
                self.send_event("modified", file_path, old_content, new_content, ai_response)

    def on_created(self, event):
        if event.is_directory:
            return  # Skip directories

        file_path = event.src_path
        new_content = self.read_file_content(file_path)
        if new_content is None:
            return  # Skip if file cannot be read

        print(f"File {file_path} has been created")

        # Ask OpenAI if the behavior is malicious
        prompt = (
            f"A new file was created. File path: {file_path}. "
            f"Content (Base64): {new_content}. "
            "Is this behavior malicious? Respond with only 'yes' or 'no'. "
            "If you cannot make a decision, default to 'no'."
        )
        ai_response = self.ask_openai(prompt)
        print(f"OpenAI response: {ai_response}")

        # Update the Kafka message with the AI response
        self.send_event("created", file_path, new_content=new_content, ai_response=ai_response)

    def ask_openai(self, prompt):
        try:
            messages = [
                {"role": "system", "content": "You are a cyber security expert specializing in ransomware detection."},
                {"role": "user", "content": prompt}
            ]

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=10,  # Limit response length
                top_p=1.0,
                frequency_penalty=0.5,
                presence_penalty=0.3
            )

            # Ensure the response is "yes" or "no"
            response_text = response.choices[0].message.content.strip().lower()

            return response_text
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return "error"

def create_producer():
    # Kafka producer configuration
    producer = KafkaProducer(
        bootstrap_servers='kafka-controller-0.kafka-controller-headless.default.svc.cluster.local:9092',  # Replace with your Kafka broker address
        security_protocol='SASL_PLAINTEXT',  # Use SASL_PLAINTEXT for authentication
        sasl_mechanism='PLAIN',  # SASL mechanism (e.g., PLAIN, SCRAM-SHA-256)
        sasl_plain_username='user1',  # Replace with your SASL username
        sasl_plain_password='O5ZT1BIiqN',  # Replace with your SASL password
        value_serializer=lambda v: v  # Skip serialization here, handle it manually
    )
    return producer

if __name__ == "__main__":
    openai_api_key = os.getenv("API-KEY")  # Ensure the environment variable is set
    if not openai_api_key:
        raise ValueError("OpenAI API key not found in environment variables.")

    client = OpenAI(api_key=openai_api_key)

    topic = 'watchdog-events'
    producer = create_producer()
    event_handler = MyHandler(producer, topic, client)
    observer = Observer()
    observer.schedule(event_handler, path="/monitored", recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()