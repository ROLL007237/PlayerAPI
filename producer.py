from kafka import KafkaProducer
import json, time

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

for i in range(5):
    msg = {"index": i, "text": f"Hello from message {i}"}
    producer.send("my-topic", msg)
    print(f"Sent: {msg}")
    time.sleep(1)

producer.flush()
producer.close()
