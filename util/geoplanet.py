
import urllib, json, sys

APPID = os.environ["YAHOO_APPID"]
url = 'http://where.yahooapis.com/v1/places.q(%s)?select=long&format=json&appid='

for line in sys.stdin:
    query = url % line.strip()
    result = urllib.urlopen(query).read()
    result = json.loads(result)
    place = result['places']['place'][0]
    print place['woeid'], "\t", place["name"]
