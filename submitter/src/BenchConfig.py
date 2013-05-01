############################################
# BenchConfig.py:
#    Class containing the config options
# for benchmarking.
# Author: Matt Mottram 
#         m.mottram@sussex.ac.uk
############################################

import os
import ConfigParser
import optparse

class BenchConfig(object):
    def __init__(self):
        self.db_server = None
        self.db_name = None
        self.db_user = None
        self.db_password = None
        self.email_address = None
        self.email_password = None
        self.sw_directory = None
        self.env_file = None
    def read_config(self,config_path):
        if not os.path.exists(config_path):
            raise Exception,'no config file'
        config_parser = ConfigParser.ConfigParser()
        config_parser.read(config_path)
        required_options = ['db_server','db_name','db_user',
                            'db_password','email_address',
                            'email_password','sw_directory']
        optional_options = ['env_file']
        missing_options = []
        for option in required_options:            
            if not config_parser.has_option('Main',option):
                missing_options.append(option)
        if len(missing_options)!=0:
            error = 'config parser missing options %s'%(missing_options)
            raise Exception,error
        self.db_server = config_parser.get('Main','db_server')
        self.db_name = config_parser.get('Main','db_name')
        self.db_user = config_parser.get('Main','db_user')
        self.db_password = config_parser.get('Main','db_password')
        self.email_address = config_parser.get('Main','email_address')
        self.email_password = config_parser.get('Main','email_password')
        self.sw_directory = config_parser.get('Main','sw_directory')
        #optional arguments
        for option in optional_options:
            if option in config_parser.items('Main'):
                setattr(self,option,config_parser.get('Main',option))
    def parse_options(self,options):
        #should fail if any option (except passwords) are not provided
        self.db_server = options.db_server
        self.db_name = options.db_name
        self.db_user = options.db_user
        self.db_password = options.db_password
        self.email_address = options.email_address
        self.email_password = options.email_password
        self.sw_directory = options.sw_directory
        self.env_file = options.env_file
        
