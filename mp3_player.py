import os
import sqlite3
import socket
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pygame
import glob
import time

# ---- DATABASE SETUP ----

DB_FILE = 'mp3_playlist.db'

def db_setup():
    """Initialize database with required tables"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Create playlist table
    c.execute('''
        CREATE TABLE IF NOT EXISTS playlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE)
    ''')
    
    # Ensure first entry is 'Default Playlist'
    c.execute('SELECT COUNT(*) FROM playlist')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO playlist (name) VALUES (?)', ("Default Playlist",))
    
    # Create songs table
    c.execute('''
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status INTEGER NOT NULL DEFAULT 0,
            playlist INTEGER NOT NULL DEFAULT 1,
            artist TEXT,
            title TEXT,
            path TEXT NOT NULL UNIQUE,
            FOREIGN KEY (playlist) REFERENCES playlist(id))
    ''')
    
    conn.commit()
    conn.close()

def db_add_song(path, artist, title, playlist_id=1, status=0):
    """Add a song to the database if not already present"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT id FROM songs WHERE path=?', (path,))
    if c.fetchone() is None:
        c.execute(
            'INSERT INTO songs (path, artist, title, playlist, status) VALUES (?, ?, ?, ?, ?)',
            (path, artist, title, playlist_id, status)
        )
        conn.commit()
    conn.close()

def db_get_playlists():
    """Retrieve all playlists"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT id, name FROM playlist')
    playlists = c.fetchall()
    conn.close()
    return playlists

def db_get_songs_by_playlist(playlist_id):
    """Get songs from a specific playlist"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        'SELECT id, artist, title, path, status FROM songs WHERE playlist=?',
        (playlist_id,)
    )
    songs = c.fetchall()
    conn.close()
    return songs

def db_get_songs_by_playlists(playlist_ids):
    """Get songs from multiple playlists"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    placeholders = ', '.join('?' * len(playlist_ids))
    c.execute(
        f'SELECT id, artist, title, path, status FROM songs WHERE playlist IN ({placeholders})',
        tuple(playlist_ids)
    )
    songs = c.fetchall()
    conn.close()
    return songs

def db_update_status(song_id, new_status):
    """Update song status"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE songs SET status=? WHERE id=?', (new_status, song_id))
    conn.commit()
    conn.close()

# ---- UDP STATUS SERVER ----

def udp_status_server():
    """UDP server to receive status updates"""
    try:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_socket.bind(('0.0.0.0', 9999))
        print("UDP Server listening on port 9999...")
        while True:
            data, addr = udp_socket.recvfrom(1024)
            try:
                msg = data.decode().strip()
                parts = msg.split(':')
                if len(parts) == 2:
                    song_id, new_status = int(parts[0]), int(parts[1])
                    db_update_status(song_id, new_status)
                    print(f"Updated song {song_id} status to {new_status}")
            except Exception as e:
                print(f"Invalid UDP message: {e}")
    except Exception as e:
        print(f"UDP Server error: {e}")

# ---- FILE SCANNING ----

def scan_mp3_files(directory, playlist_id=1):
    """Recursively scan directory for MP3 files"""
    pattern = os.path.join(directory, '**', '*.mp3')
    count = 0
    for filepath in glob.glob(pattern, recursive=True):
        filename = os.path.basename(filepath)
        # Parse artist - title from filename
        if '-' in filename:
            parts = filename.rsplit('-', 1)
            artist = parts[0].strip()
            title = parts[1].rsplit('.', 1)[0].strip()
        else:
            artist = "Unknown Artist"
            title = filename.rsplit('.', 1)[0].strip()
        db_add_song(filepath, artist, title, playlist_id)
        count += 1
    return count

# ---- AUDIO PLAYER ----

class Mp3Player:
    def __init__(self, status_callback):
        pygame.mixer.init()
        self.playlist = []
        self.index = 0
        self.playing = False
        self.paused = False
        self.thread = None
        self.status_callback = status_callback
    
    def set_playlist(self, songs):
        """Set the playlist and reset index"""
        self.stop()
        self.playlist = songs
        self.index = 0
    
    def play(self):
        """Start playback"""
        if not self.playlist:
            return
        if self.thread and self.thread.is_alive():
            self.stop()
        self.thread = threading.Thread(target=self._play_loop, daemon=True)
        self.thread.start()
    
    def _play_loop(self):
        """Main playback loop"""
        self.playing = True
        while self.index < len(self.playlist) and self.playing:
            song_id, artist, title, path, status = self.playlist[self.index]
            self.status_callback(f"Playing: {artist} - {title}")
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    if not self.playing:
                        pygame.mixer.music.stop()
                        break
                    time.sleep(0.1)
                self.index += 1
            except Exception as e:
                print(f"Error playing {path}: {e}")
                self.index += 1
        self.playing = False
        self.status_callback("Stopped")
    
    def stop(self):
        """Stop playback"""
        self.playing = False
        pygame.mixer.music.stop()
    
    def pause(self):
        """Pause playback"""
        if self.playing:
            pygame.mixer.music.pause()
            self.paused = True
    
    def resume(self):
        """Resume playback"""
        if self.paused:
            pygame.mixer.music.unpause()
            self.paused = False

