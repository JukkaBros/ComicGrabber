import requests, os, bs4
import logging, sys

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

# note! Fingerpori 2018-05-02 --> ~2018-06-01 images missing from hs.fi

# setup -->
ComicName = "JaatavaSpede"  # KamalaLuonto / Nemi / Dilbert / Fingerpori / Wumo / ViiviJaWagner / JaatavaSpede / "Nyt/FokIt"
StopAt = "2018-09-20" #None   # crawl back to 'YYYY-MM-DD' or None (if you want all) # NOTE! StopAt should be <= <date>
# <-- setup

# constants -->
is_comics = ['nemi', 'kamalaluonto', 'dilbert']
hs_comics = ['fingerpori', 'wumo', 'viivijawagner', 'jaatavaspede', 'nyt/fokit' ]
os.makedirs(ComicName, exist_ok=True)   # store comics in ./<ComicName>
# <-- constants

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

def getComicUrl(comicElem, PaperName):
    # The image is inside the first source component in the lazy class, inside the class cartoon-content
    # e.g. <source data-srcset="//hs.mediadelivery.fi/img/1920/7d5a631fb3524d9294b12789822b5ceb.jpg 1920w" />
    # -> http://hs.mediadelivery.fi/img/1920/7d5a631fb3524d9294b12789822b5ceb.jpg
    if comicElem == None or len(comicElem) == 0:
        return []
    picUrl = str(comicElem[0])
    return "http://" + picUrl[picUrl.find("//" + PaperName + ".")+2:picUrl.find(".jpg")+4] # TODO: hs./is.

def getBackBtnUrl(back_tag, baseUrl, soup):
    # <a class="article-navlink prev " href="/nemi/car-xxxx.html">Edellinen</a>?
    if back_tag == None or len(back_tag) == 0:
        back_tag = soup.find("a", class_="article-navlink prev disabled")
        if back_tag != None:
            print("First item! Can't go furher back.")
        return "#"
    url = baseUrl + str(back_tag.get("href"))
    return url

def getFirstComicsUrl(firstUrl, ComicName):
    soup = bs4.BeautifulSoup(requestWebPage(firstUrl + "/" + ComicName), "html.parser")

    data = soup.findAll('div',attrs={'class':'cartoon-content'})[0].find('a').get("href")
    if len(data) == 0:
        return "#"
    return firstUrl + data

def getFirstComicsUrl_hs(firstUrl, ComicName):
    soup = bs4.BeautifulSoup(requestWebPage(firstUrl + "/" + ComicName), "html.parser")

    # data = soup.findAll('div',attrs={'class':'is-list cartoons section'})[0].find('a').get("href")
    data = soup.findAll('li',attrs={'class':'list-item cartoon'})[0].find('a').get("href")
    print("cartoon items: \n {0}".format(data))
    if len(data) == 0:
        return "#"
    return firstUrl + data


def getBaseUrl(ComicName, is_comics, hs_comics):
    if any(str.lower(ComicName) in s for s in is_comics):
        return 'https://www.is.fi'
    if any(str.lower(ComicName) in s for s in hs_comics):
        return 'https://www.hs.fi'
    return ""

# get "is" or "hs" which will be used when getting the images url
def getPaperName(ComicName, is_comics, hs_comics):
    if any(str.lower(ComicName) in s for s in is_comics):
        return 'is'
    if any(str.lower(ComicName) in s for s in hs_comics):
        return 'hs'
    return ""

def saveImage(picName, res):
    imageFile = open(os.path.join(ComicName, os.path.basename(picName+".jpg")), "wb")
    print("Saving to: " + str(imageFile))

    for chunk in res.iter_content(100000):
        imageFile.write(chunk)
    imageFile.close

def getComicsFromIS(url):
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
                picUrl = getComicUrl(ContainerElement, Paper)

                #logging.debug("picName: " + picName)
                #logging.debug("picUrl: " + str(picUrl))

                if picName == "" or picUrl == "http://":
                    print("A problem ocurred at: " + url + "\njumping to next")
                    url = getBackBtnUrl(a_back, baseUrl, soup)
                    continue

                print ("Downloading image %s" % (picUrl))

                res = requests.get(picUrl)    # Download the image.
                res.raise_for_status()          # raises error if any
            except requests.exceptions.MissingSchema:
                # Skip this comic
                url = getBackBtnUrl(a_back, baseUrl, soup)
                logging.debug("skip")
                continue
            
        saveImage(picName, res)

        if StopAt == picName:
            print("Reached the desired stop date!")
            break

        url = getBackBtnUrl(a_back, baseUrl, soup)  # Get the Prev button's url.
        #break # uncomment when testing

def getComicsFromHS(url):
    # hs cartoons are now inside <li class="list-item cartoon><div class cartoon-content">
    # need to open up the links inside the li's individuall and grab the comic, then click the show more button
    print("TODO! implement me")


# set up some variables -->
baseUrl = getBaseUrl(ComicName, is_comics, hs_comics)
Paper = getPaperName(ComicName, is_comics, hs_comics)

# Open the first comic! No back button on the main page!
url = getFirstComicsUrl(baseUrl, str.lower(ComicName))   # appends <comicname>/car-xxxxxx.html
#url = getFirstComicsUrl_hs(baseUrl, str.lower(ComicName))   # appends <comicname>/car-xxxxxx.html
# <-- set up some variables


getComicsFromIS(url)

print('Done.')
