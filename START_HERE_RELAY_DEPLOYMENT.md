# Start here: Dropkick room-code relay

**You do not need to run `npm start` on your PC.** The new relay is Python and should run in the cloud so neither player needs to port-forward a home router.

## What is in this repository?

- The old Node/HTTP relay remains at the repository root.
- The newer TCP relay compatible with the current Codename Engine client is in [`railway-tcp-relay/`](railway-tcp-relay/).
- Do not run `npm start` from the game mod folder for the TCP relay; that folder intentionally has no `package.json`.

## One-time cloud deployment

1. Sign in to Railway and create a service from this GitHub repository.
2. Set the service's **Root Directory** to `/railway-tcp-relay`.
3. Deploy using the `Dockerfile` in that directory.
4. Add the service variable `PORT=27666`.
5. In the service's Networking settings, create a **TCP Proxy** for internal port `27666`.
6. Copy the exact public TCP hostname and public proxy port Railway gives you.
7. In both players' mod installations, set the two values in `mods/Dropkick/data/global.hx`:
   ```haxe
   static var dropkickRoomServerHost:String = "THE_PUBLIC_TCP_HOSTNAME";
   static var dropkickRoomServerPort:Int = THE_PUBLIC_TCP_PORT;
   ```
   Replace the examples with the exact values assigned by Railway. The hostname should not include `tcp://` or `https://`.
8. Restart both games, host a room, and share the six-character code.

The relay stores active rooms in memory. Keep it to one replica and create a fresh code after any server restart/redeploy. Review the host's current plan and possible charges before deploying.

## Local diagnostic (optional)

If you want to test the Python relay on your own PC only, open a terminal in this repository's `railway-tcp-relay` folder and run:

```powershell
py -3 dropkick_room_server.py --host 127.0.0.1 --port 27666
```

That local command is only for same-computer testing. It does not make the room server publicly reachable and is not the intended online-hosting setup.

## Test status

GitHub Actions runs a loopback smoke test for room creation, joining, pairing, and bidirectional packet forwarding whenever the relay files change. A passing test verifies server protocol behavior locally, not a live Railway deployment or game-client compatibility.
