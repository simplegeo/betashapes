import json, sys, os.path

woe = {}
for line in file(sys.argv[1]):
    woe_id, name = line.strip().split(None,1)
    woe[name] = int(woe_id)

features = []
for fname in sys.argv[2:]:
    name = os.path.basename(fname).split(".")[0]
    collection = json.loads(fname)
    for record in collection["features"]:
        record["properties"]["city"] = name
        record["properties"]["parent_id"] = woe[name]
    features.append(record)

json.dump(sys.stdout,
        { "type": "FeatureCollection", "features": features })

