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
                      help="Define root diretory")
    args.add_argument("movie", metavar="movie", type=str,
                      help="movie file")
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

def find_movie(movie, actors="N"):
    """
        Values:
            "movie": search movie
            "actors": extract actors (N = none; S = simple; F = full: default N)
    """
    url = "www.myapifilms.com"

    params = urllib.urlencode({"title": query, "format": "JSON", "actors": actors})
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
    query = raw_input("Movie to search: ")

    print find_movie(query)