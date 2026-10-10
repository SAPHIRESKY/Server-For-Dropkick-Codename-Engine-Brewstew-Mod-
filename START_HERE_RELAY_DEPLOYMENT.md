# Start here: Dropkick online room-code relay

**You do not need to run `npm start` on your PC.** The current relay is Python and should run online. The reason `npm start` failed is that your game folder does not contain the Node `package.json` for this service.

## Do this once

1. Open [your GitHub repository](https://github.com/SAPHIRESKY/Server-For-Dropkick-Codename-Engine-Brewstew-Mod-).
2. Open [Railway](https://railway.com/) and sign in.
3. Create a new project using **Deploy from GitHub Repo**, then select this repository.
4. Leave **Root Directory** at the default repository root. The root `Dockerfile` automatically builds the new Python TCP relay.
5. Add the service variable `PORT=27666`.
6. In the service's **Settings → Networking**, add a **TCP Proxy** for internal port `27666`. Railway creates a public TCP hostname and a public proxy port.
7. Copy the exact hostname and numeric public port from Railway.

## Set up both copies of the game

In both PCs' game folders, open `mods/Dropkick/data/global.hx` and replace the placeholders:

```haxe
static var dropkickRoomServerHost:String = "THE_PUBLIC_TCP_HOSTNAME";
static var dropkickRoomServerPort:Int = THE_PUBLIC_TCP_PORT;
```

Use Railway's real hostname and public proxy port. Do not put a URL scheme like `https://` before the hostname. Save, then restart both games.

Now your host chooses a six-character code, and your friend enters that code using **Join Online Match**. Neither player has to run a server locally or configure home-router port forwarding.

## If you get stuck

- `npm start` is not the deployment command for this Python relay.
- Railway startup log should mention listening on `0.0.0.0:27666/TCP`.
- After a friend enters the code, the logs should show a `join` handshake and `paired successfully`.
- Both clients must point to the same Railway TCP proxy hostname and public port.
- Rooms are stored in memory. After the service restarts, create a fresh room code.

Railway's official guide for raw TCP services: https://docs.railway.com/networking/tcp-proxy

You may need to sign in, choose a plan, or confirm any potential hosting charges in Railway. Do not share your Railway password or API tokens.
