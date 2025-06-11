import requests, os, bs4
import logging, sys, threading
import http3
from datetime import datetime
import ssl

# Fixes the issue with the socket connection
create_default_context_orig = ssl.create_default_context
def cdc(*args, **kwargs):
    kwargs["purpose"] = ssl.Purpose.SERVER_AUTH
    return create_default_context_orig(*args, **kwargs)
ssl.create_default_context = cdc



# logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
# note! Fingerpori 2018-05-02 --> ~2018-06-01 images missing from hs.fi

# setup -->
StopAt = "2025-02-19" #None   # crawl back to 'YYYY-MM-DD' or None (if you want all)
# <-- setup

host_is = {'BaseUrl': 'https://www.is.fi', 'ShortName': 'is'}
host_hs = {'BaseUrl': 'https://www.hs.fi', 'ShortName': 'hs'}
sanomaComicUrl = 'images.sanoma-sndp.fi'

# nemi = 			{'SaveFolder': 'Nemi', 'Hostfolder': 'nemi', 'fileextension': '.jpg', 'host': host_is } # removed from is.fi 20190104
# kamalaluonto = 	{'SaveFolder': 'KamalaLuonto', 'Hostfolder': 'kamalaluonto', 'fileextension': '.jpg', 'host': host_is }
# dilbert = 		{'SaveFolder': 'Dilbert', 'Hostfolder': 'dilbert', 'fileextension': '.gif', 'host': host_is }
# karlsson = 		{'SaveFolder': 'Karlsson', 'Hostfolder': 'karlsson', 'fileextension': '.jpg', 'host': host_hs }
# jaatavaspede = 	{'SaveFolder': 'JaatavaSpede', 'Hostfolder': 'jaatavaspede', 'fileextension': '.jpg', 'host': host_hs }
# wumo = 			{'SaveFolder': 'Wumo', 'Hostfolder': 'wumo', 'fileextension': '.jpg', 'host': host_hs }
# anonyymitElaimet = {'SaveFolder': 'anonyymitElaimet', 'Hostfolder': 'nyt/anonyymitelaimet', 'fileextension': '.jpg', 'host': host_hs }
jarla = 		{'SaveFolder': 'Jarla', 'Hostfolder': 'sarjakuvat/jarla', 'fileextension': '.jpg', 'host': host_hs }
fingerpori = 	{'SaveFolder': 'Fingerpori', 'Hostfolder': 'fingerpori', 'fileextension': '.jpg', 'host': host_hs }
viivijawagner = {'SaveFolder': 'ViiviJaWagner', 'Hostfolder': 'viivijawagner', 'fileextension': '.jpg', 'host': host_hs }
fokit = 		{'SaveFolder': 'Fok_it', 'Hostfolder': 'sarjakuvat/fokit', 'fileextension': '.jpg', 'host': host_hs }
keskenkasvuisia = {'SaveFolder': 'Keskenkasvuisia', 'Hostfolder': 'sarjakuvat/keskenkasvuisia', 'fileextension': '.jpg', 'host': host_hs }
lassijaleevi = {'SaveFolder': 'LassiJaLeevi', 'Hostfolder': 'lassijaleevi', 'fileextension': '.jpg', 'host': host_hs }
harald = {'SaveFolder': 'Harald', 'Hostfolder': 'haraldhirmuinen', 'fileextension': '.jpg', 'host': host_hs }

comics = [
	# nemi, 		# removed
	# kamalaluonto, # only in the physical paper since 1.1.2021
	# dilbert,		# removed?
	# karlsson,		# removed?
	# jaatavaspede,	# removed?
	# wumo,
	# anonyymitElaimet,
	jarla,
	fingerpori,	
	viivijawagner, 
	fokit,
	keskenkasvuisia,
	lassijaleevi,
	harald
	]



def requestWebPage(url):

	headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    "Content-Type": "application/x-www-form-urlencoded"}

	# https://www.hs.fi/api/laneitems/39221/list/normal/291/full
 	# r = http3.get(url, headers=headers) # in case http3 is the issue. it isn't.

	res = requests.get(url, headers=headers)
	res.raise_for_status()
	return res.text
    
