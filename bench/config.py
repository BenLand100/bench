'''Module to hold configuration information (i.e. load once, import anywhere)
'''
import sys
from ConfigParser import ConfigParser
from base64 import b64encode


def parse_file(config_file):
    '''One-time access call, pretty hacky!
    '''
    config_parser = ConfigParser()
    config_parser.read(config_file)
    # For now parse all options (should probably be explicit)
    # and use setattr to set them as module attributes!
    this_module = sys.modules[__name__]
    for (key, value) in config_parser.items('main'):
        setattr(this_module, key, value)
    setattr(this_module, 'qsub', dict(config_parser.items('qsub')))
    setattr(this_module, 'dirac', dict(config_parser.items('dirac')))
    # Add in the db_auth field
    setattr(this_module, 'db_auth', b64encode('{0}:{1}'.format(db_user, db_password)))


