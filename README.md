# Dropkick Relay Servers

## Recommended for the current Codename Engine mod: Railway TCP relay

**Do not run `npm start` in the game mod folder.** The current game's online code uses raw TCP sockets, so the compatible server is the Python TCP relay in `railway-tcp-relay/`. The root `Dockerfile` is configured to build and run that relay directly when this repository is deployed to Railway.

### One-time Railway setup

1. In Railway, create a new project and choose **Deploy from GitHub Repo**.
2. Select this repository and leave **Root Directory** at its default repository root (`/` or blank). The root `Dockerfile` builds the TCP relay.
3. Set the service variable `PORT=27666`.
4. In the service's **Settings → Networking**, create a **TCP Proxy** for internal port `27666`. Railway assigns a public hostname and public port.
5. In both players' copies of the game, open `mods/Dropkick/data/global.hx` and set:
   ```haxe
   static var dropkickRoomServerHost:String = "THE_PUBLIC_TCP_HOSTNAME";
   static var dropkickRoomServerPort:Int = THE_PUBLIC_TCP_PORT;
   ```
   Replace the examples with the exact hostname and numeric public port Railway assigned. Do not include `tcp://`, `http://`, or `https://` in the hostname.
6. Restart both games. The host creates a six-character code, and the friend joins using that code. Neither player runs a server on their own PC or forwards home-router ports.

Railway's TCP Proxy exposes raw TCP services and generates the public hostname and proxy port; see the official guide: https://docs.railway.com/networking/tcp-proxy.

### Local test (optional only)

The relay is Python, not Node. To test on the same PC only:
```powershell
cd railway-tcp-relay
py -3 dropkick_room_server.py --host 127.0.0.1 --port 27666
```
This loopback command is not the public hosting setup. You do not need to start the server on your PC after the Railway service is running.

### Verify deployment

- Startup log: `Dropkick room-code relay listening on 0.0.0.0:27666/TCP`.
- Host create: `Received create handshake`, then `Room CODE created`.
- Friend join: `Received join handshake`, then `Room CODE paired successfully`.
- If the game reports no reply, verify both clients use the exact same public TCP hostname and port and that the Railway service is deployed.

Rooms are stored in memory. Use one replica and create a new room after a server restart or redeploy. Review Railway's current plans and usage costs before deploying.

## Legacy HTTP relay (Render)

The older Node/HTTP relay is preserved under `server/` with the existing `render.yaml`. It is a different protocol and does **not** speak the raw TCP protocol used by the current `sys.net.Socket` game client. Do not deploy that legacy service for the current TCP client unless the game networking code is separately converted to HTTP.

See `START_HERE_RELAY_DEPLOYMENT.md` and `railway-tcp-relay/README.md` for the current setup.
