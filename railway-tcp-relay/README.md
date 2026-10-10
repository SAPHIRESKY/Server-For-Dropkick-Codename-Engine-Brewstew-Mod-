# Dropkick Room-Code Relay (Railway TCP)

This is the raw TCP relay for the current Codename Engine Dropkick client using `sys.net.Socket` and newline-delimited JSON.

## Recommended deployment: repository root

The repository root now contains a `Dockerfile` and `railway.json` that build and run this Python relay. In Railway:

1. Create a new project and select **Deploy from GitHub Repo**.
2. Choose `SAPHIRESKY/Server-For-Dropkick-Codename-Engine-Brewstew-Mod-`.
3. Leave Root Directory at the default repository root. Do **not** set it to this subfolder for the recommended setup.
4. Set service variable `PORT=27666`.
5. In **Settings → Networking**, create a **TCP Proxy** for internal port `27666`. Railway displays the public hostname and public proxy port.
6. Keep the relay at one replica; room codes are stored in memory and are not shared across replicas.

## Configure both game clients

Open `mods/Dropkick/data/global.hx` in both players' game installations and set these values to the exact TCP proxy details provided by Railway:

```haxe
static var dropkickRoomServerHost:String = "THE_PUBLIC_TCP_HOSTNAME";
static var dropkickRoomServerPort:Int = THE_PUBLIC_TCP_PORT;
```

Use the actual hostname without `tcp://`, `http://`, or `https://`; the port must be the numeric **public proxy port**, not necessarily 27666. Restart both games. The host creates a six-character code and the other player joins with that code.

## Optional folder-only deployment

If you deliberately set Railway's Root Directory to `/railway-tcp-relay`, the Dockerfile in this folder also works. In that case, set `PORT=27666` and use the same TCP Proxy procedure.

## Verify and troubleshoot

- Startup log: `Dropkick room-code relay listening on 0.0.0.0:27666/TCP`.
- Host create: `Received create handshake`, then `Room CODE created`.
- Guest join: `Received join handshake`, then `Room CODE paired successfully`.
- If a room fails to create/join, check both clients use the exact same Railway public TCP hostname and port and check deployment logs.
- Restarting/redeploying clears rooms; create a new code after a restart.

## Security and limits

Room assignments live in memory, without accounts or anti-cheat. Share room codes only with the intended friend. This service relays gameplay packets; it does not run the game simulation. Review Railway's current plans and charges before deploying. Do not publish account credentials or tokens.
