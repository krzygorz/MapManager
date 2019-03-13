"""
Everything related to processing MapInfos.
"""

import re
import time
from operator import attrgetter
from collections import namedtuple, defaultdict
from mapmanager.meme import inverse_multidict, mapvalues, list_subtract, filter_none
from dataclasses import dataclass
#MapInfo = namedtuple('MapInfo',['mapname','version','modified','size','ext'])# We *might* want to change this into a class

@dataclass(unsafe_hash=True)
class MapInfo:
    """Represents a .bsp or .bsp.bz2 file in the download/maps directory."""
    mapname: str
    version: str
    modified: int
    size: int
    ext: str

    def filename(self, withext=True):
        """Recover map filename given a MapInfo"""
        mapname = self.mapname
        if self.version is not None:
            mapname+='_'+self.version
        if withext:
            return mapname+self.ext
        else:
            return mapname

#note: remote and local sizes will be different since remote files are compressed!
#also, sizes are approximate since we are just parsing the apache file listing which gives us the size in MBs

def weak_eq_mapinfo(a,b):
    return a.mapname == b.mapname and a.version == b.version

# examples                   zs_18       _v2b           _2018           _2018_a2                _a2_3
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
    mapversions = inverse_multidict(attrgetter('mapname'), listing)
    return mapvalues(bestversion, mapversions)

MapUpgrade = namedtuple('MapUpgrade', ['old', 'new'])
def make_upgrade(local, remote, x):
    """Find the map with name x in local and remote and construct an upgrade."""
    r = remote[x]
    l = local[x] if x in local else None
    return MapUpgrade(l,r)

def is_zs_map(mapinfo):
    mapname = mapinfo.mapname
    return mapname.startswith('zs_') or mapname.startswith('ze_')
    
def should_check(x, mindate, minsize):
    return x.size >= minsize and x.modified >= mindate and is_zs_map(x)

def list_outdated(local, remote):
    """Compare local and remote versions of maps and return a list of possible updates"""

    def is_outdated(mapinfo):
        mapname = mapinfo.mapname
        return mapname not in local or local[mapname].modified < remote[mapname].modified
    return [m.mapname for m in remote.values() if is_outdated(m)] #map(adfsa, filter(is_outdated, remote.values()))

def list_orphans(local, remote):
    return list_subtract(local,remote, weak_eq_mapinfo)

def list_upgrades(local_mapinfo, remote_mapinfo, mindate=0, minsize=0):
    remote_filtered = [x for x in remote_mapinfo if should_check(x, mindate, minsize)]
    remote_filtered = sorted(remote_filtered, key=attrgetter('modified'), reverse=True)

    fresh_remote = newest_versions(remote_filtered)
    fresh_local = newest_versions(local_mapinfo)
    outdated = list_outdated(fresh_local, fresh_remote)
    return [make_upgrade(fresh_local, fresh_remote, x) for x in outdated]

def list_extensions(mapinfos):
    """Returns a nested dict that associates mapname+'_'+version and file extension with the corresponding MapInfo"""
    ret = defaultdict(dict)# this could probably be somehow merged with multidict (as a nested multidict) but I'm not sure if that's a good idea
    for m in mapinfos:
        ret[m.filename(False)][m.ext] = m
    return ret

def redundant_bzs(by_ext):
    """Returns a list of MapInfos that point to compressed files that are no longer needed."""
    def f(x):
        """returns """
        if '.bsp' in x:
            return x.get('.bsp.bz2')
    return filter_none(map(f,by_ext.values()))

def list_unextracted(by_ext):
    """Returns a list of MapInfos that point to compressed files that are no longer needed."""
    def f(x):
        """returns """
        if '.bsp.bz2' in x and not '.bsp' in x:
            return x['.bsp.bz2']
    return filter_none(map(f,by_ext.values()))

def list_local_outdated(local):
    return list_orphans(local, newest_versions(local).values())