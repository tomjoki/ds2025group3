# Distributed Systems 2025, Group 3

This repository was created to store codes related to our project implementation for the Distributed Systems course. The project idea is to create a distributed ransomware detection & file recovery system. Each part of the system can be found in the respective folders.

## Alpine
- `Alpine deployment yamls`
    - Contains the deplyoment `.yaml` files for the Alpine/Alpine-Watchdog deployments

- `aline-hpa.yaml`
    - Contains the Horizontal Pod Autoscaler (HPA) `.yaml` file

## DetectionEngine
- `detection_engine.py`
    - Contains the logic for the detection engine

- `Dockerfile`
    - Contains the docker file for the detection engine, runs `detection_engine.py` when the Docker container is deployed

- `requirements.txt`
    - Requirements for the detection engine

## nginx
- `load_balancing_test_without_locust.py`
    - Contains the script to test the load balancer in action
- `new_locust_load.py`
    - Contains the Locust script for testing the load balancer, problems with displaying data so we focused on testing without Locust
- `mongo service & deployment yamls`
    - Contains the `.yaml` files for the reverse proxy/load balancer implementation
    - Can be used by running `kubectl apply -f .` in the `nginx` directory
- `nginx.conf`
    - Configuration file

## watchdog
- `monitor.py`
    - Contains the Watchdog monitor that has been enchanced with OpenAI's `gpt-3.5-turbo` model to distinguish between malicious and non-malicious file changes

## Milestone 1 *(NOT USED IN THE END PRODUCT)*
- Contains a local implementation of the initial system utilizing gRPC and Kafka.