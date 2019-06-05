#!/usr/bin/python2

import os
import sys
import json
import signal
import psutil
import argparse

from multi_map import LightAPI


########################################################################
class Server(object):
    """
    Utilite interface
    
    Exit code:
    0 - OK
    1 - Config file not found
    2 - Source key in Config file not found
    3 - Port allredy use
    4 - Server allredy started on PID
    """
    item_opt_args = ["host", "port", "base_url"]
    item_opt_vars = ["multi", "debug"]
    item_opt_util = ["timeout"]

    #----------------------------------------------------------------------
    def __init__(self):
        """Return comstring arguments"""
        
        parser = argparse.ArgumentParser(description='Runs the multi_map server')
        parser.add_argument('-c', '--config', dest='config_file', type=str, help='''
        Path to the config file.
        ''')
        parser.add_argument('-H', '--host', dest='host', type=str, help='''
        Bind host (optionaly config).
        ''')
        parser.add_argument('-P', '--port', dest='port', type=int, help='''
        Bind port (optionaly config).
        ''')
        parser.add_argument('-U', '--url', dest='base_url', type=str, help='''
        Base URL (optionaly config).
        ''')
        parser.add_argument('-M', '--multi', dest='multi', type=bool, help='''
        Multi Process mode (optionaly config).
        ''')
        parser.add_argument('-D', '--debug', dest='debug', type=int, help='''
        Debug mode 0,1,2,3 (optionaly config).
        ''')
        parser.add_argument('-T', '--timeout', dest='timeout', type=int, help='''
        Timeout to clean serialized maps (optionaly config).
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
        
        # stop
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGQUIT, self.signal_handler)
        # reload
        signal.signal(signal.SIGHUP, self.signal_handler)

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
                else:
                    # Add optionaly config commstrings
                    for key in self.item_opt_args + self.item_opt_vars + self.item_opt_util:
                        if self.args.__dict__[key]:
                            self.config[key] = self.args.__dict__[key]
                    
                    self.item_args = {}
                    # Add sources
                    if self.config.has_key("sources"):
                        self.item_args["srcs"]=self.config["sources"]
                    else:
                        print "ERROR: Sources Key not found in config file"
                        sys.exit(2)
                        
                    # Update item optionaly args 
                    for key in self.item_opt_args:
                        if self.config.has_key(key):
                            self.item_args[key] = self.config[key]
                    
    def set_pid(self):
        id_proc = os.getpid()
        self.pid = False
        if self.args.pid_file:
            if os.path.isdir(os.path.dirname(os.path.abspath(self.args.pid_file))):
                if os.path.isfile(self.args.pid_file):
                    with open(self.args.pid_file) as file_:  
                        old_pid = int(file_.read())
                    pid_name = {
                        int(my['pid']): my['name'] 
                        for my 
                        in [
                            my.as_dict(attrs=['pid','name']) 
                            for my 
                            in psutil.process_iter()
                        ]
                    }
                    if pid_name.has_key(old_pid):
                        old_name = pid_name[old_pid]
                        new_name = pid_name[id_proc]
                        if old_name == new_name:
                            print "ERROR: Server allredy started on PID:{}".format(
                                old_pid
                            )
                            sys.exit(4)
                try:
                    with open(self.args.pid_file, "w") as file_:  
                        file_.write(str(id_proc))
                except Exception as err:
                    print "ERROR: Pid file '{0}' is not create\nsys error:{1}".format(
                        self.args.pid_file, 
                        err
                    )
                else:
                    self.pid = os.path.abspath(self.args.pid_file)

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
   
    def signal_text(self, text):
        if self.log:
            with open(self.log, "a") as file_:  
                file_.write(text)
        else:
            print (text)
    
    def signal_handler(self, signum, frame):
        # stop
        if signum in (2, 3, 15):
            if self.pid:
                os.remove(self.pid)
            self.signal_text("Stop service - PID:{}".format(os.getpid()))
            sys.exit(0)
        # reload
        if signum == 1:
            self.signal_text("Reload service - PID:{}".format(os.getpid()))
            # to do
            #self.web.serial_src = self.config["sources"]
    
    def start(self):
        # Test use port
        if self.item_args.has_key("port"):
            port = self.item_args["port"]
        else:
            port = 3007
        net_procs = {
            my.laddr[1]: my.pid
            for my 
            in psutil.net_connections() 
            if my.pid is not None
        }
        if net_procs.has_key(port):
            print "ERROR: Port: {0} allredy use from Process: {1}".format(
                port, 
                net_procs[port]
            )
            sys.exit(3)
        
        # Add requests 
        self.lapi = LightAPI
        if self.config.has_key("requests"):
            self.lapi.map_requests = self.config["requests"]
       
        self.web = self.lapi(**self.item_args)
                
        # Update item optionaly vars 
        for key in self.item_opt_vars:
            if self.config.has_key(key):
                self.web.__dict__[key] = self.config[key]

        # Logging
        if self.log:
            self.web.log = self.log
        
        # Start
        self.web()
        
    def __call__(self):
        self.start()
        

if __name__ == "__main__":
    server = Server()
    server()
