# MapManager
MapManager is a tool for keeping your `garrysmod/downloads/maps/` directory in sync with a server's listing.
## Features
* Download new maps and new versions of maps
* Remove old versions of maps and maps removed from the server's listing
## Screenshots
![](https://i.imgur.com/POssDOr.png "MapManager running on Linux, with fresh gmod instance")
![](https://i.imgur.com/eHO0DUP.jpg "MapManager on Windows")
## Installation from source
```
git clone https://github.com/krzygorz/MapManager.git
cd MapManager
pip install --user -e .
```
## Usage
```
usage: mapmanager [-h] [-u URL] [-d MINDATE] [-s MINSIZE] [-m MAPS] [operations ...]

Sync the downloads/maps/ directory with a server's listing

positional arguments:
  operations            A list of operations to perform. Possible choices are:
                        update, clean_orphans, clean_compressed, clean_outdated.

optional arguments:
  -h, --help            show this help message and exit
  -u URL, --url URL     The url of the server's maps directory
  -d MINDATE, --mindate MINDATE
                        During download/update phase, ignore serverside maps
                        older than the given date. Currently accepts only ISO
                        8601 format, for example 2018-10-23.
  -s MINSIZE, --minsize MINSIZE
                        During download/update phase, ignore serverside maps
                        with size smaller than the given size. Example:
                        mapmanager --minsize 10M
  -m MAPS, --maps MAPS  Path to the maps/ directory. If not given, MapManager
                        will try to find Garry's Mod automatically.
```

## Configuration
If you don't want to create a shell script that calls mapmanager with some arguments, you can use the config file. It has to be placed in the same directory as exe (or in the pwd of shell you're launching mapmanager from) and called `config.cfg`. Currently it is only used to specify arguments to added on start, for example:
```
[args]
maps=<path to gmod>/garrysmod/downloads/maps
minsize = 50M
operations = update clean_orphans clean_outdated clean_compressed
```

## Operations
* **update** - Fetch the listing of server's maps, compare it with the local directory and download maps that are on the remote listing but not on the local one. If the server provides several versions of the same map, download only the most recent one. This does not create any .bsp.bz2 files, all maps are decompressed immediately 
* **clean_orphans** - Remove the maps that are in the local but not in the remote listing. Note that this doesn't remove old versions that are still on the server's listing.
* **clean_compressed** - Remove all .bsp.bz2 files that have a matching .bz2 file (that is, if they have already been extracted)
* **clean_outdated** - Remove all maps that have a better version on the *local* listing. For example if you have both `zs_obj_npst_v6.bsp` and `zs_obj_npst_v7.bsp` downloaded, v6 will be removed, even if the server still provides it for whatever reason.

If no operations are given, update and clean_compressed will be executed.

## Todo
* Currently the code is optimized for the Sunrust ZS server. It might remove other server's maps but it should be possible to add support to any server that has a public listing of its maps
* Proper exception handling.
* Allow the user to choose to use parsed version strings to compare version.
* Rewrite the entire thing to Haskell because why not
