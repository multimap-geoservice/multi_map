# -*- coding: utf-8 -*-
# encoding: utf-8

import os
import ast
import json

import mapscript

from map_pub import BuildMap, PubMap


########################################################################
class Protocol(object):
    """
    Class for serialization & render maps:
    mapscript as mapscript_publisher
    """
    
    #----------------------------------------------------------------------
    def __init__(self, url, logging, config=''):
       
        self.url = url 
        self.logging = logging
        self.proto_schema = {
            "json": {
                "test": self.is_json,
                "get": self.get_mapjson,
                "request": self.request_mapscript,
                "metadata": self.get_metadata,
                "enable": True,
                },
            "maptemp": {
                "test": self.is_maptemp,
                "get": self.get_maptemp,
                "request": self.request_mapscript,
                "metadata": self.get_metadata,
                "enable": True,
                },
            "map": {
                "test": self.is_map,
                "get": self.get_mapfile,
                "request": self.request_mapscript,
                "metadata": self.get_metadata,
                "enable": True,
                },
        }
        self.def_metadata_keys = [
            "wms_title", 
            "wfs_title", 
            "ows_title",
            "wms_abstract", 
            "wfs_abstract", 
            "ows_abstract", 
            "wms_enable_request", 
            "wfs_enable_request", 
            "ows_enable_request", 
            "wms_onlineresource", 
            "wfs_onlineresource", 
            "ows_onlineresource", 
        ]
        self.mapscript_ver = [int(my) for my in mapscript.MS_VERSION.split('.')]
    
    def ver_control(self, *args):
        control = True
        index = 0
        for num in args:
            if self.mapscript_ver[index] < num:
                control = False
            index += 1
        return control
            
    def is_json(self, test_cont):
        try:
            if os.path.isfile(test_cont):
                with open(test_cont) as file_:  
                    _ = json.load(file_)
            else:
                _ = json.loads(test_cont)
        except:
            return False
        else:
            return True    

    def is_maptemp(self, test_cont):
        out = False
        if isinstance(test_cont, (str, unicode)):
            try:
                if os.path.isfile(test_cont):
                    with open(test_cont) as file_:  
                        temp_ = json.load(file_)
                else:
                    temp_ = json.loads(test_cont)
            except:
                temp_ = {}
        elif isinstance(test_cont, dict):
            temp_ = test_cont
        else:
            temp_ = {}
        
        if temp_.has_key("VARS"):
            if temp_["VARS"].has_key("data"):
                out = True
        return out

    def is_map(self, test_cont):
        try:
            if os.path.isfile(test_cont):
                _ = mapscript.mapObj(test_cont)
            else:
                raise # map file content in DB: to do
        except:
            return False
        else:
            return True
        
    def get_mapfile(self, map_name, content):
        """
        get map on map file
        PubMap()
        """
        try:
            if os.path.isfile(content):
                mapfile = mapscript.mapObj(content)
            else:
                raise # map file content in DB: to do
        except:
            self.logging(
                0, 
                "ERROR: Content {} not init as Map FILE".format(content)
            )
        else:
            return self.add_onlineresource(map_name, mapfile)
    
    def get_mapjson(self, map_name, content):
        """
        get map on json template
        PubMap()
        """
        try:
            if os.path.isfile(content):
                pub_map = PubMap()
                pub_map.load_json(content)
            else:
                content = json.loads(
                        json.dumps(
                            ast.literal_eval(content), 
                            ensure_ascii=False
                    )
                )
                pub_map = PubMap(content)
        except:
            self.logging(
                0, 
                "ERROR: Content {} not init as Map JSON".format(content)
            )
        else:
            return self.add_onlineresource(map_name, pub_map())
     
    def get_maptemp(self, map_name, template):
        """
        build json template and get map for source file
        BuildMap() and PubMap()
        """
        builder = BuildMap()
        builder.mapjson = template
        content = builder()
        pub_map = PubMap(content)
        return self.add_onlineresource(map_name, pub_map())

    def add_onlineresource(self, map_name, content):
        """
        edit requests resources in mapscript object
        """
        if isinstance(content, mapscript.mapObj):
            if map_name != "":
                map_url = "{0}/{1}".format(self.url, map_name.encode('utf-8'))
                content.web.metadata.set("wms_onlineresource", map_url)
                content.web.metadata.set("wfs_onlineresource", map_url)
                return content
    
    def request_mapscript(self, env, mapdata, que=None):
        """
        render on mapserver mapscript request
        """
        request = mapscript.OWSRequest()
        mapscript.msIO_installStdoutToBuffer()
        request.loadParamsFromURL(env['QUERY_STRING'])
        rec_obj = mapdata.clone()
    
        try:
            status = rec_obj.OWSDispatch(request)
        except Exception as err:
            pass
    
        content_type = mapscript.msIO_stripStdoutBufferContentType()
        content = mapscript.msIO_getStdoutBufferBytes()
        out_response = (content_type, content)
        if que is None:
            return out_response
        else:
            que.put(out_response)
            
    def get_metadata(self, map_cont):
        matadata_keys = self.def_metadata_keys
        if self.ver_control(7, 2):
            matadata_keys = map_cont.web.metadata.keys() 
        return {
            my: map_cont.web.metadata.get(my) 
            for my 
            in matadata_keys
            if map_cont.web.metadata.get(my) 
        }
