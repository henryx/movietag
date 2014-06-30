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
        tables = [
            "CREATE TABLE movies(movieid, title, year, poster, PRIMARY KEY(movieid))",
            "CREATE TABLE peoples(peopleid, name, PRIMARY KEY(peopleid))",
            "CREATE TABLE peoples_movies(movieid, peopleid, role, FOREIGN KEY(movieid) REFERENCES movies(movieid), FOREIGN KEY(peopleid) REFERENCES peoples(peopleid))",
            "CREATE TABLE genres(movieid, genre, FOREIGN KEY(movieid) REFERENCES movies(movieid))",
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
    args.add_argument("-c", "--country", metavar="<country>", default="(original title)",
                      help="Title used in country (default the original title)")

    group = args.add_mutually_exclusive_group(required=True)

    group.add_argument("-q", "--query", metavar="<movie>",
                      help="Search movie")
    group.add_argument("-d", "--remove", metavar="<movie>",
                      help="Remove movie")
    group.add_argument("-a", "--add", metavar="<movie>", type=str,
                      help="Add movie")
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

def find_movie(movie, actors="N", limit=10):
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

    return json.loads(response.read().decode("utf-8").replace("\\\\", "\\"))

def get_movie_title(movie, country):
    # Get the title
    title = movie["title"]

    # Check if exist a translated title
    if "akas" in movie:
        for item in movie["akas"]:
            if item["country"].lower() == country.lower():
                title = item["title"]
                break

    return title

def save_movie_data(movie, path, country):
    with Database(path) as dbs, closing(dbs.connection.cursor()) as cur:
        cur.execute("SELECT count(movieid) FROM movies WHERE movieid = ?", (movie["idIMDB"],))
        counted = cur.fetchone()[0]

        if counted > 0:
            print("Movie already in collection")
            sys.exit(0)
        else:
            title = get_movie_title(movie, country)

            # Add movie
            cur.execute("INSERT INTO movies VALUES(?, ?, ?, ?)",
                        (movie["idIMDB"], title, movie["year"], movie["urlPoster"]))

            # Add directors
            for director in movie["directors"]:
                cur.execute("SELECT count(peopleid) FROM peoples WHERE peopleid = ?", (director["nameId"],))
                counted = cur.fetchone()[0]

                if counted == 0:
                    cur.execute("INSERT INTO peoples VALUES(?, ?)",
                                (director["nameId"], director["name"]))
                    cur.execute("INSERT INTO peoples_movies VALUES(?, ?, ?)",
                                (movie["idIMDB"], director["nameId"], "director"))

            # Add actors
            for actor in movie["actors"]:
                cur.execute("SELECT count(peopleid) FROM peoples WHERE peopleid = ?", (actor["actorId"],))
                counted = cur.fetchone()[0]

                if counted == 0:
                    cur.execute("INSERT INTO peoples VALUES(?, ?)",
                                (actor["actorId"], actor["actorName"]))
                    cur.execute("INSERT INTO peoples_movies VALUES(?, ?, ?)",
                                (movie["idIMDB"], actor["actorId"], "actor"))

            # Add genres
            for genre in movie["genres"]:
                cur.execute("INSERT INTO genres VALUES(?, ?)",
                            (movie["idIMDB"], genre))

def save_movie_path(filename, movie, paths):
    def add_location(cur, movieid, path):
        cur.execute("INSERT INTO locations VALUES(?, ?)", (movieid, path))

    with Database(paths[0]) as dbs, closing(dbs.connection.cursor()) as cur:
        # Get title and year
        cur.execute("SELECT title, year FROM movies where movieid = ?", (movie["idIMDB"],))
        data = cur.fetchone()

        destfile = data[0] + "." + filename.split(".")[-1]

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
                os.link(filename, dest + os.sep + destfile)
                add_location(cur, movie["idIMDB"], dest + os.sep + destfile)

        # Title
        dest = paths[3] + os.sep + data[0][0].lower()
        if not os.path.isdir(dest):
            os.makedirs(dest)
        os.link(filename, dest + os.sep + destfile)
        add_location(cur, movie["idIMDB"], dest + os.sep + destfile)

        # Genre
        cur.execute("SELECT genre FROM genres WHERE movieid = ?", (movie["idIMDB"],))
        for location in cur.fetchall():
            dest = paths[4] + os.sep + location[0]
            if not os.path.isdir(dest):
                os.makedirs(dest)
            os.link(filename, dest + os.sep + destfile)
            add_location(cur, movie["idIMDB"], dest + os.sep + destfile)

        # Year
        dest = paths[5] + os.sep + data[1]
        if not os.path.isdir(dest):
            os.makedirs(dest)
        os.link(filename, dest + os.sep + destfile)
        add_location(cur, movie["idIMDB"], dest + os.sep + destfile)

    os.remove(filename)

def run(arguments):
    args = init_args().parse_args(arguments)

    if not args.root:
        root = os.path.sep.join([os.path.expanduser('~'), "Videos"])
    else:
        root = args.root

    paths = check_structure(root)

    if args.add:
        if not os.path.exists(args.add):
            print("File does not exists")
            sys.exit(1)

        query = input("Movie to search: ")

        # TODO: extract more results and choice the correct value
        # For now, simple actor list is used

        for movie in find_movie(query, actors="S"):
            selected = input('Is "' + get_movie_title(movie, args.country) + '" (y/N)? ')

            if not selected == "" and selected[0].lower() == 'y':
                save_movie_data(movie, paths[0], args.country)
                save_movie_path(args.add, movie, paths)

    if args.query:
        # TODO: Add search in database
        pass

    if args.remove:
        # TODO: Add remove from collection
        pass

if __name__ == "__main__":
    run(sys.argv[1:])
