#!/usr/bin/env python3
import htmllistparse
import time
import os
import sys
import bz2
import tempfile

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

def download(url, name, chunk_size=4096):  #adapted from https://stackoverflow.com/a/2030027
    """Download data from the url to a temporary file and returns the file object. Also takes a name to be used for reporting download progress."""
    with urlopen(url) as response: #TODO: Error handling!
        total_size = response.getheader('Content-Length').strip()
        total_size = int(total_size)
        bytes_so_far = 0
        time_start = time.time()
        tmp = tempfile.TemporaryFile()

        while True: #TODO: Use iterators?
            chunk = response.read(chunk_size)
            bytes_so_far += len(chunk)
            elapsed = time.time()-time_start
            speed = bytes_so_far/elapsed

            if not chunk:
                break

            tmp.write(chunk)

            percent = float(bytes_so_far) / total_size
            percent = round(percent*100, 2)
            sys.stdout.write("{} - Downloaded {}b of {}b ({:0.2f}%)   avg speed: {:0.2f} Kb/s   ETA: {}s       \r".format(name, mb_fmt(bytes_so_far), mb_fmt(total_size), percent, speed/1024, round(total_size/speed-elapsed)))
    sys.stdout.write('\n')
    return tmp

def extract_to(f, path):
    """Reads bz2 data from the file object and writes it to the given path."""
    f.seek(0)
    decompressor = bz2.BZ2Decompressor()
    with open(path, 'wb') as f_out:
        while True:
            chunk = f.read(1024)
            if not chunk:
                break
            data = decompressor.decompress(chunk)
            f_out.write(data)

def upgrade(u):
    """downloads an upgrade and writes it to disk."""
    filename = mapinfo_filename(u.new, False)
    tmp = download(url+filename+'.bsp.bz2', u.new.mapname)
    print("decompressing...")
    extract_to(tmp, os.path.join(mapsdir,filename+'.bsp')) #Assumption: server gives us only compressed maps

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

def get_local(mapsdir):
    localfiles = os.listdir(mapsdir)
    local_mapinfo = [read_local_mapinfo(f) for f in localfiles]
    return [x for x in local_mapinfo if x and is_zs_map(x)]# filter out non-zs maps and Nones from non-bsp files
def get_remote(url):
    _, listing = htmllistparse.fetch_listing(url, timeout=30)
    return [parse_remote_mapinfo(l) for l in listing]

def find_upgrades(local_mapinfo, remote_mapinfo):
    remote_filtered = filter(should_check, remote_mapinfo)
    remote_filtered = sorted(remote_filtered, key=attrgetter('modified'), reverse=True)

    fresh_remote = newest_versions(remote_filtered)
    fresh_local = newest_versions(local_mapinfo)
    outdated = list_outdated(fresh_local, fresh_remote)
    return [make_upgrade(fresh_local, fresh_remote, x) for x in outdated]

local_mapinfo = get_local(mapsdir)
remote_mapinfo = get_remote(url)

active = False

upgrades = find_upgrades(local_mapinfo, remote_mapinfo)
active = forall_prompt(upgrade, upgrades, upgrade_sumary, "Continue upgrade?", "Upgrade canceled!") or active #python short-circuits 'or' so order matters

orphans = list_orphans(local_mapinfo, remote_mapinfo)
active = forall_prompt(remove_map, orphans, orphans_summary, "Remove all orphan maps?", "No orphans deleted.") or active

by_ext = find_extensions(local_mapinfo)
redundant = redundant_bzs(by_ext)
active = forall_prompt(remove_map, redundant, redundant_bz2s_summary, "Remove all redundant files?", "No .bz2 files deleted.") or active

if not active:
    print("Nothing to do!")