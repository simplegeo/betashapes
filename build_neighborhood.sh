NAME=$1
WOEID=$2
DBNAME=sderle
PLANET_OSM=/mnt/places/belgium.osm.pbf
GRASS_LOCATION=/home/sderle/grass/Global/PERMANENT

if [ ! -r data/photos_$WOEID.txt ]; then
    grep ^$WOEID data/suburbs_wanted.csv | cut -f4 | xargs python geocrawlr.py >data/photos_$WOEID.txt
fi

BBOX=`python outliers.py data/photos_$WOEID.txt`

exit

if [ ! -r data/blocks_$WOEID.json ]; then
    osm2pgsql --latlong --database $DBNAME --input-reader pbf --slim --cache 8192 \
              --style /usr/local/share/osm2pgsql/default.style \
              --bbox $BBOX $PLANET_OSM

    sed -e 's/WOEID/$WOEID/g; s/DBNAME/$DBNAME/g; s/BBOX/$BBOX/g' <<End | grass $GRASS_LOCATION
    v.in.ogr -e --o --v dsn="PG:dbname=DBNAME" layer=osm_ways output=blocks_WOEID \
                        type=boundary spatial=BBOX \
                        where='highway is not null or waterway is not null'
    v.out.ogr in=blocks_WOEID dsn=data/blocks_WOEID.json format=GeoJSON type=area
End
fi

python blockr.py data/names.txt data/blocks_$WOEID.json data/photos_$WOEID.txt > data/$NAME.json
