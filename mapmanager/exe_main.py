import traceback
import sys
from mapmanager import cli

from configparser import ConfigParser, NoSectionError

cfg = ConfigParser()

try:
    cfg.read('config.cfg')
    args = dict(cfg.items('args'))
except NoSectionError:
    print('h')
    args = None
    sys.exit(1)

try:
    cli.main(args)
except Exception:
    traceback.print_exc()
print("Press any key...")
input()