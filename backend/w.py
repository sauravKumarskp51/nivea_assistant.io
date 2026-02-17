import json

INPUT = "data\gita_all.json"

with open(INPUT, "r", encoding="utf-8") as f:
    shloks = json.load(f)

for idx, shlok in enumerate(shloks):
    shlok["id"] = idx   # ← ADD UNIQUE ID

with open(INPUT, "w", encoding="utf-8") as f:
    json.dump(shloks, f, ensure_ascii=False, indent=2)

print("✅ IDs added successfully to gita_all.json")
