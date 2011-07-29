from OsmApi import OsmApi
from outliers import load_points, discard_outliers, get_bbox_for_points
import sys, geojson, time

DEFAULT_TAGS = ("highway", "waterway")

osm = OsmApi() #api="http://open.mapquestapi.com/xapi"

def get_osm_ways(bbox, wanted_tags=DEFAULT_TAGS):
    nodes = {}
    left, bottom, right, top = bbox
    step = .025
    scale = 100000.0
    count = 0
    iterations = int(((right-left)/step+1)*((top-bottom)/step+1))
    for x in range(int(left*scale), int(right*scale), int(step*scale)):
        for y in range(int(bottom*scale), int(top*scale), int(step*scale)):
            count += 1
            ways = {}
            request = (x/scale, y/scale, min(x/scale+step,right), min(y/scale+step, top))
            start= time.time()
            print >>sys.stderr, "\rRequesting %.4f,%.4f,%.4f,%.4f from OSM (%d of %d)..." % (request+(count, iterations)),
            for item in osm.Map(*request):
                data = item["data"]
                if item["type"] == "node":
                    nodes[int(data["id"])] = map(float, (data["lon"],data["lat"]))
                elif item["type"] == "way" and any(t for t in wanted_tags if t in data["tag"]):
                    ways[int(data["id"])] = ( dict((k, data["tag"].get(k, "")) for k in wanted_tags), data["nd"] )
            print >>sys.stderr, "%d nodes, %d ways found (%.2f elapsed)" % (len(nodes),len(ways),time.time()-start)
            for way_id, (tags, node_ids) in ways.items():
                feature = geojson.Feature()
                feature.geometry = geojson.LineString(coordinates=(nodes[ref] for ref in node_ids if ref in nodes))
                feature.properties = tags
                feature.id = way_id
                yield feature
            time.sleep(0.5)

def main(points_file):
    places = load_points(points_file)
    #random_place = dict([places.popitem()])
    random_place = discard_outliers(places)
    bbox = get_bbox_for_points(places)
    for obj in get_osm_ways(bbox):
        print obj.to_dict()

if __name__ == "__main__":
    main(sys.argv[1])

