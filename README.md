# MapManager
MapManager is a tool for keeping your `garrysmod/downloads/maps/` directory in sync with a server's listing.
## Features
* Download new maps and new versions of maps
* Remove old versions of maps and maps removed from the server's listing
## Usage
```
usage: mapmanager [-h] [-u URL] [-d MINDATE] [-s MINSIZE] [-m MAPS]
                  [operations [operations ...]]

Sync the downloads/maps/ directory with a server's listing

positional arguments:
  operations            A list of operations to perform. Possible choices are:
                        all, update, clean_orphans, clean_compressed. Default:
                        all

optional arguments:
  -h, --help            show this help message and exit
  -u URL, --url URL     The url of the server's maps directory
  -d MINDATE, --mindate MINDATE
                        During download/update phase, ignore serverside maps
                        older than the given date.
  -s MINSIZE, --minsize MINSIZE
                        During download/update phase, ignore serverside maps
                        with size smaller than the given size. Example:
                        mapmanager --minsize 10M
  -m MAPS, --maps MAPS  Path to the maps/ directory. If not given, MapManager
                        will try to find Garry's Mod automatically.
```
## Todo
* Currently the code is optimised for the Sunrust ZS server. It should be easy to generalize it to other fastdl servers but they could use different naming conventions etc...
* Proper exception handling.
* Better CLI.
* An easy way to launch it for those who fear commandline.
* Rewrite the entire thing to Haskell because why not