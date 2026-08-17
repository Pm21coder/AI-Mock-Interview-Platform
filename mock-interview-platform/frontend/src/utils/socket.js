import { io } from 'socket.io-client';

let socket = null;

/**
 * Get a singleton Socket.IO client connection.
 * The connection is authenticated with the user's JWT token so the
 * backend can route dashboard updates to the correct user room.
 */
export function getSocket() {
  if (socket) return socket;

  const token = typeof window !== 'undefined' ? window.localStorage.getItem('auth_token') : null;

  // Connect through the Next.js proxy to avoid CORS issues. The proxy in
  // next.config.js forwards /socket.io/* to the backend.
  const socketUrl = window.location.origin;

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
