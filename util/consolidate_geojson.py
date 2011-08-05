import json, sys, os.path

woe = {}
for line in file(sys.argv[1]):
    woe_id, name = line.strip().split(None,1)
    name = name.split("_")[0]
    woe[name] = int(woe_id)

features = []
for fname in sys.argv[2:]:
    print >>sys.stderr, "-", fname
    name = os.path.basename(fname).split(".")[0].split("_")[0]
    collection = json.load(file(fname))
    for record in collection["features"]:
        record["properties"]["city"] = name
        record["properties"]["parent_id"] = woe[name]
        record["properties"]["woe_type"] = "Suburb" if "_" not in fname else "LocalAdmin"
        features.append(record)

json.dump(
        { "type": "FeatureCollection", "features": features },
        sys.stdout)

