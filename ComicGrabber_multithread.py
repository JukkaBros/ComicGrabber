import requests, os, bs4
import logging, sys, threading
from datetime import datetime

# logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

# note! Fingerpori 2018-05-02 --> ~2018-06-01 images missing from hs.fi

# setup -->
StopAt = "2019-10-01" #None   # crawl back to 'YYYY-MM-DD' or None (if you want all)
# <-- setup

host_is = {'BaseUrl': 'https://www.is.fi', 'ShortName': 'is'}
host_hs = {'BaseUrl': 'https://www.hs.fi', 'ShortName': 'hs'}

# nemi = 			{'SaveFolder': 'Nemi', 'Hostfolder': 'nemi', 'fileextension': '.jpg', 'host': host_is } # removed from is.fi 20190104
kamalaluonto = 	{'SaveFolder': 'KamalaLuonto', 'Hostfolder': 'kamalaluonto', 'fileextension': '.jpg', 'host': host_is }
dilbert = 		{'SaveFolder': 'Dilbert', 'Hostfolder': 'dilbert', 'fileextension': '.gif', 'host': host_is }
fingerpori = 	{'SaveFolder': 'Fingerpori', 'Hostfolder': 'fingerpori', 'fileextension': '.jpg', 'host': host_hs }
wumo = 			{'SaveFolder': 'Wumo', 'Hostfolder': 'wumo', 'fileextension': '.jpg', 'host': host_hs }
viivijawagner = {'SaveFolder': 'ViiviJaWagner', 'Hostfolder': 'viivijawagner', 'fileextension': '.jpg', 'host': host_hs }
jaatavaspede = 	{'SaveFolder': 'JaatavaSpede', 'Hostfolder': 'jaatavaspede', 'fileextension': '.jpg', 'host': host_hs }
fokit = 		{'SaveFolder': 'Fok_it', 'Hostfolder': 'nyt/fokit', 'fileextension': '.jpg', 'host': host_hs }

comics = [
	# nemi, 
	kamalaluonto, 
	dilbert,
	fingerpori,
	wumo,
	viivijawagner, 
	jaatavaspede,
	fokit
	]



def requestWebPage(url):
    res = requests.get(url)
    res.raise_for_status()
    return res.text
    
def getComicDate(comicName):
    # use the YYYY-MM-DD as filename. inside the second meta tag
    # <meta itemprop="datePublished" content="2017-10-03">
    if len(comicName) == 0:
        return []
    picName = str(comicName[1])
    return picName[picName.find("content=")+9:picName.find(" itemprop") -1]

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

def getFirstComicsUrl(comic):
	soup = bs4.BeautifulSoup(requestWebPage(comic['host']['BaseUrl'] + "/" + comic['Hostfolder']), "html.parser")

	data = soup.findAll('div',attrs={'class':'cartoon-content'})[0].find('a').get("href")
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
        
		Name = soup.select('.cartoon meta')   # use the YYYY-MM-DD as filename. inside the second meta tag
		a_back = soup.find("a", class_="article-navlink prev ")

		if ContainerElement == [] or Name == []:
			print('Could not find comic image.')
			print('ContainerElement: ' + str(ContainerElement))
			print('Name: ' + str(Name))
		else:
			try:
				picName = getComicDate(Name)
				
				if fileExists(picName, comic['fileextension'], comic['SaveFolder']) == False:
					picUrl = getComicUrl(ContainerElement, comic['host']['ShortName'], comic['fileextension'])

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