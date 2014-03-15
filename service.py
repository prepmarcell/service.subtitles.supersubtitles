# -*- coding: utf-8 -*- 

import os
import sys
import urllib
import shutil
import unicodedata
import os.path
import re

import requests2
import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin


__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
#__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")
__temp__ = xbmc.translatePath(os.path.join(__profile__, 'temp')).decode("utf-8")

#sys.path.append (__resource__)

BASE_URL = 'http://www.feliratok.info/index.php'

TAGS = {
    'WEB\-DL',
    'PROPER',
    'REPACK'
}

QUALITIES = {
    'HDTV',
    '720p',
    '1080p',
    'DVDRip',
    'BRRip',
    'BDRip'
}

RELEASERS = {
    '2HD',
    'AFG',
    'ASAP',
    'BiA',
    'DIMENSION',
    'EVOLVE',
    'FoV',
    'FQM',
    'IMMERSE',
    'KiNGS',
    'LOL',
    'REMARKABLE',
    'ORENJI',
    'TLA'
}
HEADERS = {'User-Agent': 'xbmc subtitle plugin'}

ARCHIVE_EXTENSIONS = {
    '.zip',
    '.cbz',
    '.rar',
    '.cbr'
}

LANGUAGES = {
    "albán": "Albanian",
    "arab": "Arabic",
    "bolgár": "Bulgarian",
    "kínai": "Chinese",
    "horvát": "Croatian",
    "cseh": "Czech",
    "dán": "Danish",
    "holland": "Dutch",
    "angol": "English",
    "észt": "Estonian",
    "finn": "Finnish",
    "francia": "French",
    "német": "German",
    "görög": "Greek",
    "héber": "Hebrew",
    "hindi": "Hindi",
    "magyar": "Hungarian",
    "olasz": "Italian",
    "japán": "Japanese",
    "koreai": "Korean",
    "lett": "Latvian",
    "litván": "Lithuanian",
    "macedón": "Macedonian",
    "norvég": "Norwegian",
    "lengyel": "Polish",
    "portugál": "Portuguese",
    "román": "Romanian",
    "orosz": "Russian",
    "szerb": "Serbian",
    "szlovák": "Slovak",
    "szlovén": "Slovenian",
    "spanyol": "Spanish",
    "svéd": "Swedish",
    "török": "Turkish",
}


def recreate_dir(path):
    if xbmcvfs.exists(path):
        shutil.rmtree(path)
    xbmcvfs.mkdirs(path)


def normalize_string(str):
    return unicodedata.normalize('NFKD', unicode(unicode(str, 'utf-8'))).encode('ascii', 'ignore')


def lang_hun2eng(hunlang):
    return LANGUAGES[hunlang.lower()]


def log(msg, level):
    xbmc.log((u"### [%s] - %s" % (__scriptname__, msg,)).encode('utf-8'), level=level)


def infolog(msg):
    log(msg, xbmc.LOGNOTICE)


def errorlog(msg):
    log(msg, xbmc.LOGERROR)


def debuglog(msg):
    log(msg, xbmc.LOGDEBUG)
    #log(msg, xbmc.LOGNOTICE)


def query_data(params):
    r = requests2.get(BASE_URL, params=params, headers=HEADERS)
    debuglog(r.url)
    try:
        return r.json()
    except ValueError as e:
        errorlog(e.message)
        return None


def notification(id):
    xbmc.executebuiltin(u'Notification(%s,%s,%s,%s)' % (
        __scriptname__,
        __language__(id),
        2000,
        os.path.join(__cwd__, "icon.png")
    )
    )


def get_showid(item):
    ret = None
    qparams = {'action': 'autoname', 'nyelv': '0', 'term': item['tvshow']}
    datas = query_data(qparams)
    if datas:
        if item['year']:
            year = str(item['year'])
            for data in datas:
                if year in data['name']:
                    ret = data['ID']
                    break
        else:
            ret = datas[0]['ID']

    if ret and '-100' in ret:
        ret = None

    return ret


def convert(item):
    ret = {'filename': item['fnev'], 'name': item['nev'], 'language_hun': item['language'], 'id': item['felirat'],
           'uploader': item['feltolto'], 'hearing': False, 'language_eng': lang_hun2eng(item['language'])}

    score = int(item['pontos_talalat'], 2)
    ret['rating'] = str(score * 5 / 7)
    ret['sync'] = score >= 6
    ret['flag'] = xbmc.convertLanguage(ret['language_eng'], xbmc.ISO_639_1)
    ret['seasonpack'] = bool(item['evadpakk'])

    return ret


def set_param_if_filename_contains(data, params, paramname, items):
    compare = data['filename'].lower()
    for item in items:
        if item.lower() in compare:
            params[paramname] = item
            return item
    return None


def search_subtitles(item):
    showid = get_showid(item)
    if not showid:
        debuglog("No id found for %s" % item['tvshow'])
        return None

    qparams = {'action': 'xbmc', 'sid': showid, 'ev': item['season'], 'rtol': item['episode']};

    set_param_if_filename_contains(item, qparams, 'relj', TAGS)
    set_param_if_filename_contains(item, qparams, 'relf', QUALITIES)
    set_param_if_filename_contains(item, qparams, 'relr', RELEASERS)

    data = query_data(qparams)

    if not data:
        debuglog("No subtitle found for %s" % item['tvshow'])
        return None

    searchlist = []
    for st in data.values():
        converted = convert(st)
        if converted['language_eng'] in item['languages']:
            searchlist.append(converted)

    searchlist.sort(key=lambda k: k['rating'], reverse=True)
    return searchlist


