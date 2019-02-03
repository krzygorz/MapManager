"""Everything related to finding map files in the /download/maps directory and parsing the info."""

import htmllistparse
import time
import os
import sys
import bz2
import tempfile

from urllib.request import urlopen
from operator import attrgetter
from collections import namedtuple, defaultdict
from mapinfo import MapInfo, parse_version, is_zs_map
from meme import filter_none

steamdir = '/mnt/shared/SteamLibrary/' #TODO: Automatic detection?
gmoddir = 'steamapps/common/GarrysMod/'
#mapsdir = os.path.join(steamdir, gmoddir, 'garrysmod/download/maps')
mapsdir = 'fake-mapdir/'

map_exts = ['.bsp.bz2','.bsp']
def split_extension(filename):
    for e in map_exts:
        if filename.endswith(e):
            return filename[:-len(e)], e
    return None, None

def mb_fmt(x):
    """Given a size in bytes returns a string that says the size in MBs"""
    factor = 1024*1024
    mbs = round(x/factor)
    return "{}M".format(mbs)

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

            percent = float(bytes_so_far) / total_size #TODO: move all the cli stuff into cli.py
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

url = "http://142.44.142.152/fastdl/garrysmod/maps/"
def upgrade(u):
    """downloads an upgrade and writes it to disk."""
    filename = u.new.filename(False)
    tmp = download(url+filename+'.bsp.bz2', u.new.mapname)
    print("decompressing...")
    extract_to(tmp, os.path.join(mapsdir,filename+'.bsp')) #Assumption: server gives us only compressed maps

def remove_map(mapinfo):
    os.remove(os.path.join(mapsdir,mapinfo.filename()))

def get_local(mapsdir):
    localfiles = os.listdir(mapsdir)
    local_mapinfo = [read_local_mapinfo(f) for f in localfiles]
    return [x for x in local_mapinfo if x and is_zs_map(x)]# filter out non-zs maps and Nones from non-bsp files
def get_remote(url):
    _, listing = htmllistparse.fetch_listing(url, timeout=30)
    return [parse_remote_mapinfo(l) for l in listing]