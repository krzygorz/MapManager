import htmllistparse
import time
import os
import sys
import signal

from urllib.request import urlopen
from operator import attrgetter
from collections import namedtuple
from mapinfo import MapInfo, parse_version, strip_extension, newest_versions, make_upgrade
from test import testmaps, testmaps_parsed

url = "http://142.44.142.152/fastdl/garrysmod/maps/" # we don't use urljoin so the trailing slash has to be there!

steamdir = '/mnt/shared/SteamLibrary/'
gmoddir = 'steamapps/common/GarrysMod/'
#mapsdir = os.path.join(steamdir, gmoddir, 'garrysmod/download/maps')
mapsdir = 'fake-mapdir/'

minsize = htmllistparse.human2bytes('10M')
mindate = time.strptime("01 Dec 2018", "%d %b %Y")

def is_zs_map(mapname):
    return mapname.startswith('zs_') or mapname.startswith('ze_')

def should_check(x):
    return x.size >= minsize and x.modified >= mindate and is_zs_map(x.name)

def read_local_mapinfo(filename):
    """Make a MapInfo based on file metadata. filename is relative to the maps directory."""
    mapname, version = parse_version(strip_extension(filename))

    fullpath = os.path.join(mapsdir,filename)
    mtime = os.path.getmtime(fullpath)
    size = os.path.getsize(fullpath)
    return MapInfo(mapname, version, mtime, size)
def parse_remote_mapinfo(entry):
    """Make a MapInfo based on FileEntry metadata."""
    mapname, version = parse_version(strip_extension(entry.name))
    mtime = time.mktime(entry.modified)
    return MapInfo(mapname, version, mtime, entry.size)
    
def list_outdated(local, remote):
    """Compare local and remote versions of maps and return a list of possible updates"""

    def is_outdated(mapinfo):
        mapname = mapinfo.mapname
        return mapname not in local or local[mapname].modified < remote[mapname].modified
    return [m.mapname for m in remote.values() if is_outdated(m)] #map(filter(is_outdated, remote.values()))

def mapinfo_filename(mapinfo):
    """Recover map filename given a MapInfo"""
    mapname = mapinfo.mapname
    if mapinfo.version is not None:
        mapname+='_'+mapinfo.version
    return mapname+'.bsp.bz2'

def mb_fmt(x):
    factor = 1024*1024
    mbs = round(x/factor)
    return "{}M".format(mbs)

def truncate(s, n):
    if len(s) < n:
        return s
    else:
        return s[:n-3]+"..."

def upgrade_sumary(upgrades):
    max_name_len = 30
    fmt_exists = "{name: <{max}} {v: <10} {d1: <10} ({s1}) -> ({s2})"
    fmt_new    = "{name: <{max}} {v: <10} {d1: <10} ({s2}) NEW"
    
    for u in upgrades:
        old = u.old
        new = u.new
        mapname = truncate(new.mapname, max_name_len)
        v_old = old.version if old and old.version else "???"
        v_new = new.version if new.version else "???"

        date_new = time.strftime('%x', time.gmtime(u.new.modified))
        if old:
            print(fmt_exists.format(name = mapname,
                                    max  = max_name_len+2,
                                    v    = "{} -> {}".format(v_old, v_new),
                                    s1   = mb_fmt(old.size),
                                    s2   = mb_fmt(new.size),
                                    d1   = date_new))
        else:
            print(fmt_new.format(name = mapname,
                                 max  = max_name_len+2,
                                 v   = v_new,
                                 s2   = mb_fmt(new.size),
                                 d1   = date_new))
    print()
    print("total download size: ", mb_fmt(sum([u.new.size for u in upgrades])))

def download(response, name, chunk_size=8192):  #adapted from https://stackoverflow.com/a/2030027
    total_size = response.getheader('Content-Length').strip()
    total_size = int(total_size)
    bytes_so_far = 0
    time_start = time.time()
    data = b""

    while True:
        chunk = response.read(chunk_size)
        bytes_so_far += len(chunk)
        elapsed = time.time()-time_start
        speed = bytes_so_far/elapsed

        if not chunk:
             break

        data += chunk
        percent = float(bytes_so_far) / total_size
        percent = round(percent*100, 2)
        sys.stdout.write("{} - Downloaded {}b of {}b ({:0.2f}%)   avg speed: {:0.2f} Kb/s   ETA: {}s       \r".format(name, mb_fmt(bytes_so_far), mb_fmt(total_size), percent, speed/1024, round(total_size/speed-elapsed)))

        if bytes_so_far >= total_size:
            sys.stdout.write('\n')

    return data

writing = False
def upgrade_all(upgrades):
    global writing
    for u in upgrades:
        filename = mapinfo_filename(u.new)
        with urlopen(url+filename) as response:
            data = download(response, u.new.mapname)
            writing = True
            with open('fake-mapdir/'+filename, 'wb') as f:
                f.write(data)
                writing = False # should this be in a finally block? 


localfiles = os.listdir(mapsdir)
local_mapinfo = list(map(read_local_mapinfo, localfiles)) #read_local_mapinfo is impure, let's force it just to be safe

cwd, listing = htmllistparse.fetch_listing(url, timeout=30)
listing = filter(should_check, listing)
listing = sorted(listing, key=attrgetter('modified'), reverse=True)
listing = map(parse_remote_mapinfo, listing)

fresh_remote = newest_versions(listing)
fresh_local = newest_versions(local_mapinfo)
outdated = list_outdated(fresh_local, fresh_remote)

if len(outdated) == 0:
    print("Everything is up to date!")
    sys.exit(0)

upgrades = [make_upgrade(fresh_local, fresh_remote, x) for x in outdated]
upgrade_sumary(upgrades)

def signal_handler(sig, frame):
    print()# avoid the \r
    if writing:
        print('DOWNLOAD INTERRUPTED WHILE WRITING TO DISK!')
        print("Since currently pre-dl uses file modification date to compare version, there is a chance that the file was only partially written and next time you run pre-dl it will think it's up to date")
        print("you might want to check the file size manually")
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

upgrade_all(upgrades)