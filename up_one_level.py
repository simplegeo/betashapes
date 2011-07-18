from shapely.geometry import Polygon, MultiPolygon, shape
from shapely.ops import cascaded_union
import sys, json
import psycopg2
import psycopg2.extras

#read in a GeoJSON featurecollection
#translate those geoms into shapely land
#lookup the parent woe ids for each geom
#cascaded union the geoms to make geoms for the parents. 
#output new GeoJSON featurecollection

town, townwoeid = sys.argv[1:3]

json_file = "data/%s.json" % town
new_json_file = "data/%s_stems.geojson" % town

infh = open(json_file, 'r')
injson = json.loads(infh.next())
nbhds = {}

print >>sys.stderr, "Reading in nbhds."

for feature in injson['features']:
    nbhd = shape(feature['geometry'])
    nbhds[feature['id']] = nbhd

print >>sys.stderr, "Looking up parents."
family = {}

pquery = """select parent_id
        from woe_places
        where woe_id = %s"""

iquery = """select name
            from woe_places
            where woe_id = %s"""

conn_string = "dbname='hood'"
conn = psycopg2.connect(conn_string)
cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

for woeid, nbhd in nbhds.items():
    pq = pquery % woeid
    cursor.execute(pq)
    rs = cursor.fetchone()
    parent = rs["parent_id"]
    if parent == townwoeid:
        print >>sys.stderr, "Nbhd %s has the town for a parent" % woeid
        continue
    if parent not in family:
        iq = iquery % parent
        cursor.execute(iq)
        rs = cursor.fetchone()
        family[parent] = {}
        family[parent]["name"] = rs["name"]
        family[parent]["children"] = [woeid]
    else:
        family[parent]["children"].append(woeid)

print >>sys.stderr, "Merging %s stems" % len(family.keys())
for parent in family.keys():
    family[parent]['geom'] = cascaded_union([nbhds[child] for child in family[parent]['children']])


print >>sys.stderr, "Buffering stems."
for parent, feature in nbhds.items():
    polygon = feature['geom']
    #print >>sys.stderr, "\r%s has shape of type %s" %(place_id, type(polygon))
    if type(polygon) is Polygon:
        polygon = Polygon(polygon.exterior.coords)
    else:
        polygon = MultiPolygon([Polygon(p.exterior.coords)for p in polygon.geoms])
    nbhds[parent]['geom'] = polygon.buffer(0)
 
print >>sys.stderr, "Writing output."
features = []
for place_id, feature in family.items():
    features.append({
        "type": "Feature",
        "id": place_id,
        "geometry": feature['geom'].__geo_interface__,
        "properties": {"woe_id": place_id, "name": feature['name']}
    })

collection = {
    "type": "FeatureCollection",
    "features": features
}

print json.dumps(collection)

