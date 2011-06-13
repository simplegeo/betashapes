from shapely.geometry import Point, MultiPoint, Polygon, MultiPolygon
from shapely.ops import cascaded_union, polygonize
from shapely.prepared import prep
from rtree import Rtree
import sys, random, json, numpy, math, pickle, os

SAMPLE_ITERATIONS = 200
SAMPLE_SIZE = 5
MEDIAN_THRESHOLD = 5.0

median_distance_cache = {}
def median_distances(points, aggregate=numpy.median):
    key = tuple(sorted(points))
    if key in median_distance_cache: return median_distance_cache[key]
    median = Point((numpy.median([pt.x for pt in points]),
                    numpy.median([pt.y for pt in points])))
    distances = []
    for pt in points:
        dist = math.sqrt(((median.x-pt.x)*math.cos(median.y*math.pi/180.0))**2+(median.y-pt.y)**2)
        distances.append((dist, pt))

    median_dist = aggregate([dist for dist, pt in distances])
    median_distance_cache[key] = (median_dist, distances)
    return (median_dist, distances)

def mean_distances(points):
    return median_distances(points, numpy.mean)

names = {}
if len(sys.argv) > 1:
    for line in file(sys.argv[1]):
        place_id, name = line.strip().split(None, 1)
        names[int(place_id)] = name

places = {}
if False: #os.path.exists(sys.argv[2] + '.cache'):
    print >>sys.stderr, "Reading from file cache..."
    places = pickle.load(file(sys.argv[2] + ".cache"))
else:
    count = 0
    for line in file(sys.argv[2]):
        place_id, lon, lat = line.strip().split()
        point = Point(float(lon), float(lat))
        pts = places.setdefault(int(place_id), set())
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

"""
if not os.path.exists(sys.argv[2] + '.cache'):
    print >>sys.stderr, "Caching points..."
    pickle.dump(places, file(sys.argv[2] + ".cache", "w"), -1)
"""

print >>sys.stderr, "Indexing..."
place_list = set()
for place_id, pts in places.items():
    for point in pts:
        place_list.add((int(place_id), point.bounds, None))
index = Rtree(place_list)

"""

REASSIGNMENT_PASSES = 10
iterations = 0
count = 0
queue = places.keys() + [None]
while len(queue) > 1:
    place_id = queue.pop(0)
    if place_id is None:
        count = 0
        iterations += 1
        queue.append(None)
        place_id = queue.pop(0)
    if not places[place_id]:
        del places[place_id]
        continue
    pts = places[place_id]
    count += 1
    print >>sys.stderr, "\rIteration #%d of reassignment: %d of %d places..." % (iterations, count, len(queue)),
    if iterations > len(pts) / 10.0: continue
    old_source_mean, distances = mean_distances(pts)
    _, outlier = max(distances)
    best = (None, 0.0)
    print >>sys.stderr, ""
    for nearest in index.nearest(outlier.bounds, 3, objects=True):
        #print >>sys.stderr, "    -> %s (%d) versus %s (%d)" % (outlier, place_id, Point(nearest.bbox[0:2]), nearest.id)
        if nearest.id == place_id: continue
        old_target_mean, _ = mean_distances(places[nearest.id])
        source = list(pts)
        source.remove(outlier)
        target = list(places[nearest.id]) + [outlier]
        #print >>sys.stderr, "      source: new=%d items, old=%d items" % (len(source), len(pts))
        new_source_mean, _ = mean_distances(source)
        new_target_mean, _ = mean_distances(target)
        print >>sys.stderr, "      source mean: new=%.6f, old=%.6f" % (old_source_mean, new_source_mean)
        print >>sys.stderr, "      target mean: new=%.6f, old=%.6f" % (old_target_mean, new_target_mean)
        if new_source_mean < old_source_mean and \
           new_target_mean < old_target_mean:
            improvement = (old_source_mean - new_source_mean) \
                        + (old_target_mean - new_target_mean)
            if improvement > best[1]:
                best = (nearest.id, improvement)
    if best[1] > 0:
        pts.remove(outlier)
        places[best[0]].append(outlier)
        queue.append(place_id)
        print >>sys.stderr, "%s moved from %d to %d." % (outlier, place_id, best[0])

print >>sys.stderr, "Done."

"""

