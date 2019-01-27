"""
Everything related to processing MapInfos lives here.
Pure functions only!
"""

import re
from operator import attrgetter
from collections import namedtuple
from collections import namedtuple
from meme import mk_multidict, mapvalues, list_subtract
MapInfo = namedtuple('MapInfo',['mapname','version','modified','size','ext'])# We *might* want to change this into a class
#note: remote and local sizes will be different since remote files are compressed!
#also, sizes are approximate since we are just parsing the apache file listing which gives us the size in MBs

def weak_eq_mapinfo(a,b):
    return a.mapname == b.mapname and a.version == b.version

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

def bestversion(xs):# TODO: compare by version?
    """Return the MapInfo with newer version (modification date)."""
    return max(xs,key = attrgetter('modified'))
def newest_versions(listing):
    """Given a MapInfo list return a dictionary d associating every map name with MapInfo of the newest version of that map."""
    mapversions = mk_multidict(attrgetter('mapname'), listing)
    return mapvalues(bestversion, mapversions)

MapUpgrade = namedtuple('MapUpgrade', ['old', 'new'])
def make_upgrade(local, remote, x):
    """Find the map with name x in local and remote and construct an upgrade."""
    r = remote[x]
    l = local[x] if x in local else None
    return MapUpgrade(l,r)

def list_outdated(local, remote):
    """Compare local and remote versions of maps and return a list of possible updates"""

    def is_outdated(mapinfo):
        mapname = mapinfo.mapname
        return mapname not in local or local[mapname].modified < remote[mapname].modified
    return [m.mapname for m in remote.values() if is_outdated(m)] #map(adfsa, filter(is_outdated, remote.values()))

def list_orphans(local, remote):
    return list_subtract(local,remote, weak_eq_mapinfo)

#maybe there should be a class/namedtuple for (local, remote) pairs?
#on the other hand it could make it even easier to use the wrong version of mapinfo lists (we use several kinds of)