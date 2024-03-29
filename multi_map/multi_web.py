# -*- coding: utf-8 -*-
# encoding: utf-8

import os
import imp
import time
import copy
import json
import codecs
import importlib
from multiprocessing import Process, Queue
from wsgiref.simple_server import make_server, WSGIServer
from SocketServer import ThreadingMixIn

from interface import pgsqldb


########################################################################
class ThreadingWSGIServer(ThreadingMixIn, WSGIServer): 
    daemon_threads = True


########################################################################
class MultiWEB(object):
    """
    Class for serialization & render more maps
    """
    # full serialization sources
    fullserial = False
    # multiprocessing
    multi = False
    # debug -1-response only, 0-error, 1-warning, 2-full
    debug = 0
    # log - False or path
    log = False
    # Enviroments for request
    RESP_STATUS = {
        200: '200 OK',
        400: '400 BAD REQUEST',
        404: '404 NOT FOUND',
        500: '500 SERVER ERROR',
    }
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
        'MS_DEBUGLEVEL',
        'MS_ENCRYPTION_KEY',
        'MS_ERRORFILE',
        'MS_MAPFILE',
        'MS_MAPFILE_PATTERN',
        'MS_MAP_NO_PATH',
        'MS_MAP_PATTERN',
        'MS_MODE',
        'MS_OPENLAYERS_JS_URL',
        'MS_TEMPPATH',
        'MS_XMLMAPFILE_XSLT',
        'PATH_INFO',
        'PROJ_LIB',
        'QUERY_STRING',
        'REMOTE_ADDR',
        'REQUEST_METHOD',
        'SCRIPT_NAME',
        'SERVER_NAME',
        'SERVER_PORT'
    ]
    # invariable map name list
    invariable_name = []
    # default map requests list
    map_requests = [
        'multi_map.map_requests.request_mapscript', 
        'multi_map.map_requests.request_mapnik', 
    ]
    # config files for map requests
    req_configs = {}
    
    #----------------------------------------------------------------------
    def __init__(self, port=3007, host='0.0.0.0', base_url="http://localhost", srcs = []):
        """
        serial_src - [] list sources for serialization
        """
        self.serial_src = srcs
        """
        serial_tps - {} dict of tipes serialization data
        ------------------------------
        source format:
        {
            "type": self.serial_type
        }
        Next keys is optionls for type
        ------------------------------
        example file system:
        {
            "label": "label name" (optionaly for serialization)
            "type": "fs"
            "ext": [] json|xml|map|or any|or not
            "path": "/path/to/maps"
        }
        ------------------------------
        example database:
        {
            "label": "label name" (optionaly for serialization)
            "type": "pgsql"(while only)
            "connect": {
                "host": localhost,
                "port": 5432,
                "dbname": "name",
                "user": "user",
                "password": "pass",
            }
            "query": "select name as map_name, content as map_cont from table"
        }
        "query": select two column as: map_name, map_cont
        ----------------------------
        For maptemp_(fs|pgsql) add key: 
            'template' (mapscrip_publisher only) -
                str, unicode - path to mapscript_publisher template of mapscript
                dict - this mapscript_publisher template of mapscript
            'ext' - file extension for 'fs' source geospatial file (gif, shp, and every)
            'map_cont' - bool file content for 'fs' -
                false(default) - file path to template['VARS']['data']
                true - file content to template['VARS']['data']
            
        This mapscript_publisher template only for one file - specify in VARS[data]
        """
        self.serial_tps = {
            "fs": {
                "preserial": self._preserial_fs,
                "subserial": self._subserial_fs,
                "path": (str, unicode),
                "enable": bool,
            }, 
            "maptemp_fs": {
                "preserial": self._preserial_fs,
                "subserial": self._subserial_maptemp_fs,
                "path": (str, unicode),
                "ext": (list, str, unicode),
                "template": (dict, str, unicode),
                "enable": bool,
            }, 
            "pgsql": {
                "preserial": self._preserial_pgsql,
                "subserial": self._subserial_pgsql,
                "connect": dict,
                "query": (list, str, unicode),
                "enable": bool,
            }, 
            "maptemp_pgsql": {
                "preserial": self._preserial_pgsql,
                "subserial": self._subserial_maptemp_pgsql,
                "connect": dict,
                "query": (list, str, unicode),
                "template": (dict, str, unicode),
                "enable": bool,
            }
        }
       
        # default web params
        self.wsgi_host = host
        self.wsgi_port = port
        self.url = "{0}:{1}".format(base_url, port)
        self.maps = {}

        # add map requests 
        """
        Mpa Formats for serialization:
        key: name
        "test": test to find format
        "get": method for get map
        "request": method for request map
        "metadata": return matadata dict
        "enable": bool flag for use in serialize
        """
        self.serial_formats = {}
        self.map_requests_status = {my: False for my in self.map_requests}

            
    def logging(self, debug_layer, outdata):
        if isinstance(outdata, str):
            outdata = u'{}'.format(outdata.decode('utf-8'))
        if self.debug >= debug_layer:
            if self.log:
                with codecs.open(self.log, 'a', encoding='utf-8') as logfile:
                    logfile.write(u"{}\n".format(outdata))
            else:
                print(outdata)

    def init_map_requests(self, req_name=None):
        if req_name:
            map_requests = [req_name]
        else:
            map_requests = self.map_requests_status.keys()
        #self.serial_formats = {}
        result = {}
        for req_name in map_requests:
            try:
                if os.path.isfile(req_name):
                    map_req = imp.load_source(
                        os.path.basename(req_name), 
                        os.path.abspath(req_name)
                    )
                else:
                    map_req = importlib.import_module(req_name)
                config = self.req_configs.get(req_name, '')
                protcol = map_req.Protocol(
                    self.url, 
                    self.logging, 
                    config
                )
                proto_schema = protcol.proto_schema
                proto_maps =  protcol.proto_maps
            except Exception as err:
                self.map_requests_status[req_name] = False
                self.logging(
                    0,
                    u"ERROR: Request Module:'{0}' is not loaded\nsys err: {1}".format(
                        req_name, 
                        err
                    )
                )
                result[req_name] = False
            else:
                if proto_schema:
                    for map_name in self.maps.keys():
                        for map_format in proto_schema.keys():
                            if self.maps[map_name].get("format", False) == map_format:
                                del(self.maps[map_name])
                self.serial_formats.update(proto_schema)
                self.maps.update(proto_maps)
                self.invariable_name += protcol.proto_maps.keys()
                self.map_requests_status[req_name] = True
                self.logging(
                    3,
                    u"INFO: Request Module:'{}' is loaded".format(
                        req_name, 
                    )
                )
                result[req_name] = True
        return result
             
    def _detect_cont_format(self, cont):
        """
        Detect content format as self.serial_formats
        """
        for cont_format in self.serial_formats:
            if self.serial_formats[cont_format]["enable"]:
                if self.serial_formats[cont_format]["test"](cont):
                    return cont_format
                
    def _create_maptemp_content(self, mapsrc, maptemp):
        """
        Create maptemp from source file 
        Add mapsrc to VARS[data] maptemp
        """
        template = None
        if isinstance(mapsrc, str):
            mapsrc = u"{}".format(mapsrc.decode('utf-8'))
            
        if isinstance(maptemp, (str, unicode)):
            if os.path.isfile(maptemp):
                with open(maptemp) as file_:  
                    template = json.load(file_)
            else:
                template = json.loads(maptemp)
        elif isinstance(maptemp, dict):
            template = copy.deepcopy(maptemp)
            
        if template:
            template["VARS"]["data"] = mapsrc
            return template
        
    def _preserial_fs(self, **kwargs):
        """
        Find names for serialization all fs sources
        """
        dir_ = kwargs['path']
        if kwargs.has_key('ext'):
            if isinstance(kwargs['ext'], (list, tuple)):
                exts = kwargs['ext']
            else:
                exts = [kwargs['ext']]
        else:
            exts = self.serial_formats
        names = []
        for file_ in os.listdir(dir_):
            file_name = file_.split('.')[0]
            file_ext = file_.split('.')[-1]
            if file_ext in exts:
                self.logging(
                    2,
                    u"INFO: In Dir:{0}, add Map name {1}".format(dir_, file_name)
                )
                names.append(file_name)
        return names

    def _subserial_fs(self, map_name, **kwargs):
        """
        subserializator for fs
        """
        if isinstance(map_name, str):
            map_name = u'{}'.format(map_name.decode('utf-8'))
        dir_ = kwargs['path']
        if kwargs.has_key('ext'):
            if isinstance(kwargs['ext'], (list, tuple)):
                exts = kwargs['ext']
            else:
                exts = [kwargs['ext']]
        else:
            exts = self.serial_formats
        for file_ in os.listdir(dir_):
            for ext in exts:
                if file_ == u"{0}.{1}".format(map_name, ext):
                    content = u"{0}/{1}".format(dir_, file_)
                    cont_format = self._detect_cont_format(content)
                    if cont_format is not None:
                        self.logging(
                            2,
                            u"INFO: In Dir:{0}, load Map File {1}".format(dir_, file_)
                        )
                        return cont_format, content
                
    def _subserial_maptemp_fs(self, map_name, **kwargs):
        """
        subserializator maptemp for fs source list
        """
        if isinstance(map_name, str):
            map_name = u'{}'.format(map_name.decode('utf-8'))

        cont_format = "maptemp"
        if not self.serial_formats.has_key(cont_format):
            return
        elif not self.serial_formats[cont_format]["enable"]:
            return
        maptemp = kwargs['template']
        
        if self.serial_formats[cont_format]['test'](maptemp):
            dir_ = kwargs['path']
            if isinstance(kwargs['ext'], (list, tuple)):
                exts = kwargs['ext']
            else:
                exts = [kwargs['ext']]
            for file_ in os.listdir(dir_):
                for ext in exts:
                    test_ = u"{0}.{1}".format(map_name, ext)
                    if file_ == test_:
                        mapsrc = u"{0}/{1}".format(dir_, file_)
                        if kwargs.get('map_cont', False):
                            mapsrc_filename = mapsrc
                            with open(mapsrc_filename, 'r') as f_:
                                mapsrc = f_.read()
                        content = self._create_maptemp_content(mapsrc, maptemp)
                        if content:
                            self.logging(
                                2,
                                u"INFO: In Dir:{0}, load Map Source {1}".format(
                                    dir_, 
                                    file_
                                )
                            )
                            return cont_format, content

    def _preserial_pgsql(self, **kwargs):
        """
        Find names for serialization all pgsql sources
        """
        if isinstance(kwargs['query'], list):
            query = '\n'.join(kwargs['query'])
        else:
            query = kwargs['query']
        SQL = """
        select query.map_name
        from (
        {}
        ) as query
        """.format(query)
        
        psql = pgsqldb(**kwargs['connect'])
        psql.sql(SQL)
        names = psql.fetchall()
        psql.close()
        if names is not None:
            names = [my[0] for my in names]
            self.logging(
                2,
                "INFO: In Database:{0}, add Map name(s) {1}".format(
                    kwargs['connect']['dbname'],
                    names
                )
            )
            return names
  
    def _subserial_pgsql(self, map_name, **kwargs):
        """
        subserializator for pgsql
        """
        if isinstance(kwargs['query'], list):
            query = '\n'.join(kwargs['query'])
        else:
            query = kwargs['query']
        SQL = u"""
        select query.map_cont
        from (
        {0}
        ) as query
        where query.map_name = '{1}'
        limit 1
        """.format(query, map_name)
        
        psql = pgsqldb(**kwargs['connect'])
        psql.sql(SQL)
        content = psql.fetchone()
        psql.close()
        if content is not None:
            content = content[0]
            cont_format = self._detect_cont_format(content)
            if cont_format is not None:
                self.logging(
                    2,
                    "INFO: From Database:{0}, load Map {1}".format(
                        kwargs['connect']['dbname'],
                        map_name
                    )
                )
                return cont_format, content
    
    def _subserial_maptemp_pgsql(self, map_name, **kwargs):
        """
        subserializator maptemp for pgsql source list
        """

        cont_format = "maptemp"
        if not self.serial_formats.has_key(cont_format):
            return
        elif not self.serial_formats[cont_format]["enable"]:
            return
        maptemp = kwargs['template']
        
        if self.serial_formats[cont_format]['test'](maptemp):
            if isinstance(kwargs['query'], list):
                query = '\n'.join(kwargs['query'])
            else:
                query = kwargs['query']
            SQL = u"""
            select query.map_cont
            from (
            {0}
            ) as query
            where query.map_name = '{1}'
            limit 1
            """.format(query, map_name)
            
            psql = pgsqldb(**kwargs['connect'])
            psql.sql(SQL)
            mapsrc = psql.fetchone()
            psql.close()
            if mapsrc is not None:
                mapsrc = mapsrc[0]
                content = self._create_maptemp_content(mapsrc, maptemp)
                if content:
                    self.logging(
                        2,
                        u"INFO: From Database:{0}, load Map Source {1}".format(
                            kwargs['connect']['dbname'],
                            map_name
                        )
                    )
                    return cont_format, content

    def full_serializer(self, replace=True, map_reload=False, source=None):
        """
        Full serialization all sources map
        kwargs:
        -------
        replase - replace maps if the names match
        map_reload - reload maps
        source - serialize source by index (int) or by label (str,unicode)
        """
        if source is not None:
            srcs = []
            if isinstance(source, int):
                if source + 1 <= len(self.serial_src):
                    srcs = [self.serial_src[source]]
            elif isinstance(source, (str, unicode)):
                labels = [my.get("label", None) for my in self.serial_src]
                if source in labels:
                    index = labels.index(source)
                    srcs = [self.serial_src[index]]
        else:
            srcs = self.serial_src
            
        all_map_names = []
        for src in srcs:
            src_type = src['type']
            valid = [
                isinstance(src[key], self.serial_tps[src_type][key]) 
                for key 
                in self.serial_tps[src_type] 
                if key not in ('subserial', 'preserial')
            ]
            valid.append(src['enable'])
            if False not in valid:
                preserial = self.serial_tps[src_type]['preserial']
                all_map_names += preserial(**src)
                
        # find dublicates + replaces
        nam_count = {my: all_map_names.count(my) for my in all_map_names}
        nam_uniq = [my for my in nam_count if nam_count[my] == 1]
        nam_dubl = [my for my in nam_count if nam_count[my] > 1]
        if len(nam_dubl) > 0: 
            self.logging(
                1,
                u"WARINIG: Found dublicate Map Names:{}".format(nam_dubl)
            )
        if replace:
            all_map_names = nam_uniq + nam_dubl
        else:
            all_map_names = nam_uniq
        # load all names
        for map_name in all_map_names:
            if not self.maps.has_key(map_name) or map_reload:
                map_ = self.serializer(map_name)
                if map_ and map_name not in self.invariable_name:
                    self.maps[map_name] = map_

    def serializer(self, map_name, timestamp=True):
        """
        serialization map from name of self.serial_src
        """
        for src in self.serial_src:
            src_type = src['type']
            valid = [
                isinstance(src[key], self.serial_tps[src_type][key]) 
                for key 
                in self.serial_tps[src_type] 
                if key not in ('subserial', 'preserial')
            ]
            valid.append(src['enable'])
            if False not in valid:
                subserial = self.serial_tps[src_type]['subserial']
                out_subserial = subserial(map_name, **src)
                if out_subserial is not None:
                    cont_format, content = out_subserial
                    content = self.serial_formats[cont_format]['get'](map_name, content)
                    if content is not None:
                        if timestamp:
                            timestamp = int(time.time())
                        else:
                            timestamp = 0
                        return {
                            "format": cont_format,
                            "request": self.serial_formats[cont_format]['request'],
                            "content": content,
                            "timestamp": timestamp,
                            "multi": True,
                        }

    def application(self, env, start_response):
        
        # find map name
        map_name = "/".join(env['PATH_INFO'].split('/')[1:])
        map_name = u"{}".format(map_name.decode('utf-8'))
        
        # text debug
        if self.debug >= 1:
            self.logging(1, "-" * 30)
            for key in self.MAPSERV_ENV:
                if key in env:
                    os.environ[key] = env[key]
                    self.logging(
                        1, 
                        "{0}='{1}'".format(key, env[key])
                    )
                else:
                    os.unsetenv(key)
            if self.debug >= 2:
                self.logging(2, "QUERY_STRING=(")
                for q_str in env['QUERY_STRING'].split('&'):
                    self.logging(2, "    {},".format(q_str))
                self.logging(2, ")")
            self.logging(1, "-" * 30)
        
        # serialization & response  
        while True:
            if not self.maps.has_key(map_name):
                # serialization
                map_ = self.serializer(map_name)
                if map_ and map_name not in self.invariable_name:
                    self.maps[map_name] = map_
                else:
                    self.logging(
                        0,
                        u"ERROR: Map:'{}' is not serialized".format(map_name)
                    )
                    resp_status = self.RESP_STATUS[404]
                    resp_type = [('Content-type', 'text/plain')]
                    start_response(resp_status, resp_type)
                    return [b'MAP:\'{}\' not found'.format(map_name.encode('utf-8'))]
            else:
                # response (mono or multi)
                if self.multi and self.maps[map_name]['multi']:
                    que = Queue()
                    proc = Process(
                        target=self.maps[map_name]['request'],
                        name='response',
                        args=(
                            env,
                            self.maps[map_name]['content'],
                            que
                        )
                    )
                    proc.start()
                    response = que.get()
                    proc.join()
                else:
                    response = self.maps[map_name]['request'](
                        env,
                        self.maps[map_name]['content']
                    )
                # fin response
                if response:
                    if self.maps.has_key(map_name):
                        if self.maps[map_name].get('timestamp', False):
                            self.maps[map_name]['timestamp'] = int(time.time())
                    resp_status = str(response[0])
                    resp_type = [('Content-type', str(response[1]))]
                    start_response(
                        self.RESP_STATUS.get(
                            int(resp_status), 
                            self.RESP_STATUS[200]
                        ), 
                        resp_type
                    )
                    return [response[-1]]
                else:
                    self.logging(
                        0,
                        u"ERROR: Resource:{} error".format(map_name)
                    )
                    resp_status = self.RESP_STATUS[500]
                    resp_type = [('Content-type', 'text/plain')]
                    start_response(resp_status, resp_type)
                    return [b'Resource:{} error'.format(map_name)]

    def init_modules(self):
        self.init_map_requests() 

        if self.fullserial:
            self.full_serializer()

    def wsgi(self):
        """
        Start simple wsgi server
        """
        self.init_modules()
        httpd = make_server(
            self.wsgi_host,
            self.wsgi_port,
            self.application,
            ThreadingWSGIServer
        )
        self.logging(0, 'Serving on port %d...' % self.wsgi_port)
        httpd.serve_forever()
    
    def __call__(self):
        self.wsgi()