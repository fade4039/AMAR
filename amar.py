import tkinter.filedialog
import requests
import os
import re
import tkinter
from datetime import datetime
import textwrap
import json
from typing import Optional, List, Dict

"""
Apple Music API Ripper (AMAR) V1
Enhanced version combining ripss.py and tu.py functionality
Supports: Artists, Albums, Music Videos, Radio Stations, Search, Charts, and more
"""

# ==================== CONFIGURATION ====================

countryCodes = {
    "al": "Albania", "dz": "Algeria", "ao": "Angola", "ai": "Anguilla",
    "ag": "Antigua and Barbuda", "ar": "Argentina", "am": "Armenia",
    "au": "Australia", "at": "Austria", "az": "Azerbaijan", "bs": "Bahamas",
    "bh": "Bahrain", "bb": "Barbados", "by": "Belarus", "be": "Belgium",
    "bz": "Belize", "bj": "Benin", "bm": "Bermuda", "bt": "Bhutan",
    "bo": "Bolivia", "bw": "Botswana", "br": "Brazil", "vg": "British Virgin Islands",
    "bn": "Brunei Darussalam", "bg": "Bulgaria", "bf": "Burkina-Faso",
    "kh": "Cambodia", "ca": "Canada", "cv": "Cape Verde", "ky": "Cayman Islands",
    "td": "Chad", "cl": "Chile", "cn": "China", "co": "Colombia", "cr": "Costa Rica",
    "hr": "Croatia", "cy": "Cyprus", "cz": "Czech Republic",
    "cg": "Democratic Republic of the Congo", "dk": "Denmark", "dm": "Dominica",
    "do": "Dominican Republic", "ec": "Ecuador", "eg": "Egypt", "sv": "El Salvador",
    "ee": "Estonia", "fm": "Federated States of Micronesia", "fj": "Fiji",
    "fi": "Finland", "fr": "France", "gm": "Gambia", "de": "Germany", "gh": "Ghana",
    "gb": "Great Britain", "gr": "Greece", "gd": "Grenada", "gt": "Guatemala",
    "gw": "Guinea Bissau", "gy": "Guyana", "hn": "Honduras", "hk": "Hong Kong",
    "hu": "Hungary", "is": "Iceland", "in": "India", "id": "Indonesia",
    "ie": "Ireland", "il": "Israel", "it": "Italy", "jm": "Jamaica", "jp": "Japan",
    "jo": "Jordan", "kz": "Kazakhstan", "ke": "Kenya", "kg": "Kyrgyzstan",
    "kw": "Kuwait", "la": "Laos", "lv": "Latvia", "lb": "Lebanon", "lr": "Liberia",
    "lt": "Lithuania", "lu": "Luxembourg", "mo": "Macau", "mk": "Macedonia",
    "mg": "Madagascar", "mw": "Malawi", "my": "Malaysia", "ml": "Mali", "mt": "Malta",
    "mr": "Mauritania", "mu": "Mauritius", "mx": "Mexico", "md": "Moldova",
    "mn": "Mongolia", "ms": "Montserrat", "mz": "Mozambique", "na": "Namibia",
    "np": "Nepal", "nl": "Netherlands", "nz": "New Zealand", "ni": "Nicaragua",
    "ne": "Niger", "ng": "Nigeria", "no": "Norway", "om": "Oman", "pk": "Pakistan",
    "pw": "Palau", "pa": "Panama", "pg": "Papua New Guinea", "py": "Paraguay",
    "pe": "Peru", "ph": "Philippines", "pl": "Poland", "pt": "Portugal", "qa": "Qatar",
    "tt": "Republic of Trinidad and Tobago", "ro": "Romania", "ru": "Russia",
    "kn": "Saint Kitts and Nevis", "lc": "Saint Lucia",
    "vc": "Saint Vincent and the Grenadines", "st": "Sao Tome e Principe",
    "sa": "Saudi Arabia", "sn": "Senegal", "sc": "Seychelles", "sl": "Sierra Leone",
    "sg": "Singapore", "sk": "Slovakia", "si": "Slovenia", "sb": "Solomon Islands",
    "za": "South Africa", "kr": "South Korea", "es": "Spain", "lk": "Sri Lanka",
    "sr": "Suriname", "sz": "Swaziland", "se": "Sweden", "ch": "Switzerland",
    "tw": "Taiwan", "tj": "Tajikistan", "tz": "Tanzania", "th": "Thailand",
    "tn": "Tunisia", "tr": "Turkey", "tm": "Turkmenistan", "tc": "Turks and Caicos Islands",
    "ug": "Uganda", "ua": "Ukraine", "ae": "United Arab Emirates",
    "us": "United States of America", "uy": "Uruguay", "uz": "Uzbekistan",
    "ve": "Venezuela", "vn": "Vietnam", "ye": "Yemen", "zw": "Zimbabwe"
}

BASEPATH = os.path.dirname(os.path.realpath(__file__))
FOLDERPATH = ""
countrycode = "us"
currentDate = datetime.today().strftime('%Y-%m-%d')
albumList = []

# ==================== TOKEN MANAGEMENT ====================

