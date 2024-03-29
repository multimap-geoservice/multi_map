# -*- coding: utf-8 -*-
# encoding: utf-8

import os, sys
from map_pub import BuildMapRes


def init_map(template, fontset, map_, map_type, **kwargs):
    print ("BUILD: {}".format(map_))
    
    # init builder
    builder = BuildMapRes()
    builder.create_res = True
    builder.load4file(template)
    
    # osm
    if builder.mapjson["VARS"].has_key('db_connection'):
        db_connection = "host={0} dbname={1} user={2} password={3} port=5432".format(
            kwargs["host"], 
            map_, 
            kwargs["user"], 
            kwargs["password"], 
        )
        builder.mapjson["VARS"]["db_connection"] = db_connection 
        builder.mapjson["VARS"]["name"] = "osm_{}".format(map_) 
        builder.mapjson["VARS"]["title"] = "Open Street Map {}".format(map_) 
        builder.mapjson["VARS"]["fontset"] = fontset 
    
    if map_type == "maps_path":
        map_full_path = "{0}/{1}.json".format(kwargs['maps_path'], map_)
    elif map_type == "maps_path_db":
        map_full_path = "{0}/{1}.json".format(kwargs['maps_path_db'], map_)
    
    if map_type == "maps_db" or map_type == "maps_path_db":
        db_connect = {
            "host": kwargs['host'], 
            "dbname": kwargs['dbname'],
            "user": kwargs['user'],
            "password": kwargs['password'],
        }
        if map_type == 'maps_path_db':
            db_connect['path'] = map_full_path

    # build map
    if map_type == "maps_path":
        builder.save2file(
            path=map_full_path
        )
    elif map_type == "maps_db" or map_type == "maps_path_db":
        builder.save2pgsql(
            table=kwargs['maps_table'], 
            name=map_, 
            col_name=kwargs['maps_col_name'], 
            col_cont=kwargs['maps_col_cont'],
            columns=kwargs['columns'], 
            **db_connect
        )


if __name__ == "__main__":
    db = {
        "host": sys.argv[1], 
        "dbname": "maps",
        "user": "gis",
        "password": "gis",
        "maps_table": "maps",
        "maps_col_name": "name",
        "maps_col_cont": "cont",
        "maps_path": "{}/GIS/mapserver/debug/all_maps/fs".format(os.environ["HOME"]), 
        "maps_path_db": "{}/GIS/mapserver/debug/all_maps/db".format(os.environ["HOME"]), 
        "columns": {
            "int_data": 1,
            "float_data": 0.5,
            "text_data": "text",
            "timestamp": "now::timestamp",
            }
    }
    template = "{}/GIS/mapserver/debug/maps/osm.json".format(os.environ["HOME"])
    fontset = "{}/GIS/mapserver/debug/maps/fonts/fonts.lst".format(os.environ["HOME"])
    maps = {
        "maps_path": [
            "RU-SPE", 
        ], 
        "maps_path_db": [
            "RU-KR", 
        ], 
        "maps_db": [
            "RU-LEN", 
        ], 
    }
    for map_type in maps:
        for map_ in maps[map_type]: 
            init_map(template, fontset, map_, map_type, **db)
