FROM python:3.11-alpine

WORKDIR /app

RUN pip install kubernetes kafka-python 

COPY detection_engine.py .

CMD ["python", "detection_engine.py"]

