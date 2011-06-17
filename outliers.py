import numpy
import sys
import math

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

def load_points(point_file):
    places = {}
    count = 0
    for line in file(point_file):
        data = line.strip().split()
        place_id, lon, lat = data if len(data) == 3 else data[1:]
        place_id = int(place_id)
        point = (float(lon), float(lat))
        pts = places.setdefault(place_id, set())
        pts.add(point)
        count += 1
        if count % 1000 == 0:
            print >>sys.stderr, "\rRead %d points in %d places." % (count, len(places)),
    print >>sys.stderr, "\rRead %d points in %d places." % (count, len(places))
    return places

def discard_outliers(places, threshold=MEDIAN_THRESHOLD):
    count = 0
    discarded = 0
    result = {}
    for place_id, pts in places.items():
        count += 1
        print >>sys.stderr, "\rComputing outliers for %d of %d places..." % (count, len(places)),
        median_dist, distances = median_distances(pts)
        keep = [pt for dist, pt in distances if dist < median_dist * threshold]
        discarded += len(pts) - len(keep)
        result[place_id] = keep
    print >>sys.stderr, "%d points discarded." % discarded
    return result

def get_bbox_for_points(places):
    bbox = [180, 90, -180, -90]
    for pid, pts in places.items():
        for pt in pts:
            for i in range(4):
                bbox[i] = min(bbox[i], pt[i%2]) if i<2 else max(bbox[i], pt[i%2])
    return bbox

def main(filename):
    places = load_points(filename)
    places = discard_outliers(places)
    bbox = get_bbox_for_points(places)
    print ",".join(map(str, bbox))
    
if __name__ == "__main__":
    main(sys.argv[1])

