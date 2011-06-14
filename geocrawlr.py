import Flickr.API
import json, time, sys

FLICKR_KEY    = ""
FLICKR_SECRET = ""

START_PAGE = 1
END_PAGE = 10

api = Flickr.API.API(FLICKR_KEY, FLICKR_SECRET)

for woe_id in map(int, sys.argv[1:]):
    print >>sys.stderr, "WOEID:", woe_id
    page = total_pages = START_PAGE

    while page <= total_pages:
        print >>sys.stderr, ">>> Reading %d of %d... " % (page, total_pages),
        request = Flickr.API.Request(
                    method="flickr.photos.search",
                    format="json", 
                    nojsoncallback=1,
                    #sort="interestingness-desc",
                    page=page,
                    woe_id=woe_id,
                    extras="geo",
                    min_date_taken="2007-01-01 00:00:00"
                    )
        start = time.time()
        response = None
        while response is None:
            try:
                response = api.execute_request(request).read()
            except Exception, e:
                print >>sys.stderr, "Retrying due to:", e
        print >>sys.stderr, "%.1fs elapsed." % (time.time()-start)
        try:
            result = json.loads(response)["photos"]
            for item in result["photo"]:
                try:
                    print "\t".join(str(item[k]) for k in ("id","woeid","longitude","latitude"))
                except Exception, e:
                    print >>sys.stderr, e
            total_pages = min(int(result["pages"]), END_PAGE)
            #time.sleep(1.0)
        except:
            pass
        page += 1
