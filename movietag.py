#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Copyright (C) 2014 Enrico Bianchi (enrico.bianchi@gmail.com)
Project       MovieTAG
Description   A movie tagging system
License       GPL version 2 (see GPL.txt for details)
"""

import argparse
import httplib
import json
import os
import sys
import urllib

def init_args():
    args = argparse.ArgumentParser(description="MovieTAG")
    args.add_argument("-r", "--root", metavar="<directory>",
                      help="Define root directory")
    args.add_argument("-q", "--query", metavar="<search>",
                      help="Movie to search")
    args.add_argument("movie", metavar="movie", type=str,
                      help="Movie file")
    return args

def check_structure(root):
    subdirs = [
        "By Actor",
        "By Director",
        "By Name",
        "By Genre",
        "By Year"
    ]

    for directory in subdirs:
        if not os.path.isdir(root + os.sep + directory):
            os.makedirs(root + os.sep + directory)

def find_movie(movie, actors="N", limit=1):
    """
        Values:
            "movie": search movie
            "actors": extract actors (N = none; S = simple; F = full: default N)
            "limit":  limit results (default 1)
    """
    url = "www.myapifilms.com"

    params = urllib.urlencode({"title": movie, "format": "JSON", "actors": actors, "limit": limit})
    connection = httplib.HTTPConnection(url)

    connection.request("GET", "/search?" + params)
    response = connection.getresponse()

    data = response.read()

    return json.loads(data)

if __name__ == "__main__":
    args = init_args().parse_args(sys.argv[1:])

    if not args.root:
        root = os.path.sep.join([os.path.expanduser('~'), "Videos"])
    else:
        root = args.root

    check_structure(root)

    if not args.query:
        query = raw_input("Movie to search: ")
    else:
        query = args.query

    print find_movie(query)
