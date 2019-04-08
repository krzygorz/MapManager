"""
Arg parsing, interactive input/output.
"""

import argparse
import datetime
import operator
import time
import sys
import os

from mapmanager.htmllistparse import human2bytes
from mapmanager.mapfiles import get_local, get_remote, upgrade, remove_map, mb_fmt, extract_file, find_gmod
from mapmanager.mapinfo import list_orphans, list_outdated, list_upgrades, list_extensions, redundant_bzs, list_unextracted, list_local_outdated
from functools import reduce, partial

sunrust_url = "http://142.44.142.152/fastdl/garrysmod/maps/" # we don't use urljoin so the trailing slash has to be there!

def date_fmt(x):
    return time.strftime('%x', time.gmtime(x))

def truncate(s, n):
    if len(s) < n:
        return s
    else:
        return s[:n-3]+"..."

def map_summary(m, version_string=None, max_name_len=30):
    mapname = truncate(m.mapname, max_name_len)
    fmt_args = {
        'name': mapname,
        'max': max_name_len+2,
        'v': version_string or m.version or "???",
        's': mb_fmt(m.size),
        'd': date_fmt(m.modified)
    }
    return "{name: <{max}} {v: <10} {d: <10} ({s})".format(**fmt_args)

def upgrade_sumary(upgrades):
    print("Available upgrades:")
    
    for u in upgrades:
        old = u.old
        new = u.new

        v_old = old.version if old and old.version else "???" #for new maps, u.old is None
        v_new = new.version or "???"
        
        v = "{} -> {}".format(v_old, v_new) if old else None
        summary = map_summary(new, version_string=v)
        if not old:
            summary += " NEW"
        
        print(summary)
    print()
    print("total download size: ", mb_fmt(sum([u.new.size for u in upgrades])))

def generic_removal_sumary(maps, prompt, total_prefix="total freed up space: "):
    print(prompt)
    for m in maps:
        print(map_summary(m))
    print()
    print(total_prefix, mb_fmt(sum([u.size for u in maps])))

def orphans_summary(orphans):
    generic_removal_sumary(orphans, "Found orphaned maps:")
def outdated_summary(outdated):
    generic_removal_sumary(outdated, "Found outdated maps:")
def redundant_bz2s_summary(redundant):
    generic_removal_sumary(redundant, "Found redundant .bz2 files:")

def unextracted_summary(unextracted):
    print("Found unextracted .bz2 files!")
    for u in unextracted:
        print(map_summary(u))

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

def forall_prompt(action, xs, summary, prompt, cancelmsg, donemsg="Done!"):
    if len(xs) > 0:
        summary(xs)
        if query_yes_no(prompt):
            for x in xs:
                action(x)
            print(donemsg)
            return True
        else:
            print(cancelmsg)
            return False
    else:
        return False

def accum_actions(actions):
    """Run all the actions in the array and return True if at least one of them returned True. Otherwise return False."""
    def run(f):
        return f()
    def or_(a,b): #operator.or_ doesn't like None
        return a or b
    return reduce(or_, map(run, actions), False) #can't just use any() since it short-circuits

def read_date(x):
    return datetime.datetime.fromisoformat(x).timestamp()# TODO: Is this the proper way to do it? Same with reading dates from server listing.

def make_reporter(name):
    return partial(Reporter, name)
class Reporter:
    def __init__(self, name, total_size):
        self.total_size = total_size
        self.time_start = time.time()
        self.name = name
        self.fmt = "{name} - Downloaded {so_far}b of {total}b ({percent:5.2f}%)   avg speed: {speed:0.2f} Kb/s   ETA: {eta}s       \r"
        self.average_speed = 2000 * 1024 # 2 MB/s start speed
        self.smoothing_factor = 0.7
    def report(self, bytes_so_far):
        elapsed = time.time()-self.time_start
        if elapsed != 0:
            speed = bytes_so_far/elapsed
        else:
            speed = 1 #this should prevent division by zero

        self.average_speed = self.smoothing_factor * speed + (1-self.smoothing_factor) * self.average_speed; #https://stackoverflow.com/a/3841706

        percent = 100 * bytes_so_far / self.total_size
        eta = self.total_size/self.average_speed - elapsed
        fmt_args = {
            'name': self.name,
            'so_far': mb_fmt(bytes_so_far),
            'total': mb_fmt(self.total_size),
            'percent': percent,
            'speed': self.average_speed/1024,
            'eta': round(eta)
        }
        sys.stdout.write(self.fmt.format(**fmt_args))


