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
from mapmanager.mapinfo import list_orphans, list_outdated, list_upgrades, list_extensions, redundant_bzs, list_unextracted
from functools import reduce, partial

sunrust_url = "http://142.44.142.152/fastdl/garrysmod/maps/" # we don't use urljoin so the trailing slash has to be there!

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
    fmt_exists = "{name: <{max}} {v: <10} {d: <10} ({s})"
    fmt_new    = "{name: <{max}} {v: <10} {d: <10} ({s}) NEW"
    
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
                                    s   = mb_fmt(new.size),
                                    d   = date_new))
        else:
            print(fmt_new.format(name = mapname,
                                 max  = max_name_len+2,
                                 v   = v_new,
                                 s   = mb_fmt(new.size),
                                 d   = date_new))
    print()
    print("total download size: ", mb_fmt(sum([u.new.size for u in upgrades])))

def orphans_summary(orphans):
    print("Found orphaned maps:")
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
    print("total freed up space: ", mb_fmt(sum([u.size for u in orphans])))

def redundant_bz2s_summary(redundant):# TODO: make a generic function for those, maybe even integrate with forall_prompt
    print("Found redundant .bz2 files!")
    max_name_len = 30
    fmt = "{name: <{max}} {v: <10} {d: <10} ({s})"
    for o in redundant:
        mapname = truncate(o.mapname, max_name_len)
        print(fmt.format(name = mapname,
                        max  = max_name_len+2,
                        v    = o.version if o.version else "???",
                        s   = mb_fmt(o.size),
                        d   = date_fmt(o.modified)))
    print()
    print("total freed up space: ", mb_fmt(sum([u.size for u in redundant])))

def unextracted_summary(unextracted):
    print("Found unextracted .bz2 files!")
    max_name_len = 30
    fmt = "{name: <{max}} {v: <10} {d: <10} ({s})"
    for o in unextracted:
        mapname = truncate(o.mapname, max_name_len)
        print(fmt.format(name = mapname,
                        max  = max_name_len+2,
                        v    = o.version if o.version else "???",
                        s   = mb_fmt(o.size),
                        d   = date_fmt(o.modified)))

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

def parse_args(): #TODO: use docopt?
    parser = argparse.ArgumentParser(description="Sync the downloads/maps/ directory with a server's listing")
    parser.add_argument('-u', '--url', help="The url of the server's maps directory", default=sunrust_url) #TODO: remove defaults, move to 'launcher' .sh and .bat files
    parser.add_argument('-d', '--mindate', help="During download/update phase, ignore serverside maps older than the given date. Currently accepts only ISO 8601 format, for example 2018-10-23.", default='2018-10-01')
    parser.add_argument('-s', '--minsize', help="During download/update phase, ignore serverside maps with size smaller than the given size. Example: mapmanager --minsize 10M", default='10M')
    parser.add_argument('-m', '--maps', help="Path to the maps/ directory. If not given, MapManager will try to find Garry's Mod automatically.")
    parser.add_argument('operations', help="A list of operations to perform. Possible choices are: all, update, clean_orphans, clean_compressed. Default: all", default=['all'] ,nargs='*') #Extract intentionally not mentioned; see comment on extract_all()
    return parser.parse_args()

def main():
    args = parse_args()
    minsize = human2bytes(args.minsize) #TODO: Shouldn't this be in parse_args too?!
    mindate = read_date(args.mindate)
    url = args.url
    op_names = args.operations
    mapsdir = args.maps if args.maps else os.path.join(find_gmod(), "garrysmod/download/maps/")
    op_all = op_names == ['all']

    local_mapinfo = get_local(mapsdir)
    remote_mapinfo = get_remote(url)
    print(sorted(remote_mapinfo, key=operator.attrgetter('modified')))
    by_ext = list_extensions(local_mapinfo)

    def upgradeall(): #TODO: We should be consistent about calling it 'update' or 'upgrade'. Upgrade seems better from package-management point of view but I'm not sure if it fits in this context.
        upgrades = list_upgrades(local_mapinfo, remote_mapinfo, mindate, minsize)
        return forall_prompt(partial(upgrade, url=url, mapsdir=mapsdir), upgrades, upgrade_sumary, "Continue upgrade?", "Upgrade canceled!")
    def remove_orphans():
        orphans = list_orphans(local_mapinfo, remote_mapinfo)
        return forall_prompt(partial(remove_map, mapsdir=mapsdir), orphans, orphans_summary, "Remove all orphan maps?", "No orphans deleted.")
    def remove_redundant_bz2s():
        redundant = redundant_bzs(by_ext)
        return forall_prompt(partial(remove_map,mapsdir=mapsdir), redundant, redundant_bz2s_summary, "Remove all redundant files?", "No .bz2 files deleted.")
    def extract_all(): #I wouldn't worry about this one too much since it shouldn't ever be triggered in normal circumstances. Mostly for internal use (cleaning up the mess from previous, bad, implementations of the upgrade downloader)
        unextracted = list_unextracted(by_ext)
        return forall_prompt(partial(extract_file,mapsdir=mapsdir), unextracted, unextracted_summary, "Extract all?", "No files extracted.")
    op_lookup = {'upgrade': upgradeall, 'clean_orphans': remove_orphans, 'clean_compressed': remove_redundant_bz2s, 'extract': extract_all}
    operations = [upgradeall,remove_orphans,remove_redundant_bz2s] if op_all else [op_lookup[x] for x in op_names]
    active = accum_actions(operations) #TODO: Make sure file removal doesn't interfere with later operations. Currently local_mapinfo is not updated after file removal.
    if not active:
        print("Nothing to do!")

if __name__ == "__main__":
    main()
