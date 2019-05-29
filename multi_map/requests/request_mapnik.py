
import os
from xml.etree import ElementTree
from pkg_resources import resource_filename

try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs

#try:
    #import mapnik
#except ImportError:
    #import mapnik2 as mapnik

from ogcserver.common import Version
from ogcserver.WMS import BaseWMSFactory
from ogcserver.configparser import SafeConfigParser
from ogcserver.wms111 import ExceptionHandler as ExceptionHandler111
from ogcserver.wms130 import ExceptionHandler as ExceptionHandler130
from ogcserver.exceptions import OGCException


def do_import(module):
    """
    Makes setuptools namespaces work
    """
    moduleobj = None
    exec 'import %s' % module 
    exec 'moduleobj=%s' % module
    return moduleobj


########################################################################
class Protocol(object):
    """
    Class for serialization & render maps:
    mapnik as OGCServer
    """
    
    #----------------------------------------------------------------------
    def __init__(self, url, logging):
        
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
        # Load OGCServver config
        ogcserver = do_import('ogcserver')
        self.ogc_configfile = resource_filename(ogcserver.__name__, 'default.conf')
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
        
    def get_mapnik(self, map_name, content):
        """
        get map on mapnik xml
        mapnik.load_map_from_string()
        """
        try:
            if os.path.isfile(content):
                wms_factory = BaseWMSFactory(self.ogc_configfile)
                wms_factory.loadXML(content)
                wms_factory.finalize()
            else:
                raise # map file content in DB: to do
        except:
            self.logging(
                0, 
                "ERROR: Content {} not init as Mapnik FILE".format(content)
            )
        else:
            return wms_factory
    
    def request_mapnik(self, env, mapdata, que=None):
        """
        render on mapnik request
        """
        reqparams = {}
        base = True
        for key, value in parse_qs(env['QUERY_STRING'], True).items():
            reqparams[key.lower()] = value[0]
            base = False

        if self.ogcconf.has_option_with_value('service', 'baseurl'):
            onlineresource = '%s' % self.ogcconf.get('service', 'baseurl')
        else:
            onlineresource = 'http://%s%s%s?' % (
                env['HTTP_HOST'], 
                env['SCRIPT_NAME'], 
                env['PATH_INFO']
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
            try:
                ogcserver = do_import('ogcserver')
            except:
                raise OGCException('Unsupported service "%s".' % service)
            ServiceHandlerFactory = getattr(ogcserver, service).ServiceHandlerFactory
            servicehandler = ServiceHandlerFactory(
                self.ogcconf, 
                mapdata, 
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
            #kostyl!!!!
            response.content_type = "text/xml"
            
        out_response = (response.content_type, response.content)
        if que is None:
            return out_response
        else:
            que.put(out_response)

    def get_metadata(self, map_cont):
        return {}