def getComicDate(comicName):
    # use the YYYY-MM-DD as filename. inside the second meta tag
    # <meta itemprop="datePublished" content="2017-10-03">
    if len(comicName) == 0:
        return []
    picName = str(comicName[1])
    return picName[picName.find("content=")+9:picName.find(" itemprop") -1]

def getComicUrl_SanomaCommon(comicElem, fileextension):
	# The image is inside the img element, and the url is in the data-srcset attribute, appended with " 1920w"

	# <img id="image-6518390" class="lazyload lazyloadable-image  image-loaded" data-alt="" 
	# data-simple-src="//images.sanoma-sndp.fi/81f606067718361193953521887c6422/normal/320.jpg" 
	# data-srcset="//images.sanoma-sndp.fi/81f606067718361193953521887c6422/normal/1920.jpg 1920w" 
	# sizes="940px" srcset="//images.sanoma-sndp.fi/81f606067718361193953521887c6422/normal/1920.jpg.webp 1920w" 
	# data-lazyloaded="true">
	# -> https://images.sanoma-sndp.fi/81f606067718361193953521887c6422/normal/1920.jpg

    if comicElem == None or len(comicElem) == 0:
        return []
    picUrl = str(comicElem[0])

    # as of 6.6.2018 the comicElem contains two url, of which "data-simple-src" seems to contain the small images, and is found first
    # so cut away everything before "data-srcset" so that the bigger picture can be found

    url = picUrl[picUrl.find("data-srcset=\"//" + sanomaComicUrl):]

	# some comics, e.g. LassijaLeevi 1.11.2024 have a url like this
	# https://images.sanoma-sndp.fi/221ca68817c87389aaf0934f60f6d7b2.jpg/normal/1920.jpg.webp
	# so, use rfind() for the extension. that finds the last occurrance
    return "https://" + url[url.find("//" + sanomaComicUrl)+2:url.rfind(fileextension)+len(fileextension)]

def getComicUrl(comicElem, PaperName, fileextension):
	# The image is inside the first source component in the lazy class, inside the class cartoon-content
    # e.g. <source data-srcset="//hs.mediadelivery.fi/img/1920/7d5a631fb3524d9294b12789822b5ceb.jpg 1920w" />
    # -> http://hs.mediadelivery.fi/img/1920/7d5a631fb3524d9294b12789822b5ceb.jpg

    if comicElem == None or len(comicElem) == 0:
        return []
    picUrl = str(comicElem[0])

    # as of 6.6.2018 the comicElem contains two url, of which "data-simple-src" seems to contain the small images, and is found first
    # so cut away everything before "data-srcset" so that the bigger picture can be found
    url = picUrl[picUrl.find("data-srcset=\"//" + PaperName + "."):]

    # return "http://" + picUrl[picUrl.find("//" + PaperName + ".")+2:picUrl.find(fileextension)+len(fileextension)] # pre-"data-simple-src"
    return "http://" + url[url.find("//" + PaperName + ".")+2:url.find(fileextension)+len(fileextension)]


def getBackBtnUrl(back_tag, baseUrl, soup):
    # <a class="article-navlink prev " href="/nemi/car-xxxx.html">Edellinen</a>?
    if back_tag == None or len(back_tag) == 0:
        back_tag = soup.find("a", class_="article-navlink prev disabled")
        if back_tag != None:
            print("First item! Can't go furher back.")
        return "#"
    url = baseUrl + str(back_tag.get("href"))
    return url

def saveImage(picName, fileextension, saveFolder, res):
    imageFile = open(os.path.join(saveFolder, os.path.basename(picName+fileextension)), "wb")
    # print("Saving to: " + str(imageFile))

    for chunk in res.iter_content(100000):
        imageFile.write(chunk)
    imageFile.close

def fileExists(picName, fileextension, saveFolder):
	return os.path.isfile(os.path.join(saveFolder, os.path.basename(picName+fileextension)))



########################

