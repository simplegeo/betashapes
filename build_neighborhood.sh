NAME=$1
WOEID=$2
DBNAME=osm # you need to have planet.osm (or some relevant portion) imported
DBPORT=5433
#GRASS_LOCATION=/home/sderle/grass/Global/PERMANENT
GRASS_LOCATION=/mnt/places/melissa/grass/Global/PERMANENT
export GRASS_BATCH_JOB=$GRASS_LOCATION/neighborhood.$$

mkdir -p data
if [ ! -r data/names.txt ]; then
    echo "data/names.txt (tab separated file mapping woe_id to name) is missing"
    exit 1
fi

if [ ! -r data/photos_$WOEID.txt ]; then
    grep ^$WOEID data/suburbs_wanted.csv | cut -f4 | xargs python geocrawlr.py >data/photos_$WOEID.txt
fi

BBOX=`python outliers.py data/photos_$WOEID.txt`

if [ ! -r data/blocks_$WOEID.json ]; then
    pgsql2shp -f tmp$WOEID.shp -p $DBPORT $DBNAME \
     "select osm_id, way from planet_osm_line where way && 'BOX($BBOX)'::box2d and (highway is not null or waterway is not null)" \
     || exit 1

    sed -e "s/WOEID/$WOEID/g" >$GRASS_BATCH_JOB <<End
    v.in.ogr -e --o --v dsn=. layer=tmpWOEID output=blocks_WOEID type=boundary
    v.out.ogr in=blocks_WOEID dsn=data/blocks_WOEID.json format=GeoJSON type=area
End
    chmod +x $GRASS_BATCH_JOB
    grass -text $GRASS_LOCATION
    rm -f $GRASS_BATCH_JOB
    rm tmp$WOEID.*
fi

python blockr.py data/names.txt data/blocks_$WOEID.json data/photos_$WOEID.txt > data/$NAME.json
