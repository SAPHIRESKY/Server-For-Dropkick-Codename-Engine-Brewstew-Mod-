# Dropkick Worldwide Relay

This small public HTTP relay provides six-character room codes for the Codename Engine Dropkick mod. It carries lobby messages, guest input, and host-authoritative game snapshots. It does not need a database or any npm dependencies beyond Node itself.

## Deploy it publicly (Render example)

1. Make a new Git repository for the relay.
2. Upload the **contents** of this ZIP so `render.yaml` is at the repository root and `server/index.js` / `server/package.json` are under `server/`.
3. On Render, choose **New → Blueprint**, connect that repository, and apply the Blueprint. The included Blueprint sets up a public Node web service with `server/` as its root directory and `/health` as the health check.
4. When deployment succeeds, open `https://YOUR-SERVICE.onrender.com/health`. It should return JSON with `"ok":true`.
5. In the installed mod, edit `mods/DropkickCNE_Mod/data/global.hx` and set `dropkickOnlineServer` to that URL, including `https://` and omitting a final slash.
6. Restart Codename Engine. Every person who hosts or joins must use a mod configured with the same relay URL.

Render's Blueprint format allows a `render.yaml` at a repository root and a service `rootDir` for the application subdirectory; the included config uses that layout. See the official references: https://render.com/docs/blueprint-spec and https://render.com/docs/web-services.

## Local smoke test

From the relay repo root:

```sh
cd server
npm start
```

Then visit `http://localhost:3000/health`.

## Behavior / limits

- Rooms are held in memory and expire after 35 minutes without activity.
- Restarting or sleeping/redeploying the service clears active rooms; players then create a new code.
- The host simulates physics and sends snapshots; the guest sends input flags. The current relay is intentionally lightweight and does not include matchmaking, user accounts, or anti-cheat.
- Never publish a room token; the game manages it locally. Share the six-character room code only with the intended guest.