def getComicStrips(comic):
	os.makedirs(comic['SaveFolder'], exist_ok=True)	# create save directory
	url = getFirstComicsUrl(comic)   # appends <comicname>/car-xxxxxx.html
	downloadComicStrips(url, comic)

# Get the URL for the first comic from the host page. Thenstart downloading and crawling using downloadComicStrips().
def getFirstComicsUrl(comic):
	url = comic['host']['BaseUrl'] + "/" + comic['Hostfolder']
	page = requestWebPage(url) # PROBLEM! doesn't return the full html
	soup = bs4.BeautifulSoup(requestWebPage(url), "html.parser")
	
	# print("First comic url: " + url)
	
	data = soup.find_all('div',attrs={'class':'picture-with-caption__wrapper'})[0].find('img').get("src") # find the car-xxxxxx.html

	if len(data) == 0:
	    return "#"
	return comic['host']['BaseUrl'] + data

def downloadComicStrips(url, comic):
	while not url.endswith('#'):
    
        #print("Downloading page %s..." % url)   # Download the page.

		soup = bs4.BeautifulSoup(requestWebPage(url), "html.parser")

        # Find the URL of the comic image.
		ContainerElement = soup.findAll('figure',attrs={'class':'cartoon image scroller'})
		if ContainerElement == []:
			ContainerElement = soup.findAll('figure',attrs={'class':'cartoon image '}) #JäätäväSpede doesn't have the scroller class
		if ContainerElement == []:
			ContainerElement = soup.findAll('figure',attrs={'class':'cartoon image'}) # Sometimes there's a space after 'image', and sometimes not
        
		Name = soup.select('.cartoon meta')   # use the YYYY-MM-DD as filename. inside the second meta tag
		
		# a-tag for the back button
		a_back = soup.find("a", class_="article-navlink prev ")
		
		if a_back == None:
			a_back = soup.find("a", class_="article-navlink prev") # Sometimes there is a space after prev, sometimes not.

		if ContainerElement == [] or Name == []:
			print('Could not find comic image.')
			print('ContainerElement: ' + str(ContainerElement))
			print('Name: ' + str(Name))
		else:
			try:
				picName = getComicDate(Name)
				
				if fileExists(picName, comic['fileextension'], comic['SaveFolder']) == False:
					picUrl = getComicUrl_SanomaCommon(ContainerElement, comic['fileextension'])

					if picName == "" or picUrl == "http://":
						print("A problem ocurred at: " + url + "\njumping to next")
						url = getBackBtnUrl(a_back, comic['host']['BaseUrl'], soup)
						continue

					# print ("Downloading image %s" % (picUrl))
					print ("Downloading image {0} as {1}\\{2}{3}".format(picUrl, comic['SaveFolder'], picName, comic['fileextension'] ) )

					res = requests.get(picUrl)    # Download the image.
					res.raise_for_status()          # raises error if any
					saveImage(picName, comic['fileextension'], comic['SaveFolder'], res)
				else:
					print("{0}\\{1}{2} already downloaded. jump to next".format(comic['SaveFolder'], picName, comic['fileextension']))
					
			except requests.exceptions.MissingSchema:
                # Skip this comic
				url = getBackBtnUrl(a_back, comic['host']['BaseUrl'], soup)
				logging.debug("skip")
				continue
            
		if StopAt != None:
			dtThisPic = datetime.strptime(picName, "%Y-%m-%d")
			dtStop = datetime.strptime(StopAt, "%Y-%m-%d")

			if dtThisPic <= dtStop:
				print("Reached the desired stop date!")
				break

		url = getBackBtnUrl(a_back, comic['host']['BaseUrl'], soup)  # Get the Prev button's url.
        #break # uncomment when testing

########################

downloadThreads = []
for comic in comics:
	downloadThread = threading.Thread(target=getComicStrips, args=(comic,))	# provide args a tuple
	print("starting thread for: {0}".format(comic['SaveFolder']) )
	downloadThreads.append(downloadThread)
	downloadThread.start() 

for downloadThread in downloadThreads:
    downloadThread.join() 
    print("joining thread")

print('Done.')
