# MapManager
MapManager is a tool for keeping your `garrysmod/downloads/maps/` directory in sync with a server's listing.
## Features
* Download new maps and new versions of maps
* Remove old versions of maps and maps removed from the server's listing
## Screenshots
![](https://i.imgur.com/POssDOr.png "MapManager running on Linux, with fresh gmod instance")
![](https://i.imgur.com/eHO0DUP.jpg "MapManager on Windows")
## Installation
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
maps=fake-mapdir
minsize = 50M
```

## Todo
* Currently the code is optimised for the Sunrust ZS server. It might remove other server's maps but it should be possible to add support to any server that has a public listing of its maps
* Proper exception handling.
* Allow the user to choose to use parsed version strings to compare version.
* Rewrite the entire thing to Haskell because why not
