'use strict';

// Small HTTP relay for Dropkick room codes. The host is authoritative for the
// physics; the guest sends input and receives the host's latest snapshot.
// Rooms intentionally live in memory (no account system or personal data).
const http = require('http');
const crypto = require('crypto');

const PORT = Number(process.env.PORT || 3000);
const rooms = new Map();
const CODE_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
const VALID_CHARACTERS = new Set(['HeartBrewer', 'Tomahawk']);
const MAX_BODY = 128 * 1024;
const ROOM_IDLE_MS = 35 * 60 * 1000;

function randomToken(bytes = 24) { return crypto.randomBytes(bytes).toString('hex'); }
function makeCode() {
  let code;
  do {
    const bytes = crypto.randomBytes(6);
    code = Array.from(bytes, b => CODE_CHARS[b % CODE_CHARS.length]).join('');
  } while (rooms.has(code));
  return code;
}
function characterOrDefault(value, fallback) { return VALID_CHARACTERS.has(value) ? value : fallback; }
function readBody(req) {
  return new Promise((resolve, reject) => {
    let raw = '';
    req.setEncoding('utf8');
    req.on('data', chunk => {
      raw += chunk;
      if (raw.length > MAX_BODY) {
        reject(Object.assign(new Error('Request body too large.'), { status: 413 }));
        req.destroy();
      }
    });
    req.on('end', () => {
      if (!raw) return resolve({});
      try { resolve(JSON.parse(raw)); }
      catch { reject(Object.assign(new Error('Invalid JSON.'), { status: 400 })); }
    });
    req.on('error', reject);
  });
}
function json(res, status, value) {
  const body = JSON.stringify(value);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
    'Cache-Control': 'no-store',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
  });
  res.end(body);
}
function roomSummary(room) {
  return {
    code: room.code,
    status: room.started ? 'started' : (room.players.guest ? 'ready' : 'waiting'),
    background: 'Backyard',
    players: {
      host: room.players.host,
      guest: room.players.guest
    },
    hostConnected: Date.now() - room.hostSeen < 8000,
    guestConnected: !!room.players.guest && Date.now() - room.guestSeen < 8000
  };
}
function tokenRole(room, token) {
  if (token && token === room.tokens.host) return 'host';
  if (token && token === room.tokens.guest && room.players.guest) return 'guest';
  return null;
}
function cleanInput(input) {
  input = input && typeof input === 'object' ? input : {};
  return { left: !!input.left, right: !!input.right, jump: !!input.jump, kick: !!input.kick };
}
function notFound(res) { json(res, 404, { ok: false, message: 'Room or endpoint not found.' }); }
function roomError(res, code, message) { json(res, code, { ok: false, message }); }

const server = http.createServer(async (req, res) => {
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    });
    return res.end();
  }
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  if (req.method === 'GET' && url.pathname === '/health') return json(res, 200, { ok: true, service: 'dropkick-worldwide-relay' });
  if (req.method !== 'POST') return notFound(res);

  let body;
  try { body = await readBody(req); }
  catch (err) { return roomError(res, err.status || 400, err.message || 'Could not read request.'); }

  if (url.pathname === '/api/rooms') {
    const code = makeCode();
    const now = Date.now();
    const room = {
      code,
      tokens: { host: randomToken(), guest: null },
      players: {
        host: { character: characterOrDefault(body.character, 'HeartBrewer'), background: 'Backyard' },
        guest: null
      },
      started: false,
      state: null,
      guestInput: { left: false, right: false, jump: false, kick: false },
      createdAt: now,
      lastActivity: now,
      hostSeen: now,
      guestSeen: 0
    };
    rooms.set(code, room);
    return json(res, 201, { ok: true, code, token: room.tokens.host, room: roomSummary(room) });
  }

  const joinMatch = url.pathname.match(/^\/api\/rooms\/([A-Z0-9]{6})\/join$/i);
  if (joinMatch) {
    const room = rooms.get(joinMatch[1].toUpperCase());
    if (!room) return roomError(res, 404, 'That room code was not found.');
    if (room.started) return roomError(res, 409, 'That match has already started.');
    if (room.players.guest) return roomError(res, 409, 'That room already has two players.');
    room.tokens.guest = randomToken();
    room.players.guest = { character: characterOrDefault(body.character, 'Tomahawk'), background: 'Backyard' };
    room.guestSeen = Date.now(); room.lastActivity = Date.now();
    return json(res, 200, { ok: true, code: room.code, token: room.tokens.guest, room: roomSummary(room) });
  }

  const match = url.pathname.match(/^\/api\/rooms\/([A-Z0-9]{6})\/(lobby|game|leave)$/i);
  if (!match) return notFound(res);
  const room = rooms.get(match[1].toUpperCase());
  if (!room) return roomError(res, 404, 'That room no longer exists.');
  const role = tokenRole(room, body.token);
  if (!role) return roomError(res, 403, 'Invalid room token. Rejoin the room from its current code.');
  const now = Date.now();
  room.lastActivity = now;
  if (role === 'host') room.hostSeen = now; else room.guestSeen = now;

  if (match[2] === 'leave') {
    if (role === 'host') rooms.delete(room.code);
    else {
      room.players.guest = null;
      room.tokens.guest = null;
      room.guestInput = { left: false, right: false, jump: false, kick: false };
      room.guestSeen = 0;
      room.started = false;
      room.state = null;
    }
    return json(res, 200, { ok: true, left: true });
  }

  if (match[2] === 'lobby') {
    if (room.started && body.start !== true) return json(res, 200, { ok: true, room: roomSummary(room) });
    room.players[role].character = characterOrDefault(body.character, room.players[role].character || (role === 'host' ? 'HeartBrewer' : 'Tomahawk'));
    // Backyard is deliberately the only background available right now.
    room.players[role].background = 'Backyard';
    if (body.start === true) {
      if (role !== 'host') return roomError(res, 403, 'Only the host can start the match.');
      if (!room.players.guest) return roomError(res, 409, 'Wait for a second player before starting.');
      room.started = true;
      room.state = null;
      room.guestInput = { left: false, right: false, jump: false, kick: false };
    }
    return json(res, 200, { ok: true, room: roomSummary(room) });
  }

  // Host publishes authoritative physics; guest publishes only its four input
  // flags. Each poll returns the opposite side's latest data in the same call.
  if (!room.started) return roomError(res, 409, 'The host has not started the match yet.');
  if (role === 'host') {
    if (body.state && typeof body.state === 'object') room.state = body.state;
  } else {
    room.guestInput = cleanInput(body.input);
  }
  return json(res, 200, {
    ok: true,
    role,
    started: room.started,
    state: room.state,
    input: room.guestInput,
    room: roomSummary(room)
  });
});

setInterval(() => {
  const now = Date.now();
  for (const [code, room] of rooms) {
    if (now - room.lastActivity > ROOM_IDLE_MS) rooms.delete(code);
  }
}, 60_000).unref();

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Dropkick worldwide relay listening on port ${PORT}`);
});
