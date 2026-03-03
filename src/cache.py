import json
import redis
import hashlib

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

def get_cache(key):
    data = r.get(key)
    if data:
        return json.loads(data)
    return None

def set_cache(key, value, ttl=3600):
    r.setex(key, ttl, json.dumps(value))

def generate_cache_key(query, files):
    hasher = hashlib.sha256()

    # Hash query
    hasher.update(query.encode("utf-8"))

    # Hash each file content
    for file in files:
        content = file.read()
        hasher.update(content)
        file.seek(0)  # VERY IMPORTANT → reset pointer

    return hasher.hexdigest()