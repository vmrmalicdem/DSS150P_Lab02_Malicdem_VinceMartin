import requests

BASE_URL = "http://127.0.0.1:8000/api/events"

resp1 = requests.get(BASE_URL, params={"page": 1, "per_page": 10})
data1 = resp1.json()

print("Page 1 response keys:", list(data1.keys()))
print(f"page: {data1.get('page')}")
print(f"per_page: {data1.get('per_page')}")
print(f"total: {data1.get('total')}")
print(f"has_more: {data1.get('has_more')}")
print(f"next_page: {data1.get('next_page')}")
print(f"items in this page: {len(data1.get('items', []))}")

item = data1['items'][0]
print("\nFirst item fields:")
for k, v in item.items():
    print(f"  {k}: {type(v).__name__} = {v}")

resp2 = requests.get(BASE_URL, params={"page": 2, "per_page": 10})
data2 = resp2.json()
print(f"\nPage 2 has_more: {data2.get('has_more')}, items: {len(data2.get('items', []))}")

sample = data1['items'][0]
print("\nKey fields present:")
print("event_id:", sample.get('event_id'))
print("updated_at:", sample.get('updated_at'))
print("amount:", sample.get('amount'))
print("metadata:", sample.get('metadata'))