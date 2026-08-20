import { io } from 'socket.io-client';

let socket = null;

/**
 * Get a singleton Socket.IO client connection.
 * The connection is authenticated with the user's JWT token so the
 * backend can route dashboard updates to the correct user room.
 */
function getSocketBaseUrl() {
  if (typeof window === 'undefined') return '';

  const configured = (
    typeof process !== 'undefined' &&
    process.env &&
    typeof process.env.NEXT_PUBLIC_API_URL === 'string' &&
    process.env.NEXT_PUBLIC_API_URL.trim()
  ) ? process.env.NEXT_PUBLIC_API_URL.trim() : '';

  return configured ? configured.replace(/\/$/, '') : window.location.origin;
}

export function getSocket() {
  if (socket) return socket;

  const token = typeof window !== 'undefined' ? window.localStorage.getItem('auth_token') : null;

  // Prefer the configured backend origin when present so realtime dashboard
  // updates continue to work in non-proxied deployments. Otherwise, use the
  // current origin so local Next.js rewrites remain transparent.
  const socketUrl = getSocketBaseUrl();

  socket = io(socketUrl, {
    path: '/socket.io',
    transports: ['websocket', 'polling'],
    query: token ? { token } : {},
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
  });

  return socket;
}

/**
 * Disconnect the socket client (used on logout).
 */
export function disconnectSocket() {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
}

/**
 * Subscribe to a Socket.IO event.
 * Returns an unsubscribe function.
 */
export function onSocketEvent(event, handler) {
  const s = getSocket();
  s.on(event, handler);
  return () => s.off(event, handler);
}

/**
 * Emit a Socket.IO event.
 */
export function emitSocketEvent(event, data) {
  const s = getSocket();
  s.emit(event, data);
}
