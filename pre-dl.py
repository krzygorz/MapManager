import htmllistparse
import time
import os
from collections import defaultdict
from urllib.request import urlopen

from mapinfo import MapInfo, parse_version
from test import testmaps, testmaps_parsed

url = "http://142.44.142.152/fastdl/garrysmod/maps/" # we don't use urljoin so the trailing slash has to be there!

steamdir = '/mnt/shared/SteamLibrary/'
gmoddir = 'steamapps/common/GarrysMod/'
mapsdir = os.path.join(steamdir, gmoddir, 'garrysmod/download/maps')

minsize = htmllistparse.human2bytes('10M')
mindate = time.strptime("01 Nov 2018", "%d %b %Y")

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

def attr2fun(attr): #fuck OOP
    return lambda x: x.__getattribute__(attr)
def mapvals(f, dct):
    """Apply f to values of dict and return the result dict (keys stay the same)."""
    return {k: f(v) for k, v in dct.items()}
def bestversion(xs):
    """Return the MapInfo with newer version (modification date)."""
    return max(xs,key = attr2fun('modified'))
def newest_versions(listing):
    """Given a MapInfo list return a dictionary d associating every map name with MapInfo of the newest version of that map."""
    mapversions = mk_multidict(attr2fun('mapname'), listing)
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
    def is_outdated(mapinfo):
        mapname = mapinfo.mapname
        return mapname not in local or local[mapname].size < remote[mapname].size
    return filter(is_outdated, remote.values())

def mapinfo_filename(mapinfo):
    mapname = mapinfo.mapname
    if mapinfo.version is not None:
        mapname+='_'+mapinfo.version
    return mapname+'.bsp.bz2'

localfiles = os.listdir(mapsdir)
local_mapinfo = list(map(read_local_mapinfo, localfiles)) #read_local_mapinfo is impure, let's force it just to be safe

cwd, listing = htmllistparse.fetch_listing(url, timeout=30)
#listing = sorted(listing, key = lambda x: x.modified, reverse=True)
listing = filter(should_check, listing)
listing = map(parse_remote_mapinfo, listing)

fresh_remote_maps = newest_versions(listing)
fresh_local_maps = newest_versions(local_mapinfo)
outdated = list_outdated(fresh_local_maps, fresh_remote_maps)

for i in outdated:
    filename = mapinfo_filename(i)
    with urlopen(url+filename) as response, open('fake-mapdir/'+filename, 'wb') as f:
        f.write(response.read())
