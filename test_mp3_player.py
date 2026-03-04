# MISSION: Testing a remote-controller music player.
# STATUS: Research.
# VERSION: 0.0.1
# NOTES: Tweaking a fumbled CoPilot attempt.
# DATE: 2026-03-04 06:43:50
# FILE: test_mp3_player.py
# AUTHOR: Microsoft CoPilot
#
import unittest
import sqlite3
import os
import tempfile
import time
from pathlib import Path

import sys
sys.path.insert(0, os.path.dirname(__file__))

from mp3_player import (
    db_setup, db_add_song, db_get_playlists, db_get_songs_by_playlist,
    db_get_songs_by_playlists, db_update_status, scan_mp3_files, Mp3Player
)

class TestDatabaseSetup(unittest.TestCase):
    """Test database initialization"""
    
    def setUp(self):
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        import mp3_player
        self.original_db = mp3_player.DB_FILE
        mp3_player.DB_FILE = self.test_db.name
    
    def tearDown(self):
        import mp3_player
        mp3_player.DB_FILE = self.original_db
        if os.path.exists(self.test_db.name):
            os.remove(self.test_db.name)
    
    def test_db_setup_creates_tables(self):
        db_setup()
        conn = sqlite3.connect(self.test_db.name)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        self.assertIn('playlist', tables)
        self.assertIn('songs', tables)
        conn.close()
    
    def test_default_playlist_created(self):
        db_setup()
        playlists = db_get_playlists()
        self.assertGreater(len(playlists), 0)
        self.assertEqual(playlists[0][1], "Default Playlist")

class TestDatabaseOperations(unittest.TestCase):
    """Test CRUD operations"""
    
    def setUp(self):
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        import mp3_player
        self.original_db = mp3_player.DB_FILE
        mp3_player.DB_FILE = self.test_db.name
        db_setup()
    
    def tearDown(self):
        import mp3_player
        mp3_player.DB_FILE = self.original_db
        if os.path.exists(self.test_db.name):
            os.remove(self.test_db.name)
    
    def test_add_song(self):
        db_add_song('/test/song.mp3', 'Artist', 'Title')
        songs = db_get_songs_by_playlist(1)
        self.assertEqual(len(songs), 1)
        self.assertEqual(songs[0][1], 'Artist')
    
    def test_duplicate_prevention(self):
        db_add_song('/test/song.mp3', 'Artist', 'Title')
        db_add_song('/test/song.mp3', 'Artist', 'Title')
        songs = db_get_songs_by_playlist(1)
        self.assertEqual(len(songs), 1)
    
    def test_update_status(self):
        db_add_song('/test/song.mp3', 'Artist', 'Title')
        songs = db_get_songs_by_playlist(1)
        song_id = songs[0][0]
        db_update_status(song_id, 5)
        songs = db_get_songs_by_playlist(1)
        self.assertEqual(songs[0][4], 5)

class TestAudioPlayer(unittest.TestCase):
    """Test Mp3Player class"""
    
    def setUp(self):
        self.player = Mp3Player(lambda msg: None)
    
    def test_player_init(self):
        self.assertEqual(self.player.index, 0)
        self.assertEqual(self.player.playing, False)
    
    def test_stop(self):
        self.player.playing = True
        self.player.stop()
        self.assertEqual(self.player.playing, False)

if __name__ == '__main__':
    unittest.main(verbosity=2)

