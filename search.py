#!/usr/bin/env python3

"""
Searches a directory of MP3s and creates a playlist based on producer.

Uses genius.com's API.
"""

import os
import sys
import getopt
import requests
import eyed3
import math
import glob
import string
import credentials
from pathlib import Path
from libpytunes import Library

token = credentials.auth['token']
base_url = "https://api.genius.com"
headers = {
    'Authorization': 'Bearer ' + token
}

FORMAT_DESCRIPTOR = "#EXTM3U"
RECORD_MARKER = "#EXTINF"

target_producer = None
mp3_path = None
itunes_library = None

os.chdir(os.getcwd())


def search_song(file):
    """Search for tracks and return api path."""
    search_url = base_url + "/search"

    mp3_file = file
    file_path = os.path.realpath(mp3_file)
    audiofile = eyed3.load(mp3_file)
    artist = audiofile.tag.album_artist
    track_name = audiofile.tag.title
    track_length = math.ceil(audiofile.info.time_secs)
    search_term = str(artist) + ' ' + str(track_name)
    data = {'q': search_term}
    request = requests.get(search_url, data=data, headers=headers)
    response = request.json()

    print('= Searching for ' + search_term)
    if response['response']['hits']:
        match = response['response']['hits'][0]

        return {
            'artist': artist,
            'track_name': track_name,
            'track_length': track_length,
            'mp3_path': file_path,
            'api_path': match['result']['api_path']
        }
    else:
        print('= No results found')
        return None


def lookup_song_info(artist, song_api_path, track_name, track_length, mp3_path):
    """Look up a song for further information by song_api_path."""
    search_url = base_url + song_api_path
    request = requests.get(search_url, data={}, headers=headers)
    response = request.json()

    if len(response['response']['song']['producer_artists']):
        for producer in response['response']['song']['producer_artists']:
            translator = str.maketrans('', '', string.punctuation)
            if producer['name'].translate(translator) in target_producer.translate(translator):
                print('== ' + producer['name'] + ' produced ' + track_name + '. Adding to playlist')
                append_to_playlist(
                    'Produced by ' + target_producer,
                    mp3_path,
                    track_length,
                    artist,
                    track_name
                )
                break
            else:
                print('== Didn\'t match the producer we were searching for')
    else:
        print('== Couldn\'t find any producers for this track')


def append_to_playlist(playlist_name, mp3_path, track_length, artist, track_name):
    """Append to playlist."""
    playlist = Path(playlist_name + '.m3u')
    if not playlist.is_file():
        create_playlist(playlist_name)

    fp = open(playlist_name + '.m3u', 'a+')
    fp.write(RECORD_MARKER + ":" + str(track_length) + "," + artist + " - " + track_name + "\n")
    fp.write(mp3_path + "\n")
    fp.close()


def _usage():
    """Print the usage message."""
    msg = "Usage:  search.py [options] producer-name mp3-path\n"
    msg += __doc__ + "\n"
    msg += "Options:\n"
    msg += "%5s,\t%s==%s\n" % (
        "-p", "--producer-name",
        "the producer you're searching for"
    )
    msg += "%5s,\t%s==%s\n" % (
        "-m", "--mp3-path",
        "directory where your mp3s live"
    )
    msg += "%5s,\t%s==%s\n" % (
        "-i", "--itunes-library-xml",
        "Absolute path to iTunes library XML file (overrides mp3_path)"
    )
    msg += "%5s,\t%s==\t%s" % (
        "-h", "--help",
        "display this help and exit"
    )

    print(msg)


def create_playlist(playlist_name):
    """Create a playlist."""
    fp = open(playlist_name + '.m3u', 'a+')
    fp.write(FORMAT_DESCRIPTOR + '\n')
    fp.close()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        _usage()
        sys.exit(1)

    options = 'pmi'
    long_options = ['producer-name', 'mp3-path', 'itunes-library-xml']

    try:
        opts, args = getopt.getopt(sys.argv[1:], options, long_options)
    except getopt.GetoptError:
        _usage()
        sys.exit(1)

    for o, a in opts:
        if o in ("-h", "--help"):
            _usage()
            sys.exit(1)

    try:
        target_producer = args[0]
    except:
        pass

    try:
        mp3_path = Path(args[1])
    except:
        pass

    try:
        itunes_library = Path(args[2])
    except:
        pass

    if target_producer is None or mp3_path is None:
        _usage()
        sys.exit(1)

    if itunes_library is None:
        if not mp3_path.is_dir():
            raise Exception('mp3_path is not a directory')
            sys.exit(1)
        else:
            mp3_path = os.path.realpath(mp3_path)
    else:
        if not itunes_library.is_file():
            raise Exception('itunes library doesn\'t exist')
            sys.exit(1)
        else:
            itunes_library = os.path.realpath(itunes_library)

    print('Gonna try and find songs produced by ' + target_producer)

    if itunes_library is None:
        print('Searching through path of MP3s')
        for file in glob.glob(mp3_path + "/**/*.mp3", recursive=True):
            song_info = search_song(file)
            if song_info is not None:
                lookup_song_info(
                    song_info['artist'],
                    song_info['api_path'],
                    song_info['track_name'],
                    song_info['track_length'],
                    song_info['mp3_path']
                )
    else:
        print('Searching through iTunes library')
        l = Library(itunes_library)
        for id, song in l.songs.items():
            if song:
                song_info = search_song('/' + song.location)
                if song_info is not None:
                    lookup_song_info(
                        song_info['artist'],
                        song_info['api_path'],
                        song_info['track_name'],
                        song_info['track_length'],
                        song_info['mp3_path']
                    )
