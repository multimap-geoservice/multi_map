#!/usr/bin/python2

import os
import sys
import json
import argparse

from multi_map import LightAPI

########################################################################
class Server(object):
    """
    Utilite interface 
    """
    item_opt_args = ["host", "port", "base_url"]
    item_opt_vars = ["multi", "debug"]

    #----------------------------------------------------------------------
    def __init__(self):
        """Return comstring arguments"""
        
        parser = argparse.ArgumentParser(description='Runs the multi_map server')
        parser.add_argument('-c', '--config', dest='config_file', type=str, help='''
        Path to the config file.
        ''')
        parser.add_argument('-p', '--pid', dest='pid_file', type=str, help='''
        Path to the pid file (optionaly).
        ''')
        parser.add_argument('-l', '--log', dest='log_file', type=str, help='''
        Path to the log file (optionaly).
        ''')
        self.args = parser.parse_args()
        
        self.set_config()
        if not self.config:
            print "ERROR: CONFIG_FILE not found"
            parser.print_help()
            sys.exit(1)
        
        self.set_pid()
        self.set_log()

    def set_config(self):
        self.config = False
        if self.args.config_file:
            if os.path.isfile(self.args.config_file):
                try:
                    with open(self.args.config_file) as file_:  
                        self.config = json.load(file_)
                except Exception as err:
                    print "ERROR: Config file '{0}' is not loaded\nsys error:{1}".format(
                        self.args.config_file, 
                        err
                    )
                    
    def set_pid(self):
        id_proc = os.getpid()
        self.pid = False
        if self.args.pid_file:
            if os.path.isdir(os.path.dirname(os.path.abspath(self.args.pid_file))):
                try:
                    with open(self.args.pid_file, "w") as file_:  
                        file_.write(str(id_proc))
                except Exception as err:
                    print "ERROR: Pid file '{0}' is not create\nsys error:{1}".format(
                        self.args.pid_file, 
                        err
                    )
                else:
                    self.pid = id_proc

    def set_log(self):
        self.log = False
        if self.args.log_file:
            if os.path.isdir(os.path.dirname(os.path.abspath(self.args.log_file))):
                try:
                    with open(self.args.log_file, "w") as file_:  
                        file_.write("Start in PID:{}\n".format(os.getpid()))
                except Exception as err:
                    print "ERROR: Log file '{0}' is not create\nsys error:{1}".format(
                        self.args.log_file, 
                        err
                    )
                else:
                    self.log = os.path.abspath(self.args.log_file)
    
    def start(self):
        # Add requests 
        self.lapi = LightAPI
        if self.config.has_key("requests"):
            self.lapi.map_requests = self.config["requests"]
       
        item_args = {}
        # Add sources
        if self.config.has_key("sources"):
            item_args["srcs"]=self.config["sources"]
        else:
            print "ERROR: Sources Key not found in config file"
            sys.exit(2)
            
        # Update item optionaly args 
        for key in self.item_opt_args:
            if self.config.has_key(key):
                item_args[key] = self.config[key]
        
        self.web = self.lapi(**item_args)
                
        # Update item optionaly vars 
        for key in self.item_opt_vars:
            if self.config.has_key(key):
                self.web.__dict__[key] = self.config[key]

        # Logging
        if self.log:
            self.web.log = self.log
        
        # Start
        self.web()
        

if __name__ == "__main__":
    server = Server()
    server.start()