# ---- TKINTER GUI ----

class Mp3PlayerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MP3 Playlist Manager")
        self.geometry("750x550")
        
        db_setup()
        self.playlists = db_get_playlists()
        self.song_list = []
        
        # Build UI
        self._create_widgets()
        
        # Initialize player
        self.player = Mp3Player(self._update_status)
        
        # Refresh initial display
        self._refresh_song_list()
        
        # Start UDP server in background
        threading.Thread(target=udp_status_server, daemon=True).start()
    
    def _create_widgets(self):
        """Create GUI components"""
        # Top control frame
        top_frame = tk.Frame(self, bg='lightgray', padx=5, pady=5)
        top_frame.pack(fill=tk.X)
        
        tk.Button(top_frame, text="Add Songs...", command=self._add_songs).pack(side=tk.LEFT, padx=2)
        tk.Button(top_frame, text="Scan Folder...", command=self._scan_folder).pack(side=tk.LEFT, padx=2)
        tk.Button(top_frame, text="Play Default", command=self._play_default).pack(side=tk.LEFT, padx=2)
        tk.Button(top_frame, text="Play Selected", command=self._play_selected).pack(side=tk.LEFT, padx=2)
        tk.Button(top_frame, text="Stop", command=self.player.stop).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(top_frame, text='Playlist:').pack(side=tk.LEFT, padx=(20, 2))
        self.combo_playlist = ttk.Combobox(
            top_frame, 
            state='readonly',
            values=[name for _, name in self.playlists],
            width=20
        )
        self.combo_playlist.current(0)
        self.combo_playlist.pack(side=tk.LEFT, padx=2)
        self.combo_playlist.bind('<<ComboboxSelected>>', lambda e: self._refresh_song_list())
        
        # Song list frame with scrollbar
        list_frame = tk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.song_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=('Arial', 10))
        self.song_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.song_listbox.yview)
        
        # Status bar
        self.status_label = tk.Label(
            self, 
            text="Ready",
            relief=tk.SUNKEN,
            anchor=tk.W,
            padx=5
        )
        self.status_label.pack(fill=tk.X, side=tk.BOTTOM)
    
    def _add_songs(self):
        """Add songs manually"""
        paths = filedialog.askopenfilenames(filetypes=[("MP3 Files", "*.mp3")])
        if not paths:
            return
        
        playlist_id = self.playlists[self.combo_playlist.current()][0]
        for path in paths:
            filename = os.path.basename(path)
            if '-' in filename:
                artist, title = filename.rsplit('-', 1)
                title = title.rsplit('.', 1)[0]
            else:
                artist = "Unknown Artist"
                title = filename.rsplit('.', 1)[0]
            db_add_song(path, artist.strip(), title.strip(), playlist_id)
        
        self._refresh_song_list()
        messagebox.showinfo("Success", f"Added {len(paths)} song(s)")
    
    def _scan_folder(self):
        """Scan folder for MP3s"""
        directory = filedialog.askdirectory()
        if not directory:
            return
        
        playlist_id = self.playlists[self.combo_playlist.current()][0]
        count = scan_mp3_files(directory, playlist_id)
        self._refresh_song_list()
        messagebox.showinfo("Scan Complete", f"Found and added {count} MP3 file(s)")
    
    def _refresh_song_list(self):
        """Refresh the displayed song list"""
        playlist_id = self.playlists[self.combo_playlist.current()][0]
        self.song_list = db_get_songs_by_playlist(playlist_id)
        
        self.song_listbox.delete(0, tk.END)
        for song_id, artist, title, path, status in self.song_list:
            display_text = f"[{song_id}] {artist} - {title} | Status: {status}"
            self.song_listbox.insert(tk.END, display_text)
    
    def _play_default(self):
        """Play songs from default playlists (0 or 1)"""
        songs = db_get_songs_by_playlists([0, 1])
        if songs:
            self.player.set_playlist(songs)
            self.player.play()
        else:
            messagebox.showinfo("No Songs", "No songs in default playlists")
    
    def _play_selected(self):
        """Play songs from selected playlist"""
        playlist_id = self.playlists[self.combo_playlist.current()][0]
        songs = db_get_songs_by_playlist(playlist_id)
        if songs:
            self.player.set_playlist(songs)
            self.player.play()
        else:
            messagebox.showinfo("No Songs", f"No songs in selected playlist")
    
    def _update_status(self, message):
        """Update status bar"""
        self.status_label.config(text=message)

if __name__ == "__main__":
    app = Mp3PlayerApp()
    app.mainloop()
