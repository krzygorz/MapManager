"""
Everything related to processing MapInfos lives here.
Pure functions only!
"""

import re
from operator import attrgetter
from collections import namedtuple
from collections import defaultdict, namedtuple
MapInfo = namedtuple('MapInfo',['mapname','version','modified','size'])# We *might* want to change this into a class
#note: remote and local sizes will be different since remote files are compressed!
#also, sizes are approximate since we are just parsing the apache file listing which gives us the size in MBs

# examples                ex zs_18       _v2b           _2018           _2018_a2                _a2_3
versionformat = re.compile("(?<!zs)_(?:v?[0-9]+[a-z]?|(?:20[0-9]{2})(?:_[a-z][0-9])?|(?:[a-z][0-9])(?:_[0-9])?)$") #big suffer
def parse_version(mapname):
    version_match = re.search(versionformat, mapname)
    if not version_match:
        return (mapname,None)
    else:
        version_pos = version_match.span()[0]
        mapname_pure = mapname[:version_pos]
        version = mapname[version_pos+1:] # +1 to remove the underscore
        return (mapname_pure, version)

def bestversion(xs):
    """Return the MapInfo with newer version (modification date)."""
    return max(xs,key = attrgetter('modified'))
def newest_versions(listing):
    """Given a MapInfo list return a dictionary d associating every map name with MapInfo of the newest version of that map."""
    mapversions = mk_multidict(attrgetter('mapname'), listing)
    return mapvals(bestversion, mapversions)

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

MapUpgrade = namedtuple('MapUpgrade', ['old', 'new'])
def make_upgrade(local, remote, x):
    r = remote[x]
    l = local[x] if x in local else None
    return MapUpgrade(l,r)