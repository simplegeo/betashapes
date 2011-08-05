#!/usr/bin/env python

from mapnik import *
import sys, random

width, height = 2048, 2048
rgbs = ["80", "a2", "ab"]
base = "data/results"
city = sys.argv[1]

woe_id = None
# intl_cities.txt is a tab-separated file mapping woe_id -> name
for line in file(base+"/intl_cities.txt"):
    woe_id, name = line.strip().split(None,1)
    if city == name: break
if woe_id is None: raise Exception("Couldn't find the city '%s'" % city)

m = Map(width, height, "+proj=latlong +datum=WGS84")
m.background = Color('white')

if city == "Tokyo":
    register_fonts("/usr/share/fonts/truetype/takao")
    font = "TakaoMincho Regular"
else:
    font = "DejaVu Sans Bold"

def append_style(name, *symbols):
    s = Style()
    r = Rule()
    for symbol in symbols:
        r.symbols.append(symbol)
    s.rules.append(r)
    m.append_style(name,s)

random.shuffle(rgbs)
fill = Color('#%s%s%s' % tuple(rgbs))
hood = Layer('hood', "+proj=latlong +datum=WGS84")
hood.datasource = Ogr(base=base,file=city+".json",layer="OGRGeoJSON")
append_style("hood", PolygonSymbolizer(fill))
hood.styles.append("hood")
m.layers.append(hood)

blocks = Layer('blocks',"+proj=latlong +datum=WGS84")
blocks.datasource = Ogr(base=base,file="blocks_"+woe_id+".json",layer='OGRGeoJSON')
append_style('blocks', LineSymbolizer(Color('rgb(50%,50%,50%)'),1.0))
blocks.styles.append('blocks')
m.layers.append(blocks)

bounds = Layer('bounds', "+proj=latlong +datum=WGS84")
bounds.datasource = Ogr(base=base,file=city+".json",layer="OGRGeoJSON")
append_style("bounds", LineSymbolizer(Color('#222222'), 2.0))
text = TextSymbolizer("name", font, 12, Color("black"))
text.allow_overlap = False
text.avoid_edges = True
text.wrap_width = 15
halo_fill = [min(x+32, 255) for x in (fill.r, fill.g, fill.b)]
text.halo_fill = Color(*halo_fill)
text.halo_radius = 1
append_style("bounds_label", text)
#       <TextSymbolizer name="NAME" face_name="DejaVu Sans Bold" size="7" fill="black" halo_fill= "#DFDBE3" halo_radius="1" wrap_width="20" spacing="5" allow_overlap="false" avoid_edges="false" min_distance="10"/>
bounds.styles.append("bounds")
bounds.styles.append("bounds_label")
m.layers.append(bounds)

m.zoom_to_box(hood.envelope())
render_to_file(m,city+'.png', 'png')
