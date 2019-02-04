"""
Arg parsing, interactive input/output.
"""

import time
import sys

from htmllistparse import human2bytes
from mapfiles import get_local, get_remote, upgrade, remove_map, mb_fmt
from mapinfo import list_orphans, list_outdated, list_upgrades, list_extensions, redundant_bzs
from functools import reduce, partial

url = "http://142.44.142.152/fastdl/garrysmod/maps/" # we don't use urljoin so the trailing slash has to be there!

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

minsize = human2bytes('10M')
mindate = time.mktime(time.strptime("01 Dec 2018", "%d %b %Y"))# time is complicated
#its not like timezones matter that much here so whatever im too lazy to learn the proper way to handle it

mapsdir = "fake-mapdir"
local_mapinfo = get_local(mapsdir)
remote_mapinfo = get_remote(url)

def upgradeall():
    upgrades = list_upgrades(local_mapinfo, remote_mapinfo, mindate, minsize)
    return forall_prompt(partial(upgrade, url=url, mapsdir=mapsdir), upgrades, upgrade_sumary, "Continue upgrade?", "Upgrade canceled!")
def remove_orphans():
    orphans = list_orphans(local_mapinfo, remote_mapinfo)
    return forall_prompt(partial(remove_map, mapsdir=mapsdir), orphans, orphans_summary, "Remove all orphan maps?", "No orphans deleted.")
def remove_redundant_bz2s():
    by_ext = list_extensions(local_mapinfo)
    redundant = redundant_bzs(by_ext)
    return forall_prompt(partial(remove_map,mapsdir=mapsdir), redundant, redundant_bz2s_summary, "Remove all redundant files?", "No .bz2 files deleted.")
active = accum_actions([upgradeall, remove_orphans, remove_redundant_bz2s])
if not active:
    print("Nothing to do!")