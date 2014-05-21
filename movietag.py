#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Copyright (C) 2014 Enrico Bianchi (enrico.bianchi@gmail.com)
Project       MovieTAG
Description   A movie tagging system
License       GPL version 2 (see GPL.txt for details)
"""

import argparse
import http.client
import json
import os
import sys
import urllib

from sqlite3 import dbapi2 as sqlite

class Database():
    _commit = None
    _conn = None
    _path = None

    def __init__(self, path, commit=True):
        self._path = path
        self._commit = commit

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self._conn:
                if self._commit:
                    self._conn.commit()
                else:
                    self._conn.rollback()
                self._conn.close()
        except:
            pass

    def _check_database(self, connection):
        cursor = connection.cursor()
        cursor.execute("select count(*) from sqlite_master")

        value = cursor.fetchone()[0]
        cursor.close()

        if value == 0:
            return False
        else:
            return True

    def _create_database(self, connection):
        # TODO: write database schema
        cursor = connection.cursor()
        pass

    @property
    def connection(self):
        self._conn = sqlite.connect(self._path)

        if not self._check_database(self._conn):
            self._create_database(self._conn)
        return self._conn

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

    data = {
        "format": "JSON",
        "aka": 1,
        "title": movie,
        "actors": actors,
        "limit": limit
    }

    params = urllib.parse.urlencode(data)
    connection = http.client.HTTPConnection(url)

    connection.request("GET", "/search?" + params)
    response = connection.getresponse()

    return json.loads(response.read().decode("utf-8"))

if __name__ == "__main__":
    args = init_args().parse_args(sys.argv[1:])

    if not args.root:
        root = os.path.sep.join([os.path.expanduser('~'), "Videos"])
    else:
        root = args.root

    check_structure(root)

    if not args.query:
        query = input("Movie to search: ")
    else:
        query = args.query

    print(find_movie(query))
