from OsmApi import OsmApi
import sys, geojson

wanted_tags = ("highway", "waterway")

osm = OsmApi()

def get_osm_ways(bbox):
    nodes = {}
    ways = {}
    for item in osm.Map(*bbox):
        data = item["data"]
        if item["type"] == "node":
            nodes[int(data["id"])] = map(float, (data["lon"],data["lat"]))
        elif item["type"] == "way" and any(t for t in wanted_tags if t in data["tag"]):
            ways[int(data["id"])] = ( dict((k, data["tag"].get(k, "")) for k in wanted_tags), data["nd"] )
    features = []
    for way_id, (tags, node_ids) in ways.items():
        feature = geojson.Feature()
        feature.geometry = geojson.LineString(coordinates=(nodes[ref] for ref in node_ids))
        feature.properties = tags
        feature.id = way_id
        features.append(feature)
    return features

for obj in get_osm_ways(map(float, sys.argv[1].split(","))):
    print obj.to_dict()
