import htmllistparse
import time
import os
from collections import defaultdict, namedtuple
from urllib.request import urlopen
from operator import attrgetter

from mapinfo import MapInfo, parse_version
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

map_exts = ['.bsp.bz2','.bsp']
def strip_extension(filename):
    for e in map_exts:
        if filename.endswith(e):
            return filename[:-len(e)]
    raise ValueError(f"map {filename} doesn't end with any of {map_exts}")

def mk_multidict(keyfun, xs):
    """Returns a dict d such that for every k, d[k] is the set of xs with keyfun(x) equal to k."""
    ret = defaultdict(set)
    for x in xs: #no obvious way to do this in functional style
        ret[keyfun(x)].add(x)
    return ret

def mapvals(f, dct):
    """Apply f to values of dict and return the result dict (keys stay the same)."""
    return {k: f(v) for k, v in dct.items()}
def bestversion(xs):
    """Return the MapInfo with newer version (modification date)."""
    return max(xs,key = attrgetter('modified'))
def newest_versions(listing):
    """Given a MapInfo list return a dictionary d associating every map name with MapInfo of the newest version of that map."""
    mapversions = mk_multidict(attrgetter('mapname'), listing)
    return mapvals(bestversion, mapversions)

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

MapUpgrade = namedtuple('MapUpgrade', ['old', 'new'])

def upgrade_all(upgrades):
    for u in upgrades:
        filename = mapinfo_filename(u.old)
        print('downloading '+filename) #TODO: progress bar with ETA, summary before download start
        with urlopen(url+filename) as response, open('fake-mapdir/'+filename, 'wb') as f:
            f.write(response.read())

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
    fmt_exists = "{name} : {v1} ({s1}) -> {v2} ({s2})"
    fmt_new = "NEW: {name: <{max}} : {v2: <10} ({s2})"
    

    for u in upgrades:
        old = u.old
        new = u.new
        mapname = truncate(new.mapname, max_name_len)
        v_old = old.version if old and old.version else "???"
        v_new = new.version if new.version else "???"
        if old:
            print(fmt_exists.format(name = mapname,
                                    max  = max_name_len+2,
                                    v1   = v_old,
                                    v2   = v_new,
                                    s1   = mb_fmt(old.size),
                                    s2   = mb_fmt(new.size)))
        else:
            print(fmt_new.format(name = mapname,
                                 max  = max_name_len+2,
                                 v2   = v_new,
                                 s2   = mb_fmt(new.size)))
    print()
    print("total download size: ", mb_fmt(sum([u.new.size for u in upgrades])))


localfiles = os.listdir(mapsdir)
local_mapinfo = list(map(read_local_mapinfo, localfiles)) #read_local_mapinfo is impure, let's force it just to be safe

cwd, listing = htmllistparse.fetch_listing(url, timeout=30)
listing = filter(should_check, listing)
listing = map(parse_remote_mapinfo, listing)

fresh_remote = newest_versions(listing)
fresh_local = newest_versions(local_mapinfo)
outdated = list_outdated(fresh_local, fresh_remote)

def make_upgrade(local, remote, x):
    r = remote[x]
    if x in local:
        l = local[x]
    else:
        l = None
    return MapUpgrade(l,r)

upgrades = [make_upgrade(fresh_local, fresh_remote, x) for x in outdated]
upgrade_sumary(upgrades)
