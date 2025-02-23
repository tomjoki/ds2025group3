import json
import os 
from kafka import KafkaConsumer
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
import time

config.load_incluster_config()
KAFKA_BROKER = os.getenv("KAFKA_BROKER", 'kafka-controller-0.kafka-controller-headless.default.svc.cluster.local:9092')
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", 'watchdog-events')
KUBE_NAMESPACE = os.getenv("KUBE_NAMESPACE", 'default')
API_KEY = os.getenv("API-KEY")

def create_consumer():
    
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=[KAFKA_BROKER],
        security_protocol='SASL_PLAINTEXT',
        sasl_mechanism='PLAIN',
        sasl_plain_username='user1',
        sasl_plain_password='O5ZT1BIiqN',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')))
    return consumer

def create_simple_alpine():

    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "alpine-replica",
            "namespace": "default",
        },
        "spec": {
            "containers": [
                {
                    "image": "alpine:3.2",
                    "command": ["/bin/sh", "-c", "sleep 60m"],
                    "imagePullPolicy": "IfNotPresent",
                    "name": "alpine",
                }
            ],
            "restartPolicy": "Always",
        }
    }
    v1 = client.CoreV1Api()
    try:
        v1.create_namespaced_pod(namespace="default", body=manifest)
        print("Pod alpine_replica created in namespace default")
    except Exception as e:
        print(f"Failed to create pod: {e}")

def create_pod():

    if not API_KEY:
        raise ValueError

    manifest = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "alpine-watchdog",
            "labels": {
                "run": "alpine-watchdog"
            }
        },
        "spec": {
            "replicas": 1,
            "selector": {
                "matchLabels": {
                    "run": "alpine-watchdog"
                }
            },
            "strategy": {},
            "template": {
                "metadata": {
                    "creationTimestamp": None,
                    "labels": {
                        "run": "alpine-watchdog"
                    }
                },
                "spec": {
                    "containers": [
                        {
                            "name": "alpine",
                            "image": "alpine:latest",
                            "command": [
                                "/bin/sh",
                                "-c",
                                "echo 'Hello there Watchdog' > /shared/log.txt && sleep 60m"
                            ],
                            "imagePullPolicy": "IfNotPresent",
                            "resources": {
                                "requests": {
                                    "memory": "64Mi",
                                    "cpu": "100m"
                                },
                                "limits": {
                                    "memory": "128Mi",
                                    "cpu": "250m"
                                }
                            },
                            "volumeMounts": [
                                {
                                    "name": "shared-volume",
                                    "mountPath": "/shared"
                                }
                            ]
                        },
                        {
                            "name": "watchdog",
                            "image": "tomjoki/wdog-monitor",
                            "env": [
                                {
                                    "name": "KAFKA_BROKER",
                                    "value": "kafka-controller-0.kafka-controller-headless.default.svc.cluster.local:9092"
                                },
                                {
                                    "name": "API-KEY",
                                    "value": API_KEY
                                }
                            ],
                            "resources": {
                                "requests": {
                                    "memory": "64Mi",
                                    "cpu": "100m"
                                },
                                "limits": {
                                    "memory": "128Mi",
                                    "cpu": "250m"
                                }
                            },
                            "volumeMounts": [
                                {
                                    "name": "shared-volume",
                                    "mountPath": "/monitored"
                                }
                            ]
                        }
                    ],
                    "volumes": [
                        {
                            "name": "shared-volume",
                            "emptyDir": {}
                        }
                    ]
                }
            }
        }
    }

    service_manifest = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": "alpine-watchdog-service"
        },
        "spec": {
            "selector": {
                "run": "alpine"
            },
            "ports": [
                {
                    "protocol": "TCP",
                    "port": 80,
                    "targetPort": 8080
                }
            ],
            "type": "ClusterIP"
        }
    }
    apps_v1_api = client.AppsV1Api()
    try:
        apps_v1_api.create_namespaced_deployment(
            namespace="default",
            body=manifest,
        )
        print("Deployment 'alpine-watchdog' created successfully.")
    except Exception as e:
        print(f"Failed to create Deployment: {e}")
        
    core_v1_api = client.CoreV1Api()
    try:
        core_v1_api.create_namespaced_service(
            namespace="default",
            body=service_manifest,
        )
        print("Service 'alpine-watchdog-service' created successfully.")
    except Exception as e:
        print(f"Failed to create Service: {e}")

def delete_deployment():
    apps_v1_api = client.AppsV1Api()
    try:
        apps_v1_api.delete_namespaced_deployment(name="alpine-watchdog", namespace="default")
    except ApiException as ae:
        if ae.status == 404:
            print("Deployment not found")
        else:
            print("Error deleting deployment")

def wait_for_deletion():
    apps_v1_api = client.AppsV1Api()
    while True:
        try:
            apps_v1_api.read_namespaced_deployment(name="alpine-watchdog", namespace="default")
            print("waiting for deletion")
            time.sleep(2)
        except ApiException as ae:
            if ae.status == 404:
                print("Deployment deleted successfully")
                return
            else:
                print(f"Couldnt delete the deployment. Status: {ae}")
                return

def main():
    consumer = create_consumer()
    for message in consumer:
        event = message.value
        if event.get("ai_response") == "yes":
            try:
                print("Received a positive hit - shutting the pod down")
                delete_deployment()
                wait_for_deletion()
                create_pod()
            except ValueError:
                print("Getting API key failed")

if __name__ == "__main__":
    main()