def load_token() -> str:
    """Load API token from token.txt"""
    token_path = os.path.join(BASEPATH, "token.txt")
    try:
        with open(token_path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        print("❌ Error: token.txt not found. Run tu.py first to extract token.")
        exit(1)

def extract_token_with_selenium():
    """Extract token using Selenium (from tu.py)"""
    try:
        from selenium import webdriver
        import time
        
        print("🔄 Extracting token from Apple Music...")
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        driver = webdriver.Chrome(options=options)
        
        driver.get("https://music.apple.com")
        time.sleep(2)
        
        developer_token = driver.execute_script("return MusicKit.getInstance().developerToken;")
        driver.quit()
        
        if developer_token:
            token_path = os.path.join(BASEPATH, "token.txt")
            with open(token_path, "w") as f:
                f.write(developer_token)
            print(f"✅ Token saved to {token_path}")
            return developer_token
        else:
            print("❌ Failed to extract developer token.")
            return None
    except ImportError:
        print("❌ Selenium not installed. Install with: pip install selenium")
        return None
    except Exception as e:
        print(f"❌ Error extracting token: {e}")
        return None

token = load_token()
apiURL = 'amp-api.music.apple.com'

apiHeader = {
    'Authorization': f"Bearer {token}",
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://music.apple.com/',
    'Origin': 'https://music.apple.com',
    'Accept': '*/*'
}

# ==================== UTILITY FUNCTIONS ====================

def convertMS(mill_sec: int) -> str:
    """Convert milliseconds to MM:SS format"""
    total_sec = mill_sec / 1000
    min = int(total_sec // 60)
    sec = int(total_sec % 60)
    return f"{min}:{sec:02d}"

def getCleanName(input: str) -> str:
    """Clean filename for filesystem compatibility"""
    clean = re.sub(r"[/\\?%*:|\"<>\x7F\x00-\x1F]", "-", input)
    return clean

def fetch_storefront_ids() -> List[str]:
    """Fetch available storefronts from API"""
    try:
        resp = requests.get(f"https://{apiURL}/v1/storefronts", headers=apiHeader, timeout=15)
        if resp.ok:
            data = resp.json()
            ids = [item.get("id", "").lower() for item in data.get("data", []) if item.get("id")]
            return list(dict.fromkeys(ids))  # Remove duplicates
    except Exception as e:
        print(f"⚠️ Could not fetch storefronts: {e}")
    return list(countryCodes.keys())

def setup_folder() -> str:
    """Setup destination folder with persistence"""
    global FOLDERPATH
    dest_path = os.path.join(BASEPATH, "dest.path")
    
    if os.path.exists(dest_path):
        with open(dest_path, "r+") as f:
            path = f.readline().strip()
        if os.path.exists(path):
            FOLDERPATH = path
        else:
            FOLDERPATH = tkinter.filedialog.askdirectory()
            with open(dest_path, "w+") as f:
                f.write(FOLDERPATH)
    else:
        FOLDERPATH = tkinter.filedialog.askdirectory()
        with open(dest_path, "w+") as f:
            f.write(FOLDERPATH)
    
    return FOLDERPATH

# ==================== CATALOG SEARCH ====================

def search_catalog(query: str, types: List[str] = None, limit: int = 25) -> Dict:
    """
    Search Apple Music catalog
    types: ['songs', 'albums', 'artists', 'playlists', 'music-videos', 'stations']
    """
    if types is None:
        types = ['songs', 'albums', 'artists']
    
    params = {
        'term': query,
        'types': ','.join(types),
        'limit': limit
    }
    
    try:
        response = requests.get(
            f"https://{apiURL}/v1/catalog/{countrycode}/search",
            headers=apiHeader,
            params=params,
            timeout=15
        )
        
        if response.ok:
            return response.json()
        else:
            print(f"❌ Search failed: {response.status_code}")
            return {}
    except Exception as e:
        print(f"❌ Search error: {e}")
        return {}

def display_search_results(results: Dict):
    """Display formatted search results"""
    if not results or 'results' not in results:
        print("No results found.")
        return
    
    res = results['results']
    
    # Artists
    if 'artists' in res and res['artists']['data']:
        print("\n🎤 ARTISTS:")
        for i, artist in enumerate(res['artists']['data'][:10], 1):
            name = artist['attributes']['name']
            genres = ', '.join(artist['attributes'].get('genreNames', []))
            url = artist['attributes']['url']
            print(f"  {i}. {name} ({genres})")
            print(f"     URL: {url}")
    
    # Albums
    if 'albums' in res and res['albums']['data']:
        print("\n💿 ALBUMS:")
        for i, album in enumerate(res['albums']['data'][:10], 1):
            name = album['attributes']['name']
            artist = album['attributes']['artistName']
            year = album['attributes'].get('releaseDate', 'Unknown')[:4]
            url = album['attributes']['url']
            print(f"  {i}. {name} - {artist} ({year})")
            print(f"     URL: {url}")
    
    # Songs
    if 'songs' in res and res['songs']['data']:
        print("\n🎵 SONGS:")
        for i, song in enumerate(res['songs']['data'][:10], 1):
            name = song['attributes']['name']
            artist = song['attributes']['artistName']
            album = song['attributes']['albumName']
            duration = convertMS(song['attributes']['durationInMillis'])
            print(f"  {i}. {name} - {artist}")
            print(f"     Album: {album} | Duration: {duration}")

# ==================== CHARTS ====================

def get_charts(chart_types: List[str] = None, limit: int = 20) -> Dict:
    """
    Get Apple Music charts
    chart_types: ['songs', 'albums', 'music-videos', 'playlists']
    """
    if chart_types is None:
        chart_types = ['songs', 'albums']
    
    params = {
        'types': ','.join(chart_types),
        'limit': limit
    }
    
    try:
        response = requests.get(
            f"https://{apiURL}/v1/catalog/{countrycode}/charts",
            headers=apiHeader,
            params=params,
            timeout=15
        )
        
        if response.ok:
            return response.json()
        else:
            print(f"❌ Charts request failed: {response.status_code}")
            return {}
    except Exception as e:
        print(f"❌ Charts error: {e}")
        return {}

def display_charts(charts_data: Dict):
    """Display formatted charts"""
    if not charts_data or 'results' not in charts_data:
        print("No charts data available.")
        return
    
    results = charts_data['results']
    
    # Songs Chart
    if 'songs' in results and results['songs']:
        print("\n🔥 TOP SONGS:")
        for chart in results['songs']:
            if 'data' in chart:
                for i, song in enumerate(chart['data'][:20], 1):
                    name = song['attributes']['name']
                    artist = song['attributes']['artistName']
                    print(f"  {i:2d}. {name} - {artist}")
    
    # Albums Chart
    if 'albums' in results and results['albums']:
        print("\n💿 TOP ALBUMS:")
        for chart in results['albums']:
            if 'data' in chart:
                for i, album in enumerate(chart['data'][:20], 1):
                    name = album['attributes']['name']
                    artist = album['attributes']['artistName']
                    print(f"  {i:2d}. {name} - {artist}")

# ==================== STOREFRONT INFO ====================

def get_storefront_info(storefront_id: str = None) -> Dict:
    """Get information about a specific storefront"""
    if storefront_id is None:
        storefront_id = countrycode.lower()
    
    try:
        response = requests.get(
            f"https://{apiURL}/v1/storefronts/{storefront_id}",
            headers=apiHeader,
            timeout=15
        )
        
        if response.ok:
            return response.json()
        else:
            print(f"❌ Storefront request failed: {response.status_code}")
            return {}
    except Exception as e:
        print(f"❌ Storefront error: {e}")
        return {}

def display_storefront_info(storefront_data: Dict):
    """Display storefront information"""
    if not storefront_data or 'data' not in storefront_data:
        print("No storefront data available.")
        return
    
    data = storefront_data['data'][0]['attributes']
    print(f"\n🌍 Storefront: {data['name']}")
    print(f"   Language: {data.get('defaultLanguageTag', 'Unknown')}")
    print(f"   Supported Languages: {', '.join(data.get('supportedLanguageTags', []))}")

# ==================== ARTIST ASSETS ====================

def getArtistAssets(artistID: str, info_only: bool = False):
    """Download artist assets (from ripss.py)"""
    artistExtraParams = 'extend=artistBio,bornOrFormed,editorialArtwork,editorialVideo,extendedAssetUrls,hero,isGroup,origin,plainEditorialNotes,seoDescription,seoTitle&format[resources]=map&include=record-labels,artists&include[songs]=artists&l=en-US&platform=web'
    request = requests.get(
        url=f'https://{apiURL}/v1/catalog/{countrycode}/artists/{artistID}?{artistExtraParams}',
        headers=apiHeader
    )

    requestJSON = request.json()
    mainData = requestJSON['resources']['artists'][artistID]
    artistName = getCleanName(mainData['attributes']['name'])
    artistAssetsFolder = os.path.join(FOLDERPATH, f"{artistName} - Artist Assets - {currentDate}")

    if not os.path.exists(artistAssetsFolder):
        os.makedirs(artistAssetsFolder)

    if not info_only:
        # Hero artwork
        try:
            heroArtwork = mainData['attributes']['hero'][0]['content'][0]['artwork']
            height = heroArtwork['height']
            width = heroArtwork['width']
            artworkURL = str(heroArtwork['url']).replace("{w}", str(width)).replace("{h}", str(height))
            print(f"📥 Downloading {getCleanName(f'{artistName} ({countrycode}) - Hero - {width}x{height}.jpg')}")
            artworkReq = requests.get(url=artworkURL, stream=True)
            with open(os.path.join(artistAssetsFolder, getCleanName(f"{artistName} ({countrycode}) - Hero - {width}x{height}.jpg")), "wb+") as f:
                f.write(artworkReq.content)
        except:
            pass

        # Editorial videos
        try:
            artistPageVideo = mainData['attributes']['editorialVideo']
            for videoData in artistPageVideo:
                previewData = artistPageVideo[videoData]['previewFrame']
                width = previewData['width']
                height = previewData['height']
                previewURL = str(previewData['url']).replace("{w}", str(width)).replace("{h}", str(height))
                print(f"📥 Downloading {getCleanName(f'{artistName} ({countrycode}) - {videoData} - {width}x{height}.jpg')}")
                previewReq = requests.get(url=previewURL, stream=True)
                with open(os.path.join(artistAssetsFolder, getCleanName(f"{artistName} ({countrycode}) - {videoData} - {width}x{height}.jpg")), "wb+") as f:
                    f.write(previewReq.content)

                videoM3U8 = artistPageVideo[videoData]['video']
                videoM3U8Req = requests.get(url=videoM3U8)
                mainM3U8Link = ""
                for line in videoM3U8Req.iter_lines():
                    line = bytes(line).decode('utf-8')
                    if "https://" in line:
                        mainM3U8Link = line

                linkParts = mainM3U8Link.split("/")
                mainM3U8Req = requests.get(url=mainM3U8Link)
                videoEnding = ""
                for line in mainM3U8Req.iter_lines():
                    line = bytes(line).decode('utf-8')
                    if str(linkParts[-1])[0:20] in line:
                        videoEnding = line
                linkParts[-1] = videoEnding

                print(f"📥 Downloading {getCleanName(f'{artistName} ({countrycode}) - {videoData}.mp4')}")
                videoURL = "/".join(linkParts)
                videoURLReq = requests.get(url=videoURL, stream=True)
                with open(os.path.join(artistAssetsFolder, getCleanName(f"{artistName} ({countrycode}) - {videoData}.mp4")), "wb+") as f:
                    f.write(videoURLReq.content)
        except:
            pass

        # Editorial artwork
        try:
            editorialArtwork = mainData['attributes']['editorialArtwork']
            for key in editorialArtwork:
                mainArtwork = editorialArtwork[key]
                width = mainArtwork['width']
                height = mainArtwork['height']
                artURL = str(mainArtwork['url']).replace("{w}", str(width)).replace("{h}", str(height))
                print(f"📥 Downloading {getCleanName(f'{artistName} ({countrycode}) - {key} - {width}x{height}.jpg')}")
                artReq = requests.get(url=artURL, stream=True)
                with open(os.path.join(artistAssetsFolder, getCleanName(f"{artistName} ({countrycode}) - {key} - {width}x{height}.jpg")), "wb+") as f:
                    f.write(artReq.content)
        except:
            pass

        # General artwork
        try:
            generalArtwork = mainData['attributes']['artwork']
            width = generalArtwork['width']
            height = generalArtwork['height']
            artURL = str(generalArtwork['url']).replace("{w}", str(width)).replace("{h}", str(height))
            print(f"📥 Downloading {getCleanName(f'{artistName} ({countrycode}) - artwork - {width}x{height}.jpg')}")
            artworkReq = requests.get(url=artURL, stream=True)
            with open(os.path.join(artistAssetsFolder, getCleanName(f"{artistName} ({countrycode}) - artwork - {width}x{height}.jpg")), "wb+") as f:
                f.write(artworkReq.content)
        except:
            pass

    # Info file (always downloaded)
    print(f"📥 Downloading {getCleanName(f'{artistName} ({countrycode}) - INFO.txt')}")
    with open(os.path.join(artistAssetsFolder, f"{artistName} ({countrycode}) - INFO.txt"), "w+", encoding="utf-8") as f:
        try:
            f.write(f"Name: {mainData['attributes']['name']}\n")
        except:
            pass
        try:
            f.write(f"Genre: {'/'.join(list(mainData['attributes']['genreNames']))}\n")
        except:
            pass
        try:
            f.write(f"Born or formed: {mainData['attributes']['bornOrFormed']}\n")
        except:
            pass
        try:
            f.write(f"Origin: {mainData['attributes']['origin']}\n")
        except:
            pass
        try:
            f.write(f"Group: {mainData['attributes']['isGroup']}\n")
        except:
            pass
        try:
            f.write(f"Apple Music URL: {mainData['attributes']['url']}\n\n")
        except:
            pass
        try:
            artistBio = str(mainData['attributes']['artistBio'])
            f.write(f"Artist Bio:\n")
            f.write(textwrap.fill(artistBio, width=100))
        except:
            pass

    if info_only:
        print(f"✅ Artist info saved to {artistAssetsFolder}")
    else:
        print(f"✅ Artist assets saved to {artistAssetsFolder}")

def getAllAlbumIDs(artistID: str, offsetLink: str = "") -> List[str]:
    """Get all album IDs for an artist"""
    global albumList
    if offsetLink == "":
        mainReq = requests.get(
            url=f"https://{apiURL}/v1/catalog/{countrycode}/artists/{artistID}/albums",
            headers=apiHeader
        )
    else:
        mainReq = requests.get(url=f"https://{apiURL}{offsetLink}", headers=apiHeader)
    
    mainReq = mainReq.json()

    for albumDict in mainReq['data']:
        print(f"💽 Found album ID: {albumDict['id']}")
        albumList.append(albumDict['id'])

    try:
        getAllAlbumIDs(artistID, mainReq['next'])
    except:
        pass
    
    return albumList

# ==================== ALBUM ASSETS ====================

def getAlbumAssets(albumID: str, info_only: bool = False):
    """Download album assets"""
    artistExtraParams = '?extend=editorialArtwork,editorialVideo,extendedAssetUrls,offers,seoDescription,seoTitle&format[resources]=map&include=record-labels,artists&include[songs]=artists,composers,albums'
    mainReq = requests.get(
        url=f"https://{apiURL}/v1/catalog/{countrycode}/albums/{albumID}{artistExtraParams}",
        headers=apiHeader
    )
    mainReq = mainReq.json()
    songMainData = mainReq.get('resources', {}).get('songs', {})
    
    if not songMainData:
        print("❌ Nothing found, skipping....")
        return
    
    mainData = mainReq['resources']['albums'][albumID]
    artistName = mainData['attributes']['artistName']
    albumName = mainData['attributes']['name']

    albumFolderPath = os.path.join(
        FOLDERPATH,
        "Album Assets",
        getCleanName(f"{artistName} - {albumName} - {mainData['attributes']['releaseDate']}")
    )
    
    if not os.path.exists(albumFolderPath):
        os.makedirs(albumFolderPath)

    if not info_only:
        # Editorial videos
        try:
            albumPageVideo = mainData['attributes']['editorialVideo']
            for videoData in albumPageVideo:
                previewData = albumPageVideo[videoData]['previewFrame']
                width = previewData['width']
                height = previewData['height']
                previewURL = str(previewData['url']).replace("{w}", str(width)).replace("{h}", str(height))
                print(f"📥 Downloading {getCleanName(f'{albumName} ({countrycode}) - {videoData} - {width}x{height}.jpg')}")
                previewReq = requests.get(url=previewURL, stream=True)
                with open(os.path.join(albumFolderPath, getCleanName(f"{albumName} ({countrycode}) - {videoData} - {width}x{height}.jpg")), "wb+") as f:
                    f.write(previewReq.content)

                videoM3U8 = albumPageVideo[videoData]['video']
                videoM3U8Req = requests.get(url=videoM3U8)
                mainM3U8Link = ""
                for line in videoM3U8Req.iter_lines():
                    line = bytes(line).decode('utf-8')
                    if "https://" in line:
                        mainM3U8Link = line

                linkParts = mainM3U8Link.split("/")
                mainM3U8Req = requests.get(url=mainM3U8Link)
                videoEnding = ""
                for line in mainM3U8Req.iter_lines():
                    line = bytes(line).decode('utf-8')
                    if str(linkParts[-1])[0:20] in line:
                        videoEnding = line
                linkParts[-1] = videoEnding

                print(f"📥 Downloading {getCleanName(f'{albumName} ({countrycode}) - {videoData}.mp4')}")
                videoURL = "/".join(linkParts)
                videoURLReq = requests.get(url=videoURL, stream=True)
                with open(os.path.join(albumFolderPath, getCleanName(f"{albumName} ({countrycode}) - {videoData}.mp4")), "wb+") as f:
                    f.write(videoURLReq.content)
        except:
            pass

        # Editorial artwork
        try:
            editorialArtwork = mainData['attributes']['editorialArtwork']
            for key in editorialArtwork:
                mainArtwork = editorialArtwork[key]
                width = mainArtwork['width']
                height = mainArtwork['height']
                artURL = str(mainArtwork['url']).replace("{w}", str(width)).replace("{h}", str(height))
                print(f"📥 Downloading {getCleanName(f'{albumName} ({countrycode}) - {key} - {width}x{height}.jpg')}")
                artReq = requests.get(url=artURL, stream=True)
                with open(os.path.join(albumFolderPath, getCleanName(f"{albumName} ({countrycode}) - {key} - {width}x{height}.jpg")), "wb+") as f:
                    f.write(artReq.content)
        except:
            pass

        # General artwork
        try:
            generalArtwork = mainData['attributes']['artwork']
            width = generalArtwork['width']
            height = generalArtwork['height']
            artURL = str(generalArtwork['url']).replace("{w}", str(width)).replace("{h}", str(height))
            print(f"📥 Downloading {getCleanName(f'{albumName} ({countrycode}) - artwork - {width}x{height}.jpg')}")
            artworkReq = requests.get(url=artURL, stream=True)
            with open(os.path.join(albumFolderPath, getCleanName(f"{albumName} ({countrycode}) - artwork - {width}x{height}.jpg")), "wb+") as f:
                f.write(artworkReq.content)
        except:
            pass

    # Track list (always created for INFO file)
    trackList = []
    for songID in songMainData:
        songDetails = []
        songItem = songMainData[songID]
        songDetails.append(int(songItem['attributes']['trackNumber']))
        songDetails.append(songItem['attributes']['name'])
        duration = songItem['attributes'].get('durationInMillis')
        songDetails.append(convertMS(duration) if duration else "Unknown")
        try:
            songDetails.append(songItem['attributes']['composerName'])
        except:
            songDetails.append("No Composer")
        try:
            songDetails.append(songItem['attributes']['isrc'])
        except:
            songDetails.append("No ISRC")
        trackList.append(songDetails)

    trackList = sorted(trackList, key=lambda x: x[0])

    # Info file (always downloaded)
    print(f"📥 Downloading {getCleanName(f'{albumName} ({countrycode}) - INFO.txt')}")
    with open(os.path.join(albumFolderPath, getCleanName(f"{albumName} ({countrycode}) - INFO.txt")), "w+", encoding="utf-8") as f:
        f.write(f"Album name: {mainData['attributes']['name']}\n")
        f.write(f"Artist name: {mainData['attributes']['artistName']}\n")
        try:
            f.write(f"Genre: {'/'.join(mainData['attributes']['genreNames'])}\n")
        except:
            pass
        try:
            f.write(f"Copyright: {mainData['attributes']['copyright']}\n")
        except:
            pass
        try:
            f.write(f"Release Date: {mainData['attributes']['releaseDate']}\n")
        except:
            pass
        try:
            f.write(f"UPC: {mainData['attributes']['upc']}\n")
        except:
            pass
        try:
            f.write(f"URL: {mainData['attributes']['url']}\n")
        except:
            pass
        try:
            f.write(f"Record Label: {mainData['attributes']['recordLabel']}\n")
        except:
            pass
        try:
            f.write(f"Track count: {mainData['attributes']['trackCount']}\n")
        except:
            pass
        try:
            f.write(f"Audio Traits: {', '.join(mainData['attributes']['audioTraits'])}\n")
        except:
            pass
        try:
            f.write(f"Compilation: {mainData['attributes']['isCompilation']}\n")
        except:
            pass
        try:
            f.write(f"Pre-release: {mainData['attributes']['isPrerelease']}\n")
        except:
            pass
        try:
            f.write(f"Single: {mainData['attributes']['isSingle']}\n")
        except:
            pass
        f.write(f"\nTrack list:\n")
        for songDetails in trackList:
            f.write(f"{songDetails[0]}. {songDetails[1]} - {songDetails[2]} ({songDetails[3]}) ({songDetails[4]})\n")
        f.write("\n")
        try:
            f.write(f"Tagline: {mainData['attributes']['editorialNotes']['tagline']}\n")
        except:
            pass
        try:
            f.write(f"Short phrase: {mainData['attributes']['editorialNotes']['short']}\n")
        except:
            pass
        try:
            albumBio = str(mainData['attributes']['editorialNotes']['standard'])
            f.write(f"Album bio:\n")
            f.write(textwrap.fill(albumBio, width=100))
        except:
            pass

    if info_only:
        print(f"✅ Album info saved to {albumFolderPath}")
    else:
        print(f"✅ Album assets saved to {albumFolderPath}")

# ==================== MUSIC VIDEO ASSETS ====================

def getMusicVideoAssets(videoID: str, info_only: bool = False):
    """Download music video assets"""
    videoParams = '?extend=editorialArtwork,editorialVideo,extendedAssetUrls,offers,seoDescription,seoTitle&format[resources]=map&include=artists,albums'
    response = requests.get(
        f"https://{apiURL}/v1/catalog/{countrycode}/music-videos/{videoID}{videoParams}",
        headers=apiHeader
    )
    responseJSON = response.json()

    if 'resources' not in responseJSON or 'music-videos' not in responseJSON['resources']:
        print(f"❌ Failed to retrieve data for video ID: {videoID}")
        return

    mainData = responseJSON['resources']['music-videos'][videoID]
    videoName = getCleanName(mainData['attributes']['name'])
    artistName = getCleanName(mainData['attributes']['artistName'])

    videoFolderPath = os.path.join(
        FOLDERPATH,
        "Music Video Assets",
        f"{artistName} - {videoName} - {currentDate}"
    )
    
    if not os.path.exists(videoFolderPath):
        os.makedirs(videoFolderPath)

    if not info_only:
        # Preview frame
        try:
            previewData = mainData['attributes']['artwork']
            width, height = previewData['width'], previewData['height']
            previewURL = previewData['url'].replace("{w}", str(width)).replace("{h}", str(height))
            print(f"📥 Downloading {videoName} ({countrycode}) - Preview Frame - {width}x{height}.jpg")
            previewReq = requests.get(url=previewURL, stream=True)
            with open(os.path.join(videoFolderPath, f"{videoName} ({countrycode}) - Preview Frame - {width}x{height}.jpg"), "wb") as f:
                f.write(previewReq.content)
        except Exception as e:
            print(f"❌ Failed to download preview frame: {e}")

    # Info file (always downloaded)
    print(f"📥 Downloading {videoName} ({countrycode}) - INFO.txt")
    with open(os.path.join(videoFolderPath, f"{videoName} ({countrycode}) - INFO.txt"), "w+", encoding="utf-8") as f:
        try:
            f.write(f"Name: {mainData['attributes']['name']}\n")
        except:
            pass
        try:
            f.write(f"Artist: {mainData['attributes']['artistName']}\n")
        except:
            pass
        try:
            f.write(f"Album: {mainData['attributes'].get('albumName', 'N/A')}\n")
        except:
            pass
        try:
            f.write(f"Release Date: {mainData['attributes'].get('releaseDate', 'Unknown')}\n")
        except:
            pass
        try:
            f.write(f"Duration: {convertMS(mainData['attributes']['durationInMillis'])}\n")
        except:
            pass
        try:
            f.write(f"URL: {mainData['attributes']['url']}\n")
        except:
            pass

    if info_only:
        print(f"✅ Music video info saved to {videoFolderPath}")
    else:
        print(f"✅ Music video assets saved to {videoFolderPath}")

def getAllMusicVideoIDs(artistID: str, offsetLink: str = "") -> List[str]:
    """Fetch all music video IDs of an artist"""
    videoList = []
    url = f"https://{apiURL}/v1/catalog/{countrycode}/artists/{artistID}/music-videos"
    if offsetLink:
        url = f"https://{apiURL}{offsetLink}"

    response = requests.get(url, headers=apiHeader).json()

    if 'data' in response:
        for video in response['data']:
            print(f"🎬 Found music video ID: {video['id']} - {video['attributes']['name']}")
            videoList.append(video['id'])

    if 'next' in response:
        videoList.extend(getAllMusicVideoIDs(artistID, response['next']))

    return videoList

# ==================== RADIO STATION ASSETS ====================

def getRadioStationAssets(stationID: str, info_only: bool = False):
    """Download radio station assets"""
    request = requests.get(
        url=f"https://{apiURL}/v1/catalog/{countrycode}/stations/{stationID}",
        headers=apiHeader
    )
    requestJSON = request.json()

    if 'data' not in requestJSON:
        print(f"❌ Failed to retrieve data for radio station ID: {stationID}")
        return

    mainData = requestJSON['data'][0]
    stationName = getCleanName(mainData['attributes']['name'])

    stationFolderPath = os.path.join(
        FOLDERPATH,
        "Radio Station Assets",
        getCleanName(f"{stationName} - {currentDate}")
    )
    
    if not os.path.exists(stationFolderPath):
        os.makedirs(stationFolderPath)

    if not info_only:
        # Artwork
        try:
            artwork = mainData['attributes']['artwork']
            width, height = artwork['width'], artwork['height']
            artworkURL = artwork['url'].replace("{w}", str(width)).replace("{h}", str(height))
            print(f"📥 Downloading {stationName} ({countrycode}) - Artwork - {width}x{height}.jpg")
            artworkReq = requests.get(url=artworkURL, stream=True)
            with open(os.path.join(stationFolderPath, f"{stationName} ({countrycode}) - Artwork - {width}x{height}.jpg"), "wb+") as f:
                f.write(artworkReq.content)
        except:
            print("⚠️ No artwork found for this station.")

    # Metadata (always downloaded)
    try:
        print(f"📥 Downloading {stationName} ({countrycode}) - INFO.txt")
        with open(os.path.join(stationFolderPath, f"{stationName} ({countrycode}) - INFO.txt"), "w+", encoding="utf-8") as f:
            f.write(f"Name: {mainData['attributes']['name']}\n")
            f.write(f"Description: {mainData['attributes'].get('description', 'No description')}\n")
            f.write(f"URL: {mainData['attributes'].get('url', 'No URL')}\n")
            f.write(f"Release Date: {mainData['attributes'].get('releaseDate', 'Unknown')}\n")
    except:
        print("⚠️ No metadata found for this station.")

    if info_only:
        print(f"✅ Radio station info saved to {stationFolderPath}")
    else:
        print(f"✅ Radio station assets saved to {stationFolderPath}")

# ==================== MAIN MENU ====================

def print_menu():
    """Display main menu"""
    print("\n" + "="*60)
    print("🎵 APPLE MUSIC API RIPPER (AMAR) V1 🎵")
    print("="*60)
    print("1. Download from URL (Artist/Album/Music Video/Station)")
    print("2. Search Catalog")
    print("3. View Charts")
    print("4. View Storefront Info")
    print("5. Extract New Token (Selenium)")
    print("6. Change Storefront")
    print("7. Exit")
    print("="*60)

def handle_url_download():
    """Handle URL-based download"""
    global countrycode, FOLDERPATH
    
    enteredLink = input("\n🔗 Enter Apple Music URL: ").strip()
    enteredLinkParts = enteredLink.split("/")
    
    try:
        current_cc = enteredLinkParts[3].lower()
        if len(current_cc) != 2:
            raise ValueError
    except Exception:
        current_cc = "us"
    
    countrycode = current_cc.upper()
    dynamic_storefronts = fetch_storefront_ids()

    # Ask if user wants info only
    infoOnlyQ = input("📄 Download only INFO files? (y/n): ").strip()[0:1].lower()
    info_only = (infoOnlyQ == "y")

    if "artist" in enteredLinkParts[4]:
        ripAlbumsQ = input("💽 Rip all albums? (y/n): ").strip()[0:1].lower()
        ripVideosQ = input("🎬 Rip all music videos? (y/n): ").strip()[0:1].lower()
        countryCodeQ = input(f"🌍 Country code (current: {countrycode}, 'all' for every storefront, Enter to keep): ").strip().lower()

        if countryCodeQ == "all":
            rest = [c for c in dynamic_storefronts if c != current_cc]
            loop_codes = [current_cc] + rest
        elif countryCodeQ in countryCodes:
            loop_codes = [countryCodeQ]
        else:
            loop_codes = [current_cc]

        for cc in loop_codes:
            countrycode = cc.upper()
            print(f"\n{'='*60}")
            print(f"🌍 Storefront: {countrycode} - {countryCodes.get(cc, cc).title()}")
            print(f"{'='*60}")

            getArtistAssets(enteredLinkParts[6], info_only)

            if ripVideosQ == "y":
                videoIDs = getAllMusicVideoIDs(enteredLinkParts[6])
                for videoID in videoIDs:
                    getMusicVideoAssets(videoID, info_only)

            if ripAlbumsQ == "y":
                albumList.clear()
                getAllAlbumIDs(enteredLinkParts[6])
                for albumID in albumList:
                    getAlbumAssets(albumID, info_only)

    elif "album" in enteredLinkParts[4]:
        countryCodeQ = input(f"🌍 Country code (current: {countrycode}, 'all' for every storefront, Enter to keep): ").strip().lower()
        
        if countryCodeQ == "all":
            rest = [c for c in dynamic_storefronts if c != current_cc]
            loop_codes = [current_cc] + rest
        elif countryCodeQ in countryCodes:
            loop_codes = [countryCodeQ]
        else:
            loop_codes = [current_cc]

        for cc in loop_codes:
            countrycode = cc.upper()
            print(f"\n🌍 Storefront: {countrycode} - {countryCodes.get(cc, cc).title()}")
            getAlbumAssets(enteredLinkParts[6], info_only)

    elif "music-video" in enteredLinkParts[4]:
        countryCodeQ = input(f"🌍 Country code (current: {countrycode}, 'all' for every storefront, Enter to keep): ").strip().lower()
        
        if countryCodeQ == "all":
            rest = [c for c in dynamic_storefronts if c != current_cc]
            loop_codes = [current_cc] + rest
        elif countryCodeQ in countryCodes:
            loop_codes = [countryCodeQ]
        else:
            loop_codes = [current_cc]

        for cc in loop_codes:
            countrycode = cc.upper()
            print(f"\n🌍 Storefront: {countrycode} - {countryCodes.get(cc, cc).title()}")
            getMusicVideoAssets(enteredLinkParts[6], info_only)

    elif "station" in enteredLinkParts[4]:
        countryCodeQ = input(f"🌍 Country code (current: {countrycode}, 'all' for every storefront, Enter to keep): ").strip().lower()
        
        if countryCodeQ == "all":
            rest = [c for c in dynamic_storefronts if c != current_cc]
            loop_codes = [current_cc] + rest
        elif countryCodeQ in countryCodes:
            loop_codes = [countryCodeQ]
        else:
            loop_codes = [current_cc]

        for cc in loop_codes:
            countrycode = cc.upper()
            print(f"\n🌍 Storefront: {countrycode} - {countryCodes.get(cc, cc).title()}")
            getRadioStationAssets(enteredLinkParts[6], info_only)

def handle_search():
    """Handle catalog search"""
    query = input("\n🔍 Enter search query: ").strip()
    if not query:
        print("❌ Search query cannot be empty.")
        return
    
    print("\n🔎 Search types:")
    print("1. All (songs, albums, artists)")
    print("2. Songs only")
    print("3. Albums only")
    print("4. Artists only")
    print("5. Music videos")
    print("6. Custom")
    
    choice = input("Select option (1-6): ").strip()
    
    types_map = {
        '1': ['songs', 'albums', 'artists'],
        '2': ['songs'],
        '3': ['albums'],
        '4': ['artists'],
        '5': ['music-videos'],
    }
    
    if choice in types_map:
        types = types_map[choice]
    elif choice == '6':
        custom = input("Enter types (comma-separated, e.g., songs,albums,artists): ").strip()
        types = [t.strip() for t in custom.split(',')]
    else:
        types = ['songs', 'albums', 'artists']
    
    print(f"\n🔎 Searching for '{query}' in storefront {countrycode}...")
    results = search_catalog(query, types)
    display_search_results(results)

def handle_charts():
    """Handle charts display"""
    print("\n📊 Chart types:")
    print("1. Songs")
    print("2. Albums")
    print("3. Both")
    print("4. Music Videos")
    
    choice = input("Select option (1-4): ").strip()
    
    types_map = {
        '1': ['songs'],
        '2': ['albums'],
        '3': ['songs', 'albums'],
        '4': ['music-videos']
    }
    
    chart_types = types_map.get(choice, ['songs', 'albums'])
    
    print(f"\n📊 Fetching charts for storefront {countrycode}...")
    charts = get_charts(chart_types)
    display_charts(charts)

def main():
    """Main program loop"""
    global countrycode, FOLDERPATH
    
    print("\n🎵 Initializing Apple Music API Ripper...")
    FOLDERPATH = setup_folder()
    print(f"📂 Save location: {FOLDERPATH}")
    
    while True:
        print_menu()
        choice = input("\n🎯 Select option: ").strip()
        
        if choice == '1':
            handle_url_download()
        elif choice == '2':
            handle_search()
        elif choice == '3':
            handle_charts()
        elif choice == '4':
            storefront_data = get_storefront_info()
            display_storefront_info(storefront_data)
        elif choice == '5':
            new_token = extract_token_with_selenium()
            if new_token:
                global token, apiHeader
                token = new_token
                apiHeader['Authorization'] = f"Bearer {token}"
                print("✅ Token updated successfully!")
        elif choice == '6':
            print(f"\nCurrent storefront: {countrycode}")
            new_cc = input("Enter new country code (2 letters): ").strip().lower()
            if new_cc in countryCodes:
                countrycode = new_cc.upper()
                print(f"✅ Storefront changed to {countrycode} - {countryCodes[new_cc]}")
            else:
                print("❌ Invalid country code.")
        elif choice == '7':
            print("\n👋 Thanks for using AMAR! Goodbye!")
            break
        else:
            print("❌ Invalid option. Please try again.")

if __name__ == "__main__":
    main()