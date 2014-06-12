# !/usr/bin/python3
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

from contextlib import closing
from sqlite3 import dbapi2 as sqlite


class Database():
    _commit = None
    _conn = None
    _path = None

    def __init__(self, path, commit=True):
        self._path = path + os.sep + ".movies.db"
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

    def _check_database(self):
        cursor = self._conn.cursor()
        cursor.execute("select count(*) from sqlite_master")
        value = cursor.fetchone()[0]
        cursor.close()

        if value == 0:
            return False
        else:
            return True

    def _set_db_parameters(self):
        pragmas = [
            "PRAGMA synchronous=OFF",
            "PRAGMA journal_mode=WAL",
            "PRAGMA foreign_keys=ON"
        ]
        with closing(self._conn.cursor()) as cursor:
            for item in pragmas:
                cursor.execute(item)
        self._conn.commit()

    def _create_database(self):
        # TODO: add table for actors
        tables = [
            "CREATE TABLE movies(movieid, year, poster, PRIMARY KEY(movieid))",
            "CREATE TABLE peoples(peopleid, name, PRIMARY KEY(peopleid))",
            "CREATE TABLE peoples_movies(movieid, peopleid, role, FOREIGN KEY(movieid) REFERENCES movies(movieid), FOREIGN KEY(peopleid) REFERENCES peoples(peopleid))",
            "CREATE TABLE genres(movieid, genre, FOREIGN KEY(movieid) REFERENCES movies(movieid))",
            "CREATE TABLE titles(movieid, country, name, FOREIGN KEY(movieid) REFERENCES movies(movieid))",
            "CREATE TABLE locations(movieid, path, FOREIGN KEY(movieid) REFERENCES movies(movieid))",
        ]

        with closing(self._conn.cursor()) as cursor:
            for item in tables:
                cursor.execute(item)
        self._conn.commit()

    @property
    def connection(self):
        self._conn = sqlite.connect(self._path)
        self._set_db_parameters()

        if not self._check_database():
            self._create_database()
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
        root + os.sep,
        root + os.sep + "By Actor",
        root + os.sep + "By Director",
        root + os.sep + "By Name",
        root + os.sep + "By Genre",
        root + os.sep + "By Year"
    ]

    for directory in subdirs:
        if not os.path.isdir(directory):
            os.makedirs(directory)

    return subdirs


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

def save_movie_data(movie, path):
    with Database(path) as dbs, closing(dbs.connection.cursor()) as cur:
        cur.execute("SELECT count(movieid) FROM movies WHERE movieid = ?", (movie["idIMDB"],))
        counted = cur.fetchone()[0]

        if counted > 0:
            print("Movie already in collection")
            sys.exit(0)
        else:
            # Add movie
            cur.execute("INSERT INTO movies VALUES(?, ?, ?)",
                        (movie["idIMDB"], movie["year"], movie["urlPoster"]))

            # Add directors
            for director in movie["directors"]:
                cur.execute("INSERT INTO peoples VALUES(?, ?)",
                            (director["nameId"], director["name"]))
                cur.execute("INSERT INTO peoples_movies VALUES(?, ?, ?)",
                            (movie["idIMDB"], director["nameId"], "director"))

            # Add directors
            for actor in movie["actors"]:
                cur.execute("INSERT INTO peoples VALUES(?, ?)",
                            (actor["actorId"], actor["actorName"]))
                cur.execute("INSERT INTO peoples_movies VALUES(?, ?, ?)",
                            (movie["idIMDB"], actor["actorId"], "actor"))

            # Add genres
            for genre in movie["genres"]:
                cur.execute("INSERT INTO genres VALUES(?, ?)",
                            (movie["idIMDB"], genre))

            # Add titles
            for title in movie["akas"]:
                cur.execute("INSERT INTO titles VALUES(?, ?, ?)",
                            (movie["idIMDB"], title["country"], title["title"]))

def save_movie_path(filename, movie, paths):
    # TODO: add code for link the filename
    with Database(paths[0]) as dbs, closing(dbs.connection.cursor()) as cur:
        # Actors and Directors
        roles = ["actor", "director"]
        pointer = 0
        for role in roles:
            pointer += 1
            cur.execute("SELECT peoples.name FROM peoples, peoples_movies"
                        " WHERE peoples.peopleid = peoples_movies.peopleid"
                        " AND peoples_movies.role = ? AND peoples_movies.movieid = ?",
                        (role, movie["idIMDB"]))

            for location in cur.fetchall():
                dest = paths[pointer] + os.sep + location[0]
                if not os.path.isdir(dest):
                    os.makedirs(dest)

        # TODO: add code for locate filename by movie name

        # Genre
        cur.execute("SELECT genre FROM genres WHERE movieid = ?", (movie["idIMDB"],))
        for location in cur.fetchall():
            dest = paths[4] + os.sep + location[0]
            if not os.path.isdir(dest):
                os.makedirs(dest)

        # Year
        cur.execute("SELECT year FROM movies where movieid = ?", (movie["idIMDB"],))
        for location in cur.fetchall():
            dest = paths[5] + os.sep + location[0]
            if not os.path.isdir(dest):
                os.makedirs(dest)

    # TODO: add code for remove old filename

def run(arguments):
    args = init_args().parse_args(arguments)

    if not args.root:
        root = os.path.sep.join([os.path.expanduser('~'), "Videos"])
    else:
        root = args.root

    paths = check_structure(root)

    if not args.query:
        query = input("Movie to search: ")
    else:
        query = args.query

    # For now, simple actor list is used
    movies = find_movie(query, actors="S")

    # NOTE: for now, only first result is saved
    save_movie_data(movies[0], paths[0])
    save_movie_path(args.movie, movies[0], paths)

if __name__ == "__main__":
    run(sys.argv[1:])
