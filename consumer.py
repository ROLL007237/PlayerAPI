from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    "my-topic",
    bootstrap_servers="localhost:9092",
    auto_offset_reset="earliest",       # read from the beginning
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
)

print("Waiting for messages...")
for msg in consumer:
    print(f"Received: {msg.value}")
