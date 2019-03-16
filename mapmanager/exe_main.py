import traceback
import sys
from mapmanager import cli

from configparser import ConfigParser, NoSectionError

cfg = ConfigParser() #TODO: move this to cli.py

try:
    cfg.read('config.cfg')
    args = dict(cfg.items('args'))
except NoSectionError:
    args = {}
    
try:
    cli.main(args)
except Exception:
    traceback.print_exc()
print("Press any key...")
input()