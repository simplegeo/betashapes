from shapely.geometry import Point, MultiPoint, Polygon, MultiPolygon, asShape
from shapely.ops import cascaded_union, polygonize
from shapely.prepared import prep
from rtree import Rtree
import sys, random, json, numpy, math, pickle, os, geojson

SAMPLE_SIZE = 20
SCALE_FACTOR = 111111.0
MEDIAN_THRESHOLD = 5.0

median_distance_cache = {}
def median_distances(pts, aggregate=numpy.median):
    key = tuple(sorted(pts))
    if key in median_distance_cache: return median_distance_cache[key]
    median = (numpy.median([pt[0] for pt in pts]),
              numpy.median([pt[1] for pt in pts]))
    distances = []
    for pt in pts:
        dist = math.sqrt(((median[0]-pt[0])*math.cos(median[1]*math.pi/180.0))**2+(median[1]-pt[1])**2)
        distances.append((dist, pt))

    median_dist = aggregate([dist for dist, pt in distances])
    median_distance_cache[key] = (median_dist, distances)
    return (median_dist, distances)

def mean_distances(pts):
    return median_distances(pts, numpy.mean)

name_file, line_file, point_file = sys.argv[1:4]

places = {}
names = {}
blocks = {}
if os.path.exists(point_file + '.cache'):
    print >>sys.stderr, "Reading from %s cache..." % point_file
    names, blocks, places = pickle.load(file(point_file + ".cache"))
    blocks = map(asShape, blocks)
else:
    all_names = {}
    count = 0
    for line in file(name_file):
        place_id, name = line.strip().split(None, 1)
        all_names[int(place_id)] = name
        count += 1
        if count % 1000 == 0:
            print >>sys.stderr, "\rRead %d names from %s." % (count, name_file),
    print >>sys.stderr, "\rRead %d names from %s." % (count, name_file)

    count = 0
    for line in file(point_file):
        place_id, lon, lat = line.strip().split()
        place_id = int(place_id)
        names[place_id] = all_names.get(place_id, "")
        point = (float(lon), float(lat))
        pts = places.setdefault(place_id, set())
        pts.add(point)
        count += 1
        if count % 1000 == 0:
            print >>sys.stderr, "\rRead %d points in %d places." % (count, len(places)),
    print >>sys.stderr, "\rRead %d points in %d places." % (count, len(places))

    count = 0
    discarded = 0
    for place_id, pts in places.items():
        count += 1
        print >>sys.stderr, "\rComputing outliers for %d of %d places..." % (count, len(places)),
        median_dist, distances = median_distances(pts)
        keep = [pt for dist, pt in distances if dist < median_dist * MEDIAN_THRESHOLD]
        discarded += len(pts) - len(keep)
        places[place_id] = keep

    print >>sys.stderr, "%d points discarded." % discarded

    lines = []
    do_polygonize = False
    print >>sys.stderr, "Reading lines from %s..." % line_file,
    for feature in geojson.loads(file(line_file).read()):
        if feature.geometry.type in ('LineString', 'MultiLineString'):
            do_polygonize = True
        lines.append(asShape(feature.geometry.to_dict()))
    print >>sys.stderr, "%d lines read." % len(lines)
    if do_polygonize:
        print >>sys.stderr, "Polygonizing %d lines..." % (len(lines)),
        blocks = [poly.__geo_interface__ for poly in  polygonize(lines)]
        print >>sys.stderr, "%d blocks formed." % len(blocks)
    else:
        blocks = [poly.__geo_interface__ for poly in lines]

if not os.path.exists(point_file + '.cache'):
    print >>sys.stderr, "Caching points, blocks, and names ..."
    pickle.dump((names, blocks, places), file(point_file + ".cache", "w"), -1)
    blocks = map(asShape, blocks)

points = []
place_list = set()
count = 0
for place_id, pts in places.items():
    count += 1
    print >>sys.stderr, "\rPreparing %d of %d places..." % (count, len(places)),
    for pt in pts:
        place_list.add((len(points), pt+pt, None))
        points.append((place_id, Point(pt)))
