import re
from collections import namedtuple
MapInfo = namedtuple('MapInfo',['mapname','version','modified','size']) #note: remote and local sizes will be different since remote files are compressed!

versionformat = re.compile("_(?:v?[0-9]+[a-z]?|(?:20[0-9]{2})(?:_[a-z][0-9])?|(?:[a-z][0-9])(?:_[0-9])?)$") #big suffer
def parse_version(mapname):
    version_match = re.search(versionformat, mapname)
    if not version_match:
        return (mapname,None)
    else:
        version_pos = version_match.span()[0]
        mapname_pure = mapname[:version_pos]
        version = mapname[version_pos+1:]
        return (mapname_pure, version)