def search(item):
    debuglog(item)
    subtitles_list = search_subtitles(item)

    if subtitles_list:
        for it in subtitles_list:
            #label="%s | %s | %s"%(it['name'], it['filename'], it['uploader'])
            label = "%s [%s]" % (it['filename'], it['uploader'])
            listitem = xbmcgui.ListItem(label=it["language_eng"],
                                        label2=label,
                                        iconImage=it["rating"],
                                        thumbnailImage=it["flag"]
            )
            listitem.setProperty("sync", ("false", "true")[it["sync"]])
            listitem.setProperty("hearing_imp", ("false", "true")[it.get("hearing", False)])

            qparams = {'action': 'download', 'id': it['id'], 'filename': it['filename']}
            url = "plugin://%s/?%s" % (__scriptid__, urllib.urlencode(qparams))

            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)


def is_archive(filename):
    if filename:
        for ext in ARCHIVE_EXTENSIONS:
            if filename.endswith(ext):
                return True
    return False


def extract(archive):
    basename = os.path.basename(archive).replace('.', '_')
    extracted = os.path.join(__temp__, basename)
    xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (archive, extracted)).encode('utf-8'), True)
    return extracted


def download_file(item):
    localfile = os.path.join(__temp__, item['filename'].decode("utf-8"))
    qparams = {'action': 'letolt', 'felirat': item['id']}
    r = requests2.get(BASE_URL, params=qparams, headers=HEADERS, stream=True)
    debuglog(r.url)

    with open(localfile, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=1024):
            fd.write(chunk)
        fd.flush()

    return localfile


def is_match(item, filename):
    pattern = r'^.*S?(?P<season>\d+)([x_-]|\.)+E?(?P<episode>\d+).*$'
    match = re.search(pattern, filename, re.I)
    if match:
        season = int(item['season'])
        episode = int(item['episode'])
        fs = int(match.group('season'))
        fe = int(match.group('episode'))
        if season == fs and episode == fe:
            return True

    return False


def download(item):
    debuglog(item)
    subtitle = None
    downloaded = download_file(item)

    if is_archive(downloaded):
        extracted = extract(downloaded)
        for file in xbmcvfs.listdir(extracted)[1]:
            file = os.path.join(extracted, file.decode('utf-8'))
            filename = os.path.basename(file)
            if is_match(item, filename):
                subtitle = file
                break
    else:
        subtitle = downloaded

    if subtitle:
        listitem = xbmcgui.ListItem(label=subtitle)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=subtitle, listitem=listitem, isFolder=False)
        notification(32501)


def setup_tvshow_data(item):
    tvshow = normalize_string(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))
    if tvshow:
        item['tvshow'] = tvshow
        item['season'] = str(xbmc.getInfoLabel("VideoPlayer.Season"))
        item['episode'] = str(xbmc.getInfoLabel("VideoPlayer.Episode"))
    else:
        title = xbmc.getCleanMovieTitle(item['file_original_path'])[0]
        pattern = r'^(?P<title>.+)S(?P<season>\d+)E(?P<episode>\d+)$'
        match = re.search(pattern, title, re.I)
        item['tvshow'] = match.group('title').strip()
        item['season'] = match.group('season')
        item['episode'] = match.group('episode')

    return item


def setup_path(item):
    item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))
    if item['file_original_path'].find("http") > -1:
        item['temp'] = True

    elif item['file_original_path'].find("rar://") > -1:
        item['rar'] = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

    elif item['file_original_path'].find("stack://") > -1:
        item['stack'] = True
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]

    return item


def get_params(string=""):
    param = []
    if string == "":
        paramstring = sys.argv[2]
    else:
        paramstring = string
    if len(paramstring) >= 2:
        params = paramstring
        cleanedparams = params.replace('?', '')
        if params[len(params) - 1] == '/':
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]

    return param


recreate_dir(__temp__)
params = get_params()

debuglog(params)

if params['action'] == 'search':
    debuglog("action 'search' called")
    item = {'temp': False, 'rar': False, 'stack': False, 'year': xbmc.getInfoLabel("VideoPlayer.Year"),
            'title': normalize_string(xbmc.getInfoLabel("VideoPlayer.OriginalTitle")),
            'languages': []}

    for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
        item['languages'].append(lang)

    if item['title'] == "":
        debuglog("VideoPlayer.OriginalTitle not found")
        item['title'] = normalize_string(xbmc.getInfoLabel("VideoPlayer.Title"))
    setup_path(item)
    item['filename'] = os.path.basename(item['file_original_path'])

    item = setup_tvshow_data(item)

    if item['episode'].lower().find("s") > -1:  # Check if season is "Special"
        item['season'] = "0"  #
        item['episode'] = item['episode'][-1:]

    search(item)

elif params['action'] == 'download':
    item = {'id': params['id'], 'filename': params['filename']}
    item = setup_tvshow_data(setup_path(item))
    download(item)

elif params['action'] == 'manualsearch':
    notification(32502)

xbmcplugin.endOfDirectory(int(sys.argv[1]))
