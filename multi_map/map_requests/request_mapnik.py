# -*- coding: utf-8 -*-
# encoding: utf-8

import os
import importlib
from xml.etree import ElementTree
from pkg_resources import resource_filename

try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs

from ogcserver.common import Version
from ogcserver.WMS import BaseWMSFactory
from ogcserver.configparser import SafeConfigParser
from ogcserver.wms111 import ExceptionHandler as ExceptionHandler111
from ogcserver.wms130 import ExceptionHandler as ExceptionHandler130
from ogcserver.exceptions import OGCException


########################################################################
class Protocol(object):
    """
    Class for serialization & render maps:
    mapnik as OGCServer
    """

    #----------------------------------------------------------------------
    def __init__(self, url, logging, config=''):
       
        # default protocol variables
        self.url = url 
        self.home_html = None
        self.logging = logging
        self.proto_schema = {
            "xml": {
                "test": self.is_xml,
                "get": self.get_mapnik,
                "request": self.request_mapnik,
                "metadata": self.get_metadata,
                "enable": True,
                },
        }
        self.proto_maps = {}
        # Load OGCServver config
        self.ogcserver = importlib.import_module('ogcserver')
        if os.path.isfile(config):
            self.ogc_configfile = config
        else:
            self.ogc_configfile = resource_filename(
                self.ogcserver.__name__, 'default.conf'
            )
        ogcconf = SafeConfigParser()
        ogcconf.readfp(open(self.ogc_configfile))
        self.ogcconf = ogcconf
        if ogcconf.has_option('server', 'debug'):
            self.debug = int(ogcconf.get('server', 'debug'))
        else:
            self.debug = 0
            
    def is_xml(self, test_cont):
        try:
            if os.path.isfile(test_cont):
                _ = ElementTree.parse(test_cont)
            else:
                _ = ElementTree.fromstring(test_cont)
        except:
            return False
        else:
            return True
    
    def ogcserver_constructor(self, content):
        try:
            wms_factory = BaseWMSFactory(self.ogc_configfile)
            if os.path.isfile(content):
                if isinstance(content, unicode):
                    mapnik_file = content.encode("utf-8")
                else:
                    mapnik_file = content
                wms_factory.loadXML(xmlfile=mapnik_file)
            else:
                wms_factory.loadXML(xmlstring=content)  #for testing
            wms_factory.finalize()
        except Exception as err:
            self.logging(
                0, 
                u"ERROR: Content {0} not init as Mapnik FILE\n{1}".format(
                    content, 
                    err.__str__().decode("utf-8")
                )
            )
        else:
            return wms_factory
        
    def get_mapnik(self, map_name, content):
        """
        get map on mapnik xml
        """
        # serialize string
        return content  
    
    def request_mapnik(self, env, mapdata, que=None):
        """
        render on mapnik request
        """
        map_obj = self.ogcserver_constructor(mapdata)
        reqparams = {}
        base = True
        for key, value in parse_qs(env['QUERY_STRING'], True).items():
            reqparams[key.lower()] = value[0]
            base = False

        if self.ogcconf.has_option_with_value('service', 'baseurl'):
            onlineresource = '%s' % self.ogcconf.get('service', 'baseurl')
        else:
            onlineresource = u'http://%s%s%s?' % (
                env['HTTP_HOST'].decode('utf-8'), 
                env['SCRIPT_NAME'].decode('utf-8'), 
                env['PATH_INFO'].decode('utf-8')
            )

        try:
            if not reqparams.has_key('request'):
                raise OGCException('Missing request parameter.')
            request = reqparams['request']
            del reqparams['request']
            if request == 'GetCapabilities' and not reqparams.has_key('service'):
                raise OGCException('Missing service parameter.')
            if request in ['GetMap', 'GetFeatureInfo']:
                service = 'WMS'
            else:
                try:
                    service = reqparams['service']
                except:
                    service = 'WMS'
                    request = 'GetCapabilities'
            if reqparams.has_key('service'):
                del reqparams['service']
            ServiceHandlerFactory = getattr(self.ogcserver, service).ServiceHandlerFactory
            servicehandler = ServiceHandlerFactory(
                self.ogcconf, 
                map_obj, 
                onlineresource, 
                reqparams.get('version', None)
            )
            if reqparams.has_key('version'):
                del reqparams['version']
            if request not in servicehandler.SERVICE_PARAMS.keys():
                raise OGCException(
                    'Operation "%s" not supported.' % request, 
                    'OperationNotSupported'
                )
            ogcparams = servicehandler.processParameters(request, reqparams)
            try:
                requesthandler = getattr(servicehandler, request)
            except:
                raise OGCException(
                    'Operation "%s" not supported.' % request, 
                    'OperationNotSupported'
                )

            ogcparams['HTTP_USER_AGENT'] = env.get('HTTP_USER_AGENT', '')

            response = requesthandler(ogcparams)
        except:
            version = reqparams.get('version', None)
            if not version:
                version = Version()
            else:
                version = Version(version)
            if version >= '1.3.0':
                eh = ExceptionHandler130(self.debug,base,self.home_html)
            else:
                eh = ExceptionHandler111(self.debug,base,self.home_html)
            response = eh.getresponse(reqparams)
            
        out_response = (
            int(response.status_code), 
            response.content_type, 
            response.content
        )
        if que is None:
            return out_response
        else:
            que.put(out_response)

    def get_metadata(self, map_cont):
        map_obj = self.ogcserver_constructor(map_cont)
        return {
            "layers": [my for my in map_obj.layers], 
            "aggregatestyles": map_obj.aggregatestyles, 
            "map_attributes": {
                my: str(map_obj.map_attributes[my]) 
                for my 
                in map_obj.map_attributes
            }, 
        }
