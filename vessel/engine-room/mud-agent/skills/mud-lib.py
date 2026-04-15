#!/usr/bin/env python3
"""mud-lib.py — MUD connection utilities for fleet agents."""

import socket
import time

class MudClient:
    def __init__(self, host="147.224.38.131", port=7777):
        self.host = host
        self.port = port
        self.sock = None
    
    def connect(self, name, role="vessel"):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5)
        self.sock.connect((self.host, self.port))
        time.sleep(0.5)
        self._read()
        self._send(name)
        time.sleep(0.5)
        self._read()
        self._send(role)
        time.sleep(1)
        return self._read()
    
    def _send(self, text):
        self.sock.sendall((text + "\n").encode())
    
    def _read(self):
        try:
            return self.sock.recv(8192).decode("utf-8", errors="replace").strip()
        except socket.timeout:
            return ""
    
    def go(self, room):
        return self.cmd(f"go {room}")
    
    def look(self):
        return self.cmd("look")
    
    def say(self, message):
        return self.cmd(f"say {message}")
    
    def whisper(self, target, message):
        return self.cmd(f"whisper {target} {message}")
    
    def read_notes(self):
        return self.cmd("read")
    
    def who(self):
        return self.cmd("who")
    
    def write_note(self, text):
        return self.cmd(f"write {text}")
    
    def cmd(self, text, delay=1.0):
        self._send(text)
        time.sleep(delay)
        return self._read()
    
    def disconnect(self):
        if self.sock:
            self.sock.close()
