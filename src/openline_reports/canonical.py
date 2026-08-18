
import json, hashlib

def canonical_json_bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def sha256_obj(obj):
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()
