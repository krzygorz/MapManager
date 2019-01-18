import re
from collections import namedtuple
MapInfo = namedtuple('MapInfo',['mapname','version','modified','size'])#TODO: We probably want to change this into a class
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
