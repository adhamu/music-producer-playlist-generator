# Music Producer Playlist Generator

## Introduction
The aim of this project is to generate M3U playlists based on a music producer searching through a directory of MP3s.

## Requirements
- Python3
- Genius Music API token (https://docs.genius.com)

## Usage

```
usage: search.py [-h] -p Producers [-m MP3 folder path] [-i iTunes Library]
```

### One producer

```
python3 search.py -p 'Kanye West' -m '/Users/Amit/Music'
```

### Multiple Producers

```
python3 search.py -p 'Kanye West|Just Blaze' -m '/Users/Amit/Music'
```

### Using Your iTunes Library

```
python3 search.py -p 'Kanye West|Just Blaze' -i '/Users/Amit/iTunes/iTunes Music Library.xml'
```

## Notes
- Playlists are generated in the current working directory
- If a playlist exists, it will be appended to
- If a duplicate song exists in an existing playlist, it will be skipped