print >>sys.stderr, "Indexing...",
index = Rtree(place_list)
print >>sys.stderr, "Done."

def score_block(polygon):
    centroid = polygon.centroid
    score = {}
    for item in index.nearest((centroid.x, centroid.y), SAMPLE_SIZE):
        place_id, point = points[item]
        score.setdefault(place_id, 0.0)
        score[place_id] += 1.0 / math.sqrt(max(polygon.distance(point)*SCALE_FACTOR, 1.0))
    return list(reversed(sorted((sc, place_id) for place_id, sc in score.items())))

count = 0
assigned_blocks = {}
for polygon in blocks:
    count += 1
    print >>sys.stderr, "\rScoring %d of %d blocks..." % (count, len(blocks)),
    if polygon.is_empty: continue
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    if not polygon.is_valid:
        continue
    scores = score_block(polygon)
    winner = scores[0][1]
    assigned_blocks.setdefault(winner, [])
    assigned_blocks[winner].append(polygon)
print >>sys.stderr, "Done."

polygons = {}
count = 0
for place_id in places.keys():
    count += 1
    print >>sys.stderr, "\rMerging %d of %d boundaries..." % (count, len(places)),
    if place_id not in assigned_blocks: continue
    polygons[place_id] = cascaded_union(assigned_blocks[place_id])
print >>sys.stderr, "Done."

count = 0
orphans = []
for place_id, multipolygon in polygons.items():
    count += 1
    print >>sys.stderr, "\rRemoving %d orphans from %d of %d polygons..." % (len(orphans), count, len(polygons)),
    if type(multipolygon) is not MultiPolygon: continue
    polygon_count = [0] * len(multipolygon)
    for i, polygon in enumerate(multipolygon.geoms):
        prepared = prep(polygon)
        for item in index.intersection(polygon.bounds):
            item_id, point = points[item]
            if item_id == place_id and prepared.intersects(point):
                polygon_count[i] += 1
    winner = max((c, i) for (i, c) in enumerate(polygon_count))[1]
    polygons[place_id] = multipolygon.geoms[winner]
    orphans.extend((place_id, p) for i, p in enumerate(multipolygon.geoms) if i != winner)
print >>sys.stderr, "Done."

count = 0
total = len(orphans)
retries = 0
unassigned = None
while orphans:
    unassigned = []
    for origin_id, orphan in orphans:
        count += 1
        changed = False
        print >>sys.stderr, "\rReassigning %d of %d orphans..." % (count-retries, total),
        for score, place_id in score_block(orphan):
            if place_id not in polygons:
                # Turns out we just wind up assigning tiny, inappropriate places
                #polygons[place_id] = orphan
                #changed = True
                continue
            elif place_id != origin_id and orphan.intersects(polygons[place_id]):
                polygons[place_id] = polygons[place_id].union(orphan)
                changed = True
            if changed:
                break
        if not changed:
            unassigned.append((origin_id, orphan))
            retries += 1
    if len(unassigned) == len(orphans):
        # give up
        break
    orphans = unassigned
print >>sys.stderr, "%d retried, %d unassigned." % (retries, len(unassigned))

print >>sys.stderr, "Returning remaining orphans to original places."
for origin_id, orphan in orphans:
    if orphan.intersects(polygons[origin_id]):
        polygons[origin_id] = polygons[origin_id].union(orphan)

print >>sys.stderr, "Buffering polygons."
for place_id, polygon in polygons.items():
    if type(polygon) is Polygon:
        polygon = Polygon(polygon.exterior.coords)
    else:
        polygon = MultiPolygon([Polygon(p.exterior.coords)for p in polygon.geoms])
    polygons[place_id] = polygon.buffer(0)
 
print >>sys.stderr, "Writing output."
features = []
for place_id, poly in polygons.items():
    features.append({
        "type": "Feature",
        "id": place_id,
        "geometry": poly.__geo_interface__,
        "properties": {"woe_id": place_id, "name": names.get(place_id, "")}
    })

collection = {
    "type": "FeatureCollection",
    "features": features
}

print json.dumps(collection)

