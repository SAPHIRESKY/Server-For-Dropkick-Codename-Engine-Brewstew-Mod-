# Dropkick Room-Code Relay (Railway TCP)

This is the raw TCP relay for the current Codename Engine Dropkick client that uses `sys.net.Socket` and newline-delimited JSON. It is added in its own folder so it does not replace the existing Node/HTTP relay at the repository root.

## Deploy on Railway

1. In Railway, create a new project from this GitHub repository.
2. In the service settings, set **Root Directory** to `/railway-tcp-relay`.
3. Deploy the service using its Dockerfile.
4. In the service's Variables, set `PORT=27666`.
5. In **Settings → Networking**, create a **TCP Proxy** for internal port `27666`. Railway will show the public hostname and public proxy port.
6. Keep the relay at one replica. Room codes are stored in memory and are not shared across replicas.
7. On both players' game installations, edit `mods/Dropkick/data/global.hx`:
   - Set `dropkickRoomServerHost` to the exact public TCP proxy hostname.
   - Set `dropkickRoomServerPort` to the exact public TCP proxy port.
   - Do not include `tcp://`, `http://`, or `https://` in the hostname.
8. Restart both games. The host creates a six-character code; the guest enters that code. Neither player needs to run the server or forward ports on their home router.

## Verify and troubleshoot

- Startup log: `Dropkick room-code relay listening on 0.0.0.0:27666/TCP`.
- Host creation: `Received create handshake`, then `Room CODE created`.
- Guest join: `Received join handshake`, then `Room CODE paired successfully`.
- If a room fails to create/join, check that both clients have the same Railway public TCP hostname and port and that the service is deployed.
- Restarting/redeploying clears active rooms; create a new room after restart.

## Security and limitations

- The relay stores room assignments in memory and has no account system. Room codes should be shared only with the intended friend.
- This server relays gameplay packets; it does not host the game's simulation itself.
- Review Railway's current plan, usage limits, and costs before deploying.
- No account credentials or API tokens are included in this folder.
