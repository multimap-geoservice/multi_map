# -*- coding: utf-8 -*-
# encoding: utf-8

import json
import requests

def json_format(cont):
    print json.dumps(
        cont,
        sort_keys=True,
        indent=4,
        separators=(',', ': '), 
        ensure_ascii=False, 
    )


def get_response(request_):
    if isinstance(request_, dict):
        request_ = json.dumps(
            request_, 
            ensure_ascii=False
        )
    json_format(
        requests.get(
            #u"http://localhost:3007/geocoder/ОСМ_RU-SPE?{}".format(
            #u"http://localhost:3007/geocoder/OSM_RU?{}".format(
            u"http://localhost:3007/geocoder/central_russia_sxf?{}".format(
                request_.decode('utf-8')
            )
        ).json()
    )
    

if __name__ == "__main__":
    request_ = {
        "epsg_code": 900913,
        #"max_features": 10,
        "layer_property": [
            "type", 
            "name",
            "id", 
            #"msGeometry", 
        ],
        #"layers": {
            #"buildings": None,
            #"landuse": {
                #"filter": {
                    #"type": {
                        #"=": "military",
                    #},
                #},
                #"layer_property": [
                    #"type", 
                    #"name",
                    #"id", 
                    #"msGeometry", 
                #],
            #},
        #},
        "filter": {
            "or": [
                {
                    #"and": {
                        "name": {
                            "like": "*пет*",
                        },
                        #"type": {
                            #"=": "hotel",
                        #},
                    #},
                }, 
                {
                    #"and": {
                        "name": {
                            "like": "*бал*",
                        },
                        #"type": {
                            #"=": "hotel",
                        #},
                    #},
                }, 
            ],
        }
    }
    
    print "*" * 30
    print "Metadata"
    print "*" * 30
    get_response(request_)

    
    request_ = {
        "epsg_code": 900913,
        #"epsg_code": 3857,
        #"max_features": 1,
        "layer_property": [
            "type", 
            "name",
            "id", 
            #"msGeometry", 
        ],
        #"layers": {
            #"buildings": None,
            #"landuse": None, 
        #}, 
        "filter": {
            "name": {
                "null": None,
                "bbox": {
                    "coord": [
                        59.97111801186481728,
                        30.21720754623224181,
                        59.97569926211409097,
                        30.22404557000332304, 
                    ],
                    "epsg_code": 4326,
                    #"coord": [
                        #3364107.934602736961,
                        #8393636.548086917028,
                        #3364263.219452924561,
                        #8393740.583811631426
                    #],
                    #"epsg_code": 3857,
                },
            },
        }, 
    }
        
    #print "*" * 30
    #print "Bbox"
    #print "*" * 30
    #get_response(request_)

    request_ = {
        "epsg_code": 900913,
        "layer_property": [
            "name",
            "msGeometry"
        ],
        "max_features": 10,
        "layer_property": [
            "type", 
            "name",
            "id", 
            #"msGeometry", 
        ],
        #"layers": {
            #"buildings": None,
            #},
        "filter": {
            "coord1": {
                "buffer": {
                    #"coord": [
                        #59.93903,
                        #30.31589,
                    #],
                    "coord": [
                        8386175.766,
                        3374749.506,
                    ],
                    "radius": 105,
                    #"epsg_code": 4326, 
                    #"epsg_code_measure": 900913, 
                    #"epsg_code_measure": 4326, 
                    "epsg_code": 3857, 
                },
            }, 
        }, 
    }
    #print "*" * 30
    #print "Buffer"
    #print "*" * 30
    #get_response(request_)
    
    request_ = {
        "max_features": 1,
        "layer_property": [
            "type", 
            "name",
            "id", 
            "msGeometry", 
        ],
        "filter": {
            "geom": {
                "bbox": {
                    #"coord": [
                        #59.97111801186481728,
                        #30.21720754623224181,
                        #59.97569926211409097,
                        #30.22404557000332304, 
                    #],
                    #"epsg_code": 4326,
                    "coord": [
                        -20037508.34,
                        4507843.48159565,
                        20037508.34,
                        19593253.9008964, 
                    ],
                    "epsg_code": 3857,
                },
            }
        },
    }    

    #print "*" * 30
    #print "monotest"
    #print "*" * 30
    #get_response(request_)
    
    #print "*" * 30
    #print "GetCapabilites"
    #print "*" * 30
    #get_response("GetCapabilites")

    #print "*" * 30
    #print "GetInfo"
    #print "*" * 30
    #get_response("GetInfo")

    #print "*" * 30
    #print "GetHelp"
    #print "*" * 30
    #get_response("GetHelp")
    
    #print "*" * 30
    #print "GetPropperties"
    #print "*" * 30
    #get_response("GetPropperties")
