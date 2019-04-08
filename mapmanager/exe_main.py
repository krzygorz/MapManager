import traceback
import sys
from mapmanager import cli

from configparser import ConfigParser, NoSectionError

<<<<<<< HEAD
cfg = ConfigParser() #TODO: move this to cli.py

try:
    cfg.read('config.cfg')
    args = dict(cfg.items('args'))
except NoSectionError:
    args = {}

=======
>>>>>>> a06cf8b33481c9562ade4a1793a6edf1a1c7f4bc
try:
    cfg = ConfigParser() #TODO: move this to cli.py
    #TODO: JSON might be a better choice

    try:
        cfg.read('config.cfg')
        args = dict(cfg.items('args'))
    except NoSectionError:
        args = {}

    if 'operations' in args:
        args['operations'] = args['operations'].split()

    cli.main(args)
except Exception:
    traceback.print_exc()
print("Press return to close mapmanager...")
input()