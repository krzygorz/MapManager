import htmllistparse
import time
import os
import sys
import signal

from urllib.request import urlopen
from operator import attrgetter
from collections import namedtuple
from mapinfo import MapInfo, parse_version, newest_versions, make_upgrade, list_orphans, list_outdated
from test import testmaps, testmaps_parsed
from meme import lmap, lfilter, filter_none

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
def strip_extension(filename):
    for e in map_exts:
        if filename.endswith(e):
            return filename[:-len(e)]
    return None

def read_local_mapinfo(filename):
    """Make a MapInfo based on file metadata. filename is relative to the maps directory."""
    rawname = strip_extension(filename)
    if not rawname: 
        return None

    mapname, version = parse_version(rawname)
    fullpath = os.path.join(mapsdir,filename)
    mtime = os.path.getmtime(fullpath)
    size = os.path.getsize(fullpath)
    return MapInfo(mapname, version, mtime, size)
def parse_remote_mapinfo(entry):
    """Make a MapInfo based on FileEntry metadata."""
    mapname, version = parse_version(strip_extension(entry.name))
    mtime = time.mktime(entry.modified)
    return MapInfo(mapname, version, mtime, entry.size)

def mapinfo_filename(mapinfo):
    """Recover map filename given a MapInfo"""
    mapname = mapinfo.mapname
    if mapinfo.version is not None:
        mapname+='_'+mapinfo.version
    return mapname+'.bsp.bz2'

def mb_fmt(x):
    """Given a size in bytes returns a string that says the size in MBs"""
    factor = 1024*1024
    mbs = round(x/factor)
    return "{}M".format(mbs)
def date_fmt(x):
    return time.strftime('%x', time.gmtime(x))

def truncate(s, n):
    if len(s) < n:
        return s
    else:
        return s[:n-3]+"..."

def upgrade_sumary(upgrades):
    print("Available upgrades:")
    max_name_len = 30
    fmt_exists = "{name: <{max}} {v: <10} {d1: <10} ({s1}) -> ({s2})"
    fmt_new    = "{name: <{max}} {v: <10} {d1: <10} ({s2}) NEW"
    
    for u in upgrades:
        old = u.old
        new = u.new
        mapname = truncate(new.mapname, max_name_len)
        v_old = old.version if old and old.version else "???"
        v_new = new.version if new.version else "???"

        date_new = date_fmt(u.new.modified)
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

def orphans_summary(orphans):
    print("Found orphaned packages:")
    max_name_len = 30
    fmt = "{name: <{max}} {v: <10} {d: <10} ({s})"
    for o in orphans:
        mapname = truncate(o.mapname, max_name_len)
        print(fmt.format(name = mapname,
                        max  = max_name_len+2,
                        v    = o.version if o.version else "???",
                        s   = mb_fmt(o.size),
                        d   = date_fmt(o.modified)))
    print()
    print("total download size: ", mb_fmt(sum([u.new.size for u in upgrades])))


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
def upgrade_all(upgrades):
    """Given a list of available upgrades download them and write them to disk."""
    global writing
    for u in upgrades:
        filename = mapinfo_filename(u.new)
        with urlopen(url+filename) as response:
            data = download(response, u.new.mapname)
            writing = True
            with open(os.path.join(mapsdir,filename), 'wb') as f:
                f.write(data)
                writing = False # should this be in a finally block?

def remove_map(mapinfo):
    os.remove(os.path.join(mapsdir,mapinfo_filename(mapinfo)))

def query_yes_no(question, default="yes"):# http://code.activestate.com/recipes/577058/
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")

localfiles = os.listdir(mapsdir)
local_mapinfo = lmap(read_local_mapinfo, localfiles)
local_mapinfo = list(filter_none(local_mapinfo))# filter out Nones from non-bsp files
local_mapinfo = lfilter(is_zs_map, local_mapinfo)

cwd, listing = htmllistparse.fetch_listing(url, timeout=30)
remote_mapinfo = lmap(parse_remote_mapinfo, listing)
remote_filtered = filter(should_check, remote_mapinfo)
remote_filtered = sorted(remote_filtered, key=attrgetter('modified'), reverse=True)

fresh_remote = newest_versions(remote_filtered)
fresh_local = newest_versions(local_mapinfo)
outdated = list_outdated(fresh_local, fresh_remote)

upgrades = [make_upgrade(fresh_local, fresh_remote, x) for x in outdated]

def signal_handler(sig, frame):
    print()# avoid the \r
    if writing:# this shouldn't happen in normal circumstances
        print('DOWNLOAD INTERRUPTED WHILE WRITING TO DISK!')
        print("Since currently pre-dl uses file modification date to compare version, there is a chance that the file was only partially written and next time you run pre-dl it will think it's up to date")
        print("you might want to check the file size manually")
        sys.exit(1)
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

noop = True

if len(upgrades) > 0:
    upgrade_sumary(upgrades)
    if query_yes_no("continue upgrade?"):
        noop = False
        upgrade_all(upgrades)
    else:
        print("upgrade cancelled.")

orphans = list(list_orphans(local_mapinfo, remote_mapinfo))
if len(orphans) > 0:
    print()
    orphans_summary(orphans)
    if query_yes_no("remove orphans?"):
        noop = False
        for o in orphans:
            remove_map(o)
        print("done!")
    else:
        print("no orphans deleted.")

if noop:
    print("Nothing to do!")