def parse_args(): #TODO: use docopt?
    parser = argparse.ArgumentParser(description="Sync the downloads/maps/ directory with a server's listing",
                                     usage="mapmanager [-h] [-u URL] [-d MINDATE] [-s MINSIZE] [-m MAPS] [operations ...]")
    parser.add_argument('-u', '--url', help="The url of the server's maps directory", default=sunrust_url)
    parser.add_argument('-d', '--mindate', help="During download/update phase, ignore serverside maps older than the given date. Currently accepts only ISO 8601 format, for example 2018-10-23.", default='2018-10-01')
    parser.add_argument('-s', '--minsize', help="During download/update phase, ignore serverside maps with size smaller than the given size. Example: mapmanager --minsize 10M", default='10M')
    parser.add_argument('-m', '--maps', help="Path to the maps/ directory. If not given, MapManager will try to find Garry's Mod automatically.")
    parser.add_argument('operations', help="A list of operations to perform. Possible choices are: update, clean_orphans, clean_compressed, clean_outdated.", default=['update', 'clean_compressed'] ,nargs='*') #Extract intentionally not mentioned; see comment on extract_all()
    return parser.parse_args()

def main(config={}):
    args = vars(parse_args())
    args.update(config)
    
    minsize = human2bytes(args['minsize']) #TODO: Shouldn't this be in parse_args too?!
    mindate = read_date(args['mindate'])
    url = args['url']
    op_names = args['operations']
    mapsdir = args['maps'] or os.path.join(find_gmod(), "garrysmod/download/maps/")
    print("The maps directory is: "+mapsdir)

    local_mapinfo = get_local(mapsdir)
    remote_mapinfo = get_remote(url)
    by_ext = list_extensions(local_mapinfo)

    def upgradeall(): #TODO: We should be consistent about calling it 'update' or 'upgrade'. Upgrade seems better from package-management point of view but I'm not sure if it fits in this context.
        upgrades = list_upgrades(local_mapinfo, remote_mapinfo, mindate, minsize)
        return forall_prompt(partial(upgrade, url=url, mapsdir=mapsdir, make_reporter=make_reporter), upgrades, upgrade_sumary, "Continue upgrade?", "Upgrade canceled!")
    def remove_orphans():
        orphans = list_orphans(local_mapinfo, remote_mapinfo)
        return forall_prompt(partial(remove_map, mapsdir=mapsdir), orphans, orphans_summary, "Remove all orphan maps?", "No orphans deleted.")
    def remove_outdated():
        outdated = list_local_outdated(local_mapinfo)
        return forall_prompt(partial(remove_map, mapsdir=mapsdir), outdated, outdated_summary, "Remove all outdated maps?", "No maps deleted.")
    def remove_redundant_bz2s():
        redundant = redundant_bzs(by_ext)
        return forall_prompt(partial(remove_map,mapsdir=mapsdir), redundant, redundant_bz2s_summary, "Remove all redundant files?", "No .bz2 files deleted.")
    def extract_all(): #I wouldn't worry about this one too much since it shouldn't ever be triggered in normal circumstances. Mostly for internal use (cleaning up the mess from previous, bad, implementations of the upgrade downloader)
        unextracted = list_unextracted(by_ext)
        return forall_prompt(partial(extract_file,mapsdir=mapsdir), unextracted, unextracted_summary, "Extract all?", "No files extracted.")
    
    op_lookup = {'update': upgradeall, 'clean_orphans': remove_orphans, 'clean_compressed': remove_redundant_bz2s, 'extract': extract_all, 'clean_outdated': remove_outdated}
    operations = [op_lookup[x] for x in op_names]
    active = accum_actions(operations) #TODO: Make sure file removal doesn't interfere with later operations. Currently local_mapinfo is not updated after file removal.
    #Also, currently mapmanager has to be run twice to remove old versions of just downloaded maps
    if not active:
        print("Nothing to do!")

if __name__ == "__main__":
    main()
