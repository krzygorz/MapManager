"""Everything related to finding map files in the download/maps/ directory and parsing the info."""

import time
import os
import sys
import bz2
import tempfile
import platform
import itertools

from urllib.request import urlopen
from operator import attrgetter
from collections import namedtuple, defaultdict
from functools import partial

from mapmanager.htmllistparse import fetch_listing
from mapmanager.keyvalues import KeyValues
from mapmanager.mapinfo import MapInfo, parse_version, is_zs_map
from mapmanager.meme import filter_none

gmoddir = 'steamapps/common/GarrysMod/'
def has_gmod(path):
    fullpath = os.path.join(path, gmoddir)# is this reliable?
    return os.path.isdir(fullpath)
    
def find_gmod():
    p = platform.system()
    if p == 'Linux':
        main_lib = os.path.expanduser('~/.steam/steam/')
    elif p == 'Windows':
        main_lib = r'C:\Program Files (x86)\Steam'

    if has_gmod(main_lib):
        return os.path.join(main_lib, gmoddir)

    try:
        kv = KeyValues(filename=os.path.join(main_lib, 'steamapps/libraryfolders.vdf'))
    except FileNotFoundError:
        print("Couldn't find libraryfolders.vdf", file=sys.stderr)
        return []

    library_folders = kv['LibraryFolders'] #it would be nice to rewrite this using map and any
    for i in itertools.count(1):
        key = str(i)
        if key in library_folders:
            path = library_folders[key]
            if has_gmod(path):
                return os.path.join(path, gmoddir)
        else:
            return []

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

def read_local_mapinfo(filename, mapsdir):
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

def download(url, reporter_class, chunk_size=4096):  #adapted from https://stackoverflow.com/a/2030027
    """Download data from the url to a temporary file and returns the file object. Also takes a reporter object to use to display progress."""
    with urlopen(url) as response: #TODO: Error handling!
        total_size = response.getheader('Content-Length').strip()
        total_size = int(total_size)
        reporter = reporter_class(total_size)
        bytes_so_far = 0
        tmp = tempfile.TemporaryFile()

        while True: #TODO: Use iterators?
            chunk = response.read(chunk_size)
            if not chunk:
                break
            bytes_so_far += len(chunk)
            reporter.report(bytes_so_far)

            tmp.write(chunk)

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

def upgrade(u, url, mapsdir, make_reporter): #TODO: all the operations that need url or mapsdir should probably be methods of a new class
    """downloads an upgrade and writes it to disk."""
    filename = u.new.filename(False)
    tmp = download(url+filename+'.bsp.bz2', make_reporter(u.new.mapname))
    print("decompressing...")
    extract_to(tmp, os.path.join(mapsdir,filename+'.bsp')) #Assumption: server gives us only compressed maps

def remove_map(mapinfo, mapsdir):
    os.remove(os.path.join(mapsdir,mapinfo.filename()))
def extract_file(mapinfo, mapsdir):
    print("Sorry, extraction not implemented yet! ({})".format(mapinfo.mapname))

def get_local(mapsdir):
    localfiles = os.listdir(mapsdir)
    local_mapinfo = [read_local_mapinfo(f, mapsdir) for f in localfiles]
    return [x for x in local_mapinfo if x and is_zs_map(x)]# filter out non-zs maps and Nones from non-bsp files
def get_remote(url):
    _, listing = fetch_listing(url, timeout=30) #TODO: use HTTP content-length to determine size accurately
    return [parse_remote_mapinfo(l) for l in listing]