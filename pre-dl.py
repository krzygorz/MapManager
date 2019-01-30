#!/usr/bin/env python3
import htmllistparse
import time
import os
import sys
import bz2

from urllib.request import urlopen
from operator import attrgetter
from collections import namedtuple, defaultdict
from mapinfo import MapInfo, parse_version, newest_versions, make_upgrade, list_orphans, list_outdated
from test import testmaps, testmaps_parsed
from meme import lmap, lfilter, filter_none
from cli import forall_prompt, orphans_summary, upgrade_sumary, mb_fmt, redundant_bz2s_summary

url = "http://142.44.142.152/fastdl/garrysmod/maps/" # we don't use urljoin so the trailing slash has to be there!

steamdir = '/mnt/shared/SteamLibrary/'
gmoddir = 'steamapps/common/GarrysMod/'
#mapsdir = os.path.join(steamdir, gmoddir, 'garrysmod/download/maps')
mapsdir = 'fake-mapdir/'

minsize = htmllistparse.human2bytes('10M')
mindate = time.mktime(time.strptime("01 Dec 2018", "%d %b %Y"))# time is complicated
#its not like timezones matter that much here so whatever im too lazy to learn the proper way to handle it

def is_zs_map(mapinfo):
    mapname = mapinfo.mapname
    return mapname.startswith('zs_') or mapname.startswith('ze_')

def should_check(x):
    return x.size >= minsize and x.modified >= mindate and is_zs_map(x)

map_exts = ['.bsp.bz2','.bsp']
def split_extension(filename):
    for e in map_exts:
        if filename.endswith(e):
            return filename[:-len(e)], e
    return None, None

def read_local_mapinfo(filename):
    """Make a MapInfo based on file metadata. filename is relative to the maps directory."""
    rawname, ext = split_extension(filename)
    if not rawname: 
        return None

    mapname, version = parse_version(rawname)
    fullpath = os.path.join(mapsdir,filename)
    mtime = os.path.getmtime(fullpath)
    size = os.path.getsize(fullpath)
    return MapInfo(mapname, version, mtime, size, ext)
def parse_remote_mapinfo(entry):
    """Make a MapInfo based on FileEntry metadata."""
    rawname, ext = split_extension(entry.name)
    if not rawname: 
        return None
    
    mapname, version = parse_version(rawname)
    mtime = time.mktime(entry.modified)
    return MapInfo(mapname, version, mtime, entry.size, ext)

def mapinfo_filename(mapinfo, withext = True): #it would probably be good to have this as a class method
    """Recover map filename given a MapInfo"""
    mapname = mapinfo.mapname
    if mapinfo.version is not None:
        mapname+='_'+mapinfo.version
    if withext:
        return mapname+mapinfo.ext
    else:
        return mapname

#FIXME: what is going on with the decreasing speed?!
def download(response, name, chunk_size=8192):  #adapted from https://stackoverflow.com/a/2030027
    """given a response, downloads the data (to memory) and returns it. Also takes a name to be used for reporting download progress."""
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
def upgrade(u):
    """downloads an upgrade and writes it to disk."""
    global writing
    filename = mapinfo_filename(u.new, False)
    with urlopen(url+filename+'.bsp.bz2') as response: #Assumption: server gives us only compressed maps
        data = download(response, u.new.mapname)
        writing = True
        sys.stdout.write("decompressing...")
        sys.stdout.flush()
        decompressed = bz2.decompress(data) #TODO: Use temporary files. We are using way more memory than we should
        with open(os.path.join(mapsdir,filename+'.bsp'), 'wb') as f:
            f.write(decompressed)
            writing = False # should this be in a finally block?

def remove_map(mapinfo):
    os.remove(os.path.join(mapsdir,mapinfo_filename(mapinfo)))


def find_extensions(mapinfos):
    """returns a dict that associates mapname+'_'+version with all the MapInfos that have this plus an extension as file name"""
    ret = defaultdict(dict)# this could probably be somehow merged with multidict but I'm not sure if that is a good idea
    for m in mapinfos:
        ret[mapinfo_filename(m, False)][m.ext] = m
    return ret

def redundant_bzs(by_ext):
    def f(x):
        """returns """
        if '.bsp' in x:
            return x.get('.bsp.bz2')
    return filter_none(map(f,by_ext.values()))

localfiles = os.listdir(mapsdir)
local_mapinfo = [read_local_mapinfo(f) for f in localfiles]
local_mapinfo = [x for x in local_mapinfo if x and is_zs_map(x)]# filter out non-zs maps and Nones from non-bsp files
local_mapinfo = lfilter(is_zs_map, local_mapinfo)

cwd, listing = htmllistparse.fetch_listing(url, timeout=30)
remote_mapinfo = lmap(parse_remote_mapinfo, listing)
remote_filtered = filter(should_check, remote_mapinfo)
remote_filtered = sorted(remote_filtered, key=attrgetter('modified'), reverse=True)

fresh_remote = newest_versions(remote_filtered)
fresh_local = newest_versions(local_mapinfo)
outdated = list_outdated(fresh_local, fresh_remote)

active = False

upgrades = [make_upgrade(fresh_local, fresh_remote, x) for x in outdated]
active = forall_prompt(upgrade, upgrades, upgrade_sumary, "Continue upgrade?", "Upgrade canceled!") or active #python short-circuits 'or' so order matters

orphans = list_orphans(local_mapinfo, remote_mapinfo)
active = forall_prompt(remove_map, orphans, orphans_summary, "Remove all orphan maps?", "No orphans deleted.") or active

by_ext = find_extensions(local_mapinfo)
redundant = redundant_bzs(by_ext)
active = forall_prompt(remove_map, redundant, redundant_bz2s_summary, "Remove all redundant files?", "No .bz2 files deleted.") or active

if not active:
    print("Nothing to do!")