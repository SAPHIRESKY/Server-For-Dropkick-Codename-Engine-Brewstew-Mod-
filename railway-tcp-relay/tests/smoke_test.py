#!/usr/bin/env python3
"""Run a loopback integration smoke test for the TCP room relay."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

RELAY_DIR = Path(__file__).resolve().parents[1]
SERVER = RELAY_DIR / "dropkick_room_server.py"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def read_json_line(reader):
    line = reader.readline()
    if not line:
        raise AssertionError("relay closed the connection before replying")
    return json.loads(line.decode("utf-8"))


def main() -> int:
    port = free_port()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        [sys.executable, str(SERVER), "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(RELAY_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    host = guest = None
    try:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise AssertionError("relay exited during startup: " + (proc.stdout.read() if proc.stdout else ""))
            try:
                probe = socket.create_connection(("127.0.0.1", port), timeout=0.25)
                probe.close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise AssertionError("relay failed to start on loopback")

        host = socket.create_connection(("127.0.0.1", port), timeout=2)
        host.settimeout(3)
        host_reader = host.makefile("rb")
        host.sendall(b'{"type":"create","code":"BREW42"}\n')
        created = read_json_line(host_reader)
        assert created.get("type") == "created" and created.get("code") == "BREW42", created

        guest = socket.create_connection(("127.0.0.1", port), timeout=2)
        guest.settimeout(3)
        guest_reader = guest.makefile("rb")
        guest.sendall(b'{"type":"join","code":"BREW42"}\n')
        host_paired = read_json_line(host_reader)
        guest_paired = read_json_line(guest_reader)
        assert host_paired.get("type") == "paired", host_paired
        assert guest_paired.get("type") == "paired", guest_paired

        snapshot = {"type": "snapshot", "x": 123, "y": 456}
        host.sendall((json.dumps(snapshot, separators=(",", ":")) + "\n").encode())
        assert read_json_line(guest_reader) == snapshot

        guest_input = {"type": "input", "left": True, "jump": False}
        guest.sendall((json.dumps(guest_input, separators=(",", ":")) + "\n").encode())
        assert read_json_line(host_reader) == guest_input

        print("PASS: create, join, pair both clients, forward packets in both directions")
        return 0
    finally:
        for sock in (guest, host):
            if sock:
                try:
                    sock.close()
                except OSError:
                    pass
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)


if __name__ == "__main__":
    raise SystemExit(main())
