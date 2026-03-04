import tkinter as tk
import socket
import sqlite3
import threading
import os
import pygame

class MP3Player:
    def __init__(self, master):
        self.master = master
        self.master.title("MP3 Playlist Manager")
        self.master.geometry("300x400")

        self.create_widgets()
        self.conn = self.setup_database()
        self.playlist = []

    def create_widgets(self):
        self.playlist_box = tk.Listbox(self.master)
        self.playlist_box.pack(pady=20)

        self.add_button = tk.Button(self.master, text="Add MP3", command=self.add_mp3)
        self.add_button.pack(pady=10)

        self.play_button = tk.Button(self.master, text="Play Selected", command=self.play_selected)
        self.play_button.pack(pady=10)

        self.stop_button = tk.Button(self.master, text="Stop", command=self.stop_playback)
        self.stop_button.pack(pady=10)

    def setup_database(self):
        conn = sqlite3.connect('playlist.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS songs (id INTEGER PRIMARY KEY, path TEXT)''')
        conn.commit()
        return conn

    def add_mp3(self):
        # Here, implement file dialog to select MP3 files and add to playlist and database
        
        # For simulation, let's add a hardcoded path
        path = 'song.mp3'
        self.playlist_box.insert(tk.END, path)
        self.playlist.append(path)
        c = self.conn.cursor()
        c.execute('INSERT INTO songs (path) VALUES (?)', (path,))
        self.conn.commit()

    def play_selected(self):
        try:
            selected = self.playlist_box.curselection()[0]
            song_to_play = self.playlist[selected]
            pygame.mixer.init()
            pygame.mixer.music.load(song_to_play)
            pygame.mixer.music.play()
        except IndexError:
            print("No song selected!")

    def stop_playback(self):
        pygame.mixer.music.stop()

    def start_udp_server(self):
        # Implement UDP server functionality here
        pass

if __name__ == '__main__':
    root = tk.Tk()
    mp3_player = MP3Player(root)
    root.mainloop()