sample_hulls = {}
count = 0
for place_id, pts in places.items():
    hulls = []
    if len(pts) < 3:
        print >>sys.stderr, "\n    ... discarding place #%d" % place_id
        continue
    for i in range(min(pts,SAMPLE_ITERATIONS)):
        multipoint = MultiPoint(random.sample(pts, min(SAMPLE_SIZE, len(pts))))
        hull = multipoint.convex_hull
        if not hull.is_empty and hull.is_simple and not isinstance(hull,Point): hulls.append(hull)
    try:
        sample_hulls[place_id] = cascaded_union(hulls)
    except:
        print >>sys.stderrm, hulls
        sys.exit()
    if hasattr(sample_hulls[place_id], "geoms"):
        sample_hulls[place_id] = cascaded_union([hull for hull in sample_hulls[place_id] if type(hull) is Polygon])
    count += SAMPLE_ITERATIONS
    print >>sys.stderr, "\rComputing %d of %d hulls..." % (count, (len(places) * SAMPLE_ITERATIONS)),

print >>sys.stderr, "\nCombining hull boundaries..."
boundaries = cascaded_union([hull.boundary for hull in sample_hulls.values()])

print >>sys.stderr, "Polygonizing %d boundaries..." % len(boundaries)
rings = list(polygonize(boundaries))

for i, ring in enumerate(rings):
    print >>sys.stderr, "\rBuffering %d of %d polygons..." % (i, len(rings)),
    rings[i] = ring.buffer(0.001).buffer(-0.001)
print >>sys.stderr, "Done."

polygons = {}
count = 0
for polygon in rings:
    if polygon.is_empty: continue
    place_count = dict((place_id, 0) for place_id in places)
    prepared = prep(polygon)
    #for item in index.intersection(polygon.bounds, objects=True):
    for item in index.intersection(polygon.bounds, objects=True):
        if prepared.intersects(Point(item.bbox[0:2])):
            place_count[item.id] += 1
    pt_count, place_id = max((c, i) for (i, c) in place_count.items())
    polys = polygons.setdefault(place_id, [])
    polys.append(polygon)
    count += 1
    print >>sys.stderr, "\rAssigning %d of %d polygons..." % (count,len(rings)),
print >>sys.stderr, "Done."

count = 0
for place_id, polys in polygons.items():
    polygons[place_id] = cascaded_union(polys)
    count += 1
    print >>sys.stderr, "\rUnifying %d of %d polygons..." % (count,len(polygons)),
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
        for item in index.intersection(polygon.bounds, objects=True):
            if item.id == place_id and prepared.intersects(Point(item.bbox[0:2])):
                polygon_count[i] += 1
    winner = max((c, i) for (i, c) in enumerate(polygon_count))[1]
    polygons[place_id] = multipolygon.geoms[winner]
    orphans.extend(p for i, p in enumerate(multipolygon.geoms) if i != winner)
print >>sys.stderr, "Done."

count = 0
changed = True
while changed and orphans:
    orphan = orphans.pop(0)
    changed = False
    count += 1
    print >>sys.stderr, "\rReassigning %d of %d orphans..." % (count, len(orphans)),
    place_count = dict((place_id, 0) for place_id in places)
    total_count = 0.0
    prepared = prep(orphan)
    for item in index.intersection(orphan.bounds, objects=True):
        if prepared.intersects(Point(item.bbox[0:2])): 
                if filter(prepared.intersects, places[item.id]):
                    place_count[item.id] += 1
                    total_count += 1
    for place_id, ct in place_count.items():
        if total_count > 0  and float(ct)/total_count > 1/3.0:
            polygons[place_id] = polygons[place_id].union(orphan)
            changed = True
    if not changed:
        orphans.append(orphan)

print >>sys.stderr, "Done."
 
print >>sys.stderr, "\nWriting output."
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

