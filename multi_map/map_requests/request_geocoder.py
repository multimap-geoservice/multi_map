# -*- coding: utf-8 -*-
# encoding: utf-8

import os
import json
import urllib
import requests

from wfs_geocoder import GeoCoder


########################################################################
class Protocol(object):
    """
    Tiny gcoder server
    """
    MAPSERV_ENV = [
        'CONTENT_LENGTH',
        'CONTENT_TYPE', 
        'CURL_CA_BUNDLE', 
        'HTTP_COOKIE',
        'HTTP_HOST', 
        'HTTPS', 
        'HTTP_X_FORWARDED_HOST', 
        'HTTP_X_FORWARDED_PORT',
        'HTTP_X_FORWARDED_PROTO', 
        'PROJ_LIB', 
        'QUERY_STRING', 
        'REMOTE_ADDR',
        'REQUEST_METHOD', 
        'SCRIPT_NAME', 
        'SERVER_NAME', 
        'SERVER_PORT'
    ]
    #----------------------------------------------------------------------
    def __init__(self, url, logging, config=''):
        """
        Config file for geocoder:
        {
            "debug": true|false,
            "out_geom": null|"gml"|"wkt"
            "map_formats":["map","json","maptemp"]
        }
        """
        # default protocol variables
        self.home_html = None
        self.logging = logging
        self.proto_schema = {
            "geocoder": {
                "test": lambda self, test_data: False,
                "get": False,
                "request": False,
                "metadata": False,
                "enable": False,
                },
        }
        self.proto_maps = {
            'geocoder': {
                "request": self.request_geocoder_service,
                "content": 'geocoder',
                "timestamp": 0,
                "multi": False
            }
        }
        # next
        self.wfs_maps = []
        self.url = url
        self.api_url = u"{}/api?".format(url)
        # geocoder map default comands    
        self.config = {
            "debug": False,
            "out_geom": None,
            "map_formats": [
                "map", 
                "json", 
                "maptemp", 
            ],
        }
        self.gc_map_com = {
            "GetCapabilites": "get_capabilities", 
            "GetInfo": "get_info", 
            "GetHelp": "get_help", 
            "GetPropperties": "get_properties",
        }
        self.geocoder_init(config)

    def geocoder_init(self, config=''):
        # load config file
        if os.path.isfile(config):
            try:
                with open(config) as file_:  
                    conf_dict = json.load(file_)
            except Exception as err:
                self.logging(
                    1, 
                    u"WARNING: Geocoder config '{0}' is not loaded\n{1}".format(
                        config, 
                        err
                    )
                )
            else:
                self.config.update(conf_dict)
        elif config:
            self.logging(
                1, 
                u"WARNING: Geocoder config '{}' not found in fs".format(config)
            )

        # test api
        valid_maps = []
        try:
            api_resp = requests.get(self.api_url)
        except Exception as err:
            raise Exception(
                u"ERROR: URL API not found!\n{}".format(err)
            )
        else:
            if api_resp.status_code != 200:
                raise Exception(
                    u"ERROR: API is not valid, status code:{}".format(
                        api_resp.status_code
                    )
                )
            else:  
                serialize = requests.get(
                    "{}serialize".format(self.api_url)
                )
                if serialize.status_code == 200:
                    all_maps = requests.get(
                        "{}maps".format(self.api_url)
                    )
                    if all_maps.status_code == 200:
                        out_maps = all_maps.json()
                        valid_maps = [
                            my
                            for my
                            in out_maps["maps"]
                            if out_maps["maps"][my]["format"] in self.config["map_formats"]
                        ]
        
        # load geocoser objs
        for test_map in valid_maps:
            try:
                geocoder = GeoCoder
                geocoder.out_geom = self.config["out_geom"]
                gc_obj = geocoder(
                    url=self.url, 
                    map_name=test_map, 
                    debug=self.config["debug"]
                )
            except:
                pass
            else:
                self.wfs_maps.append(test_map)
                gc_map_name = u"geocoder/{}".format(test_map)
                map_dict = {
                    gc_map_name: {
                    "format": "geocoder",
                    "request": self.request_geocoder_map,
                    "content": gc_obj,
                    "timestamp": 0,
                    "multi": True
                    }
                }
                self.proto_maps.update(map_dict)
                self.logging(
                    3, 
                    u"INFO: Map '{}' append to Geocoder".format(test_map)
                )
        
    def request_geocoder_service(self, env, mapdata, que=None):
        resp = json.dumps(
            self.wfs_maps,
            ensure_ascii=False
        )
        status = 200
        content = b'{}'.format(resp.encode('utf-8'))
        content_type = 'application/json'

        out_response = (
            status, 
            content_type, 
            content
        )
        if que is None:
            return out_response
        else:
            que.put(out_response)

    def request_geocoder_map(self, env, mapdata, que=None):
        status = 200
        if not env["QUERY_STRING"]:
            gk_comm_list = [my for my in self.gc_map_com]
            gk_comm_list.append({})
            resp = json.dumps(
                gk_comm_list,
                ensure_ascii=False
            )
        elif self.gc_map_com.has_key(env["QUERY_STRING"]):
            resp = json.dumps(
                mapdata.__class__.__dict__[
                    self.gc_map_com[env["QUERY_STRING"]]
                ](mapdata), 
                ensure_ascii=False
            )
        else:
            try:
                req = json.loads(urllib.unquote(env["QUERY_STRING"]))
                resp = json.dumps(
                    mapdata.get_response(req), 
                    ensure_ascii=False
                )
            except Exception as err:
                status = 500
                resp = json.dumps(
                    {
                        "ERROR": u"{}".format(err),
                    }, 
                    ensure_ascii=False
                )
                self.logging(
                    0, 
                    "ERROR: Geocoder failed:\n{}".format(err)
                )
    
        content = b'{}'.format(resp.encode('utf-8'))
        content_type = 'application/json'

        out_response = (
            status, 
            content_type, 
            content
        )
        if que is None:
            return out_response
        else:
            que.put(out_response)