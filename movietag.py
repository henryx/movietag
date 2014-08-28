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
import shutil
import socket
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
                      default=os.path.sep.join([os.path.expanduser('~'), "Videos"]),
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

    try:
        connection.request("GET", "/search?" + params)
        response = connection.getresponse()

        if response.status == 200:
            return json.loads(response.read().decode("utf-8").replace("\\\\", "\\"))
        else:
            print("Service not available")
            sys.exit(1)
    except socket.gaierror as e:
        print(e)
        sys.exit(2)

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

def save_movie(filename, movie, paths, country):
    def add_location(cur, movieid, path):
        cur.execute("INSERT INTO locations VALUES(?, ?)", (movieid, path))

    def link_file(source, dest, destfile):
        if not os.path.isdir(dest):
            os.makedirs(dest)
        os.link(source, dest + os.sep + destfile)

    with Database(paths[0]) as dbs, closing(dbs.connection.cursor()) as cur:
        cur.execute("SELECT count(movieid) FROM movies WHERE movieid = ?", (movie["idIMDB"],))
        counted = cur.fetchone()[0]

        if counted > 0:
            print("Movie already in collection")
            sys.exit(0)

        # Add movie
        title = get_movie_title(movie, country)

        destfile = title + "." + filename.split(".")[-1]
        cur.execute("INSERT INTO movies VALUES(?, ?, ?, ?)",
                    (movie["idIMDB"], title, movie["year"], movie["urlPoster"]))
        dest = paths[3] + os.sep + title[0].lower()
        link_file(filename, dest, destfile)
        add_location(cur, movie["idIMDB"], dest + os.sep + destfile)

        dest = paths[5] + os.sep + movie["year"]
        link_file(filename, dest, destfile)
        add_location(cur, movie["idIMDB"], dest + os.sep + destfile)


        # Add directors
        for director in movie["directors"]:
            cur.execute("SELECT count(peopleid) FROM peoples WHERE peopleid = ?", (director["nameId"],))
            counted = cur.fetchone()[0]

            if counted == 0:
                cur.execute("INSERT INTO peoples VALUES(?, ?)",
                            (director["nameId"], director["name"]))

            cur.execute("INSERT INTO peoples_movies VALUES(?, ?, ?)",
                        (movie["idIMDB"], director["nameId"], "director"))
            dest = paths[2] + os.sep + director["name"]
            link_file(filename, dest, destfile)
            add_location(cur, movie["idIMDB"], dest + os.sep + destfile)

        # Add actors
        for actor in movie["actors"]:
            cur.execute("SELECT count(peopleid) FROM peoples WHERE peopleid = ?", (actor["actorId"],))
            counted = cur.fetchone()[0]

            if counted == 0:
                cur.execute("INSERT INTO peoples VALUES(?, ?)",
                            (actor["actorId"], actor["actorName"]))

            cur.execute("INSERT INTO peoples_movies VALUES(?, ?, ?)",
                        (movie["idIMDB"], actor["actorId"], "actor"))
            dest = paths[1] + os.sep + actor["actorName"]
            link_file(filename, dest, destfile)
            add_location(cur, movie["idIMDB"], dest + os.sep + destfile)

        # Add genres
        for genre in movie["genres"]:
            cur.execute("INSERT INTO genres VALUES(?, ?)",
                        (movie["idIMDB"], genre))
            dest = paths[4] + os.sep + genre
            link_file(filename, dest, destfile)
            add_location(cur, movie["idIMDB"], dest + os.sep + destfile)

    os.remove(filename)

def run(arguments):
    args = init_args().parse_args(arguments)

    paths = check_structure(args.root)

    if args.add:
        if not os.path.exists(args.add):
            print("File does not exists")
            sys.exit(1)

        # Move file to the root of the collection
        filename = paths[0] + os.sep + os.path.basename(args.add)
        shutil.move(args.add, filename)

        query = input("Movie to search: ")

        # For now, simple actor list is used
        for movie in find_movie(query, actors="S"):
            if len(movie["directors"]) == 0:
                message = "".join(['Is "', get_movie_title(movie, args.country),
                                 ' (', movie["year"], ')" (y/N)? '])
            else:
                message = "".join(['Is "', get_movie_title(movie, args.country),
                                 ' (',  movie["directors"][0]["name"], " - ",
                                 movie["year"], ')" (y/N)? '])
            selected = input(message)

            if not selected == "" and selected[0].lower() == 'y':
                save_movie(filename, movie, paths, args.country)
                break
        else:
            print("No movie selected")

    if args.query:
        # TODO: Add search in database
        pass

    if args.remove:
        # TODO: Add remove from collection
        pass

if __name__ == "__main__":
    run(sys.argv[1:])
