import Flickr.API
import os, os.path, json, sys
import xml.etree.ElementTree

key, secret = os.environ["FLICKR_KEY"], os.environ["FLICKR_SECRET"]

# flickr.test.echo:
api = Flickr.API.API(key, secret)
token = None

# flickr.auth.getFrob:
frob_request = Flickr.API.Request(method='flickr.auth.getFrob')
frob_rsp = api.execute_request(frob_request)
if frob_rsp.code == 200:
    frob_rsp_et = xml.etree.ElementTree.parse(frob_rsp)
    if frob_rsp_et.getroot().get('stat') == 'ok':
        frob = frob_rsp_et.findtext('frob')

# get the desktop authentication url
auth_url = api.get_authurl('write', frob=frob)

# ask the user to authorize your app now using that url
print "auth me:  %s" % (auth_url,)
input = raw_input("done [y]: ")
if input.lower() not in ('', 'y', 'yes'):
    sys.exit()

# flickr.auth.getToken:
token_rsp = api.execute_request(Flickr.API.Request(method='flickr.auth.getToken', frob=frob, format='json', nojsoncallback=1))
if token_rsp.code == 200:
    token_rsp_json = json.load(token_rsp)
    if token_rsp_json['stat'] == 'ok':
        token = str(token_rsp_json['auth']['token']['_content'])

for filename in sys.argv[1:]:
    photo = file(filename, "rb")
    filename = os.path.basename(filename)
    #upload_response = api.execute_upload(filename=filename, args={'auth_token':token, 'title':title, 'photo':photo})

    upload_request = Flickr.API.Request("http://api.flickr.com/services/upload", auth_token=token, title=filename, photo=photo)
    upload_response = api.execute_request(upload_request, sign=True, encode=Flickr.API.encode_multipart_formdata)
    print upload_response
