#!/usr/bin/env python3

"""
Searches a directory of MP3s and creates a playlist based on producer.

Uses genius.com's API.
"""

import re
import os
import sys
import requests
import eyed3
import math
import glob
import string
import credentials
import argparse
import pickle
import time
from pathlib import Path
from libpytunes import Library
from colorama import Fore, Style

base_url = "https://api.genius.com"
headers = {
    'Authorization': 'Bearer ' + credentials.auth['token']
}

FORMAT_DESCRIPTOR = "#EXTM3U"
RECORD_MARKER = "#EXTINF"

target_producers = None
target_producer_list = None
mp3_path = None
itunes_library = None


def get_song_details_using_id3(mp3_file):
    """Search for tracks and return api path."""
    file_path = os.path.realpath(mp3_file)
    audiofile = eyed3.load(mp3_file)

    if audiofile is None:
        print(Fore.RED + 'Couldn\'t load ID3 tag')
        return None

    artist = str(audiofile.tag.artist)
    if audiofile.tag.album_artist:
        artist = str(audiofile.tag.album_artist)
    track_name = str(audiofile.tag.title)
    track_length = math.ceil(audiofile.info.time_secs)
    search_term = str(artist) + ' ' + str(track_name)

    print(
        Fore.YELLOW +
        str(search_term) + ' - ' +
        str(track_length) + 's'
    )

    lookup = search(search_term)
    if lookup is not None:
        match = lookup[0]

        return {
            'artist': artist,
            'track_name': track_name,
            'track_length': track_length,
            'mp3_path': file_path,
            'api_path': match['result']['api_path']
        }
    else:
        print(Fore.RED + 'No results found')
        return None


def get_song_details_using_itunes(song):
    """Search song using iTunes library XML."""
    file_path = os.path.realpath('/' + str(song.location))
    artist = str(song.artist)
    if song.album_artist:
        artist = str(song.album_artist)
    track_name = str(song.name)
    track_length = math.ceil(song.length / 1000)
    search_term = str(artist) + ' ' + str(track_name)

    print(
        Fore.YELLOW +
        str(search_term) + ' - ' +
        str(track_length) + 's'
    )

    lookup = search(search_term)
    if lookup is not None:
        match = lookup[0]

        return {
            'artist': artist,
            'track_name': track_name,
            'track_length': track_length,
            'mp3_path': file_path,
            'api_path': match['result']['api_path']
        }
    else:
        print(Fore.RED + 'No results found')
        return None


def search(term):
    """Make a search on Genius.com for a song."""
    search_url = base_url + "/search"
    term.replace('[', '(')
    term.replace(']', ')')
    term = term.lower()

    strip_out_excess_song_info = re.compile(r"^(.*)((\(?.)(ft|feat|prod|bonus))", re.IGNORECASE)
    search_modified = re.search(strip_out_excess_song_info, term)

    if search_modified is not None and search_modified.group(1):
        term = search_modified.group(1)

    data = {'q': term}
    request = requests.get(search_url, data=data, headers=headers)
    response = request.json()

    return response['response']['hits'] or None


def lookup_song_info(artist, song_api_path, track_name, track_length, mp3_path):
    """Look up a song for further information by song_api_path."""
    search_url = base_url + song_api_path
    request = requests.get(search_url, data={}, headers=headers)
    response = request.json()

    translator = str.maketrans('', '', string.punctuation)

    if len(response['response']['song']['producer_artists']):

        actual_producers = response['response']['song']['producer_artists']

        producer_list = [
            str(producer['name'].translate(translator)).lower()
            for producer in actual_producers
        ]

        matches = [
            c for c in target_producer_list if c.translate(translator).lower() in producer_list
        ]

        if matches:
            append_to_playlist(
                'Produced by ' + str(matches[0]).title(),
                mp3_path,
                track_length,
                artist,
                track_name
            )

    else:
        print(Fore.RED + 'Couldn\'t find any producers for this track')


def append_to_playlist(playlist_name, mp3_path, track_length, artist, track_name):
    """Append to playlist."""
    playlist = Path(playlist_name + '.m3u')
    if not playlist.is_file():
        create_playlist(playlist_name)

    l = str(RECORD_MARKER) + ":" + str(track_length) + "," + str(artist) + " - " + str(track_name)
    if l not in open(playlist_name + '.m3u').read():
        print(Fore.GREEN + 'Adding ' + track_name + ' to ' + playlist_name)
        fp = open(playlist_name + '.m3u', 'a+')
        fp.write(l + "\n")
        fp.write(mp3_path + "\n")
        fp.close()
    else:
        print(Fore.BLUE + 'Skipping... ' + track_name + ' exists in ' + playlist_name)


def create_playlist(playlist_name):
    """Create a playlist."""
    fp = open(playlist_name + '.m3u', 'a+')
    fp.write(FORMAT_DESCRIPTOR + '\n')
    fp.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Searches a directory of MP3s and creates a playlist based on producer.'
    )
    parser.add_argument(
        '-p',
        metavar='Producers',
        type=str,
        required=True,
        help='The producer(s) you\'re searching for. Pipe delimited for multiple'
    )
    parser.add_argument(
        '-m',
        metavar='MP3 folder path',
        type=str,
        default='.',
        help='Absolute directory path to MP3s. (Default = current directory)'
    )
    parser.add_argument(
        '-i',
        metavar='iTunes Library',
        type=str,
        required=False,
        help='Absolute path to iTunes Library XML file. If provided, will override -m'
    )

    args = parser.parse_args()

    target_producers = args.p
    target_producer_list = target_producers.split('|')
    mp3_path = Path(args.m)

    if args.i is None:
        if not mp3_path.is_dir():
            raise Exception('mp3_path is not a directory')
            sys.exit(1)
        else:
            mp3_path = os.path.realpath(mp3_path)
    else:
        itunes_library = Path(args.i)
        if not itunes_library.is_file():
            raise Exception('iTunes library doesn\'t exist')
            sys.exit(1)
        else:
            itunes_library = os.path.realpath(itunes_library)

    print(Fore.YELLOW + 'Will create playlists for these producers: ', target_producers.split('|'))
    if itunes_library is None:
        print(Fore.BLUE + 'Searching through path of MP3s')
        for file in glob.glob(mp3_path + "/**/*.mp3", recursive=True):
            song_info = get_song_details_using_id3(file)
            if song_info is not None:
                lookup_song_info(
                    song_info['artist'],
                    song_info['api_path'],
                    song_info['track_name'],
                    song_info['track_length'],
                    song_info['mp3_path']
                )
    else:
        print(Fore.BLUE + 'Searching through iTunes library')
        lib_path = itunes_library
        pickle_file = "itl.p"
        expiry = 60 * 60
        epoch_time = int(time.time())

        if not os.path.isfile(pickle_file) or os.path.getmtime(pickle_file) + expiry < epoch_time:
            itl_source = Library(lib_path)
            pickle.dump(itl_source, open(pickle_file, "wb"))

        itl = pickle.load(open(pickle_file, "rb"))

        for id, song in itl.songs.items():
            if song:
                song_info = get_song_details_using_itunes(song)
                if song_info is not None:
                    lookup_song_info(
                        song_info['artist'],
                        song_info['api_path'],
                        song_info['track_name'],
                        song_info['track_length'],
                        song_info['mp3_path']
                    )

    print(Style.RESET_ALL)
