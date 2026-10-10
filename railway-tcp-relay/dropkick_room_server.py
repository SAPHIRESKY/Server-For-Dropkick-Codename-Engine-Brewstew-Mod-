#!/usr/bin/env python3
"""Small TCP room-code relay for Dropkick Brewstew's Codename Engine mod.

Hosts connect outbound and request a room code. Joiners connect outbound and
submit that code. The server pairs one joiner with each host and relays the
existing newline-delimited JSON match packets in both directions.

Run on a publicly reachable machine where you can expose one TCP port:
    python3 dropkick_room_server.py --host 0.0.0.0 --port 27666
"""
from __future__ import annotations

import argparse
import json
import logging
import secrets
import socket
import socketserver
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # Avoid I/1 and O/0 confusion.
CODE_LENGTH = 6
MAX_LINE_BYTES = 64 * 1024
ROOMS: dict[str, "Room"] = {}
ROOMS_LOCK = threading.RLock()


class Peer:
    def __init__(self, sock: socket.socket, address: tuple[str, int]):
        self.sock = sock
        self.address = address
        self.send_lock = threading.Lock()
        self.room: Optional[Room] = None
        self.role: Optional[str] = None
        self.alive = True

    def send_raw(self, payload: bytes) -> None:
        with self.send_lock:
            if not self.alive:
                raise ConnectionError("peer is closed")
            self.sock.sendall(payload)

    def send_json(self, payload: dict) -> None:
        self.send_raw(json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n")

    def close(self) -> None:
        self.alive = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass


@dataclass
class Room:
    code: str
    host: Peer
    created_at: float = field(default_factory=time.monotonic)
    guest: Optional[Peer] = None


def make_code() -> str:
    with ROOMS_LOCK:
        for _ in range(100):
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
            if code not in ROOMS:
                return code
    raise RuntimeError("could not allocate an unused room code")


class RoomRelayHandler(socketserver.StreamRequestHandler):
    def setup(self):
        super().setup()
        self.request.settimeout(25.0)
        self.peer = Peer(self.request, self.client_address)

    def _read_line(self) -> Optional[bytes]:
        line = self.rfile.readline(MAX_LINE_BYTES + 1)
        if not line:
            return None
        if len(line) > MAX_LINE_BYTES or not line.endswith(b"\n"):
            try:
                self.peer.send_json({"type": "error", "message": "packet too large"})
            except OSError:
                pass
            return None
        return line

    def handle(self):
        logging.info("TCP connection accepted from %s:%d", self.client_address[0], self.client_address[1])
        try:
            handshake_line = self._read_line()
        except socket.timeout:
            logging.warning("Client %s connected but sent no room handshake before timeout", self.client_address[0])
            self.peer.close()
            return
        except OSError as exc:
            logging.info("Client %s disconnected before room handshake: %s", self.client_address[0], exc)
            self.peer.close()
            return
        if handshake_line is None:
            self.peer.close()
            return
        try:
            handshake = json.loads(handshake_line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._error("invalid handshake")
            return

        action = handshake.get("type") if isinstance(handshake, dict) else None
        logging.info("Received %s handshake from %s", action or "unknown", self.client_address[0])
        if action == "create":
            self._create_room(handshake.get("code", ""))
        elif action == "join":
            self._join_room(handshake.get("code", ""))
        else:
            self._error("expected create or join handshake")
            return

        if self.peer.room is None:
            return

        try:
            while True:
                line = self._read_line()
                if line is None:
                    break
                room = self.peer.room
                if room is None:
                    break
                other = room.guest if self.peer.role == "host" else room.host
                if other is None:
                    continue
                try:
                    other.send_raw(line)
                except OSError:
                    break
        except (OSError, ConnectionError, socket.timeout):
            pass
        finally:
            self._detach_peer()

    def _create_room(self, requested_code=""):
        try:
            if not isinstance(requested_code, str):
                self._error("room code must be six valid characters")
                return
            code = requested_code.strip().upper()
            has_requested_code = bool(code)
            if code:
                if len(code) != CODE_LENGTH or any(ch not in CODE_ALPHABET for ch in code):
                    self._error("room code must be six valid characters (A-H, J-N, P-Z, 2-9)")
                    return
            else:
                code = make_code()

            with ROOMS_LOCK:
                if not has_requested_code and code in ROOMS:
                    code = make_code()
                    while code in ROOMS:
                        code = make_code()
                already_in_use = code in ROOMS
                if not already_in_use:
                    room = Room(code=code, host=self.peer)
                    ROOMS[code] = room
                    self.peer.room = room
                    self.peer.role = "host"
            if already_in_use:
                self._error("room code already in use; choose another code")
                return
            self.request.settimeout(None)
            self.peer.send_json({"type": "created", "code": code})
            logging.info("Room %s created by %s", code, self.client_address[0])
        except (OSError, RuntimeError) as exc:
            self._error("could not create room")
            logging.warning("room creation failed: %s", exc)

    def _join_room(self, requested_code):
        if not isinstance(requested_code, str):
            self._error("invalid room code")
            return
        code = requested_code.strip().upper()
        if len(code) != CODE_LENGTH or any(ch not in CODE_ALPHABET for ch in code):
            self._error("room code must be 6 valid characters")
            return
        with ROOMS_LOCK:
            room = ROOMS.get(code)
            if room is None or not room.host.alive:
                room = None
            elif room.guest is not None:
                self._error("room is already full")
                return
            else:
                room.guest = self.peer
                self.peer.room = room
                self.peer.role = "client"
                self.request.settimeout(None)
        if room is None:
            self._error("room not found; check the code and ask the host to create a new room")
            return
        try:
            room.host.send_json({"type": "paired", "role": "host"})
            self.peer.send_json({"type": "paired", "role": "client"})
            logging.info("Room %s paired successfully; sent pairing notice to host and joiner (%s)", code, self.client_address[0])
        except OSError:
            self._detach_peer()
            self._error("could not connect both players")

    def _error(self, message: str):
        try:
            self.peer.send_json({"type": "error", "message": message})
        except OSError:
            pass
        self.peer.close()

    def _detach_peer(self):
        peer = self.peer
        room = peer.room
        peer.close()
        if room is None:
            return
        other: Optional[Peer] = None
        with ROOMS_LOCK:
            if room.host is peer:
                ROOMS.pop(room.code, None)
                other = room.guest
            elif room.guest is peer:
                room.guest = None
                other = room.host
            peer.room = None
        if other is not None and other.alive:
            notice = {"type": "closed"} if peer.role == "host" else {"type": "leave"}
            try:
                other.send_json(notice)
            except OSError:
                pass
        logging.info("Peer disconnected from room %s", room.code)


class ThreadedRoomServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 128


def main() -> int:
    parser = argparse.ArgumentParser(description="Dropkick room-code TCP relay")
    parser.add_argument("--host", default="0.0.0.0", help="bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=27666, help="TCP port (default: 27666)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        with ThreadedRoomServer((args.host, args.port), RoomRelayHandler) as server:
            logging.info("Dropkick room-code relay listening on %s:%d/TCP", args.host, args.port)
            logging.info("Configure dropkickRoomServerHost and dropkickRoomServerPort in mods/Dropkick/data/global.hx using the public TCP proxy host and port.")
            server.serve_forever(poll_interval=0.5)
    except OSError as exc:
        logging.error("cannot listen on %s:%d: %s", args.host, args.port, exc)
        return 1
    except KeyboardInterrupt:
        logging.info("stopping relay")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
