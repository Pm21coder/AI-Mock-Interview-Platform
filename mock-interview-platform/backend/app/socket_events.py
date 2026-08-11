"""Socket.IO event handlers for real-time dashboard updates.

When an interview completes, the backend emits a `dashboard_update` event
to the user's personal room. The dashboard page subscribes to this event
and refreshes its data immediately, eliminating the need to wait for the
30-second polling interval.
"""
from flask import request
from flask_socketio import join_room, emit

from app import socketio

# Room name prefix for per-user dashboard updates.
USER_ROOM_PREFIX = 'user_'


def user_room(user_id):
    """Return the Socket.IO room name for a given user id."""
    return f'{USER_ROOM_PREFIX}{user_id}'


def register_socket_handlers():
    """Register Socket.IO connection and room-join handlers."""

    @socketio.on('connect')
    def handle_connect():
        """Authenticate the socket connection and join the user's room."""
        try:
            token = request.args.get('token')
            if not token:
                # Allow connection but don't join any room (guest mode).
                return

            from app.utils.auth import get_user_id_from_token
            user_id = get_user_id_from_token(token)
            if user_id:
                join_room(user_room(user_id))
                emit('connected', {'user_id': user_id})
        except Exception as exc:
            print(f'Socket connect error: {exc}')
            # Never reject the connection; just don't join a room.
            return

    @socketio.on('join_dashboard')
    def handle_join_dashboard(data):
        """Explicitly join the dashboard room for the authenticated user."""
        token = (data or {}).get('token')
        if not token:
            return

        from app.utils.auth import get_user_id_from_token
        user_id = get_user_id_from_token(token)
        if user_id:
            join_room(user_room(user_id))
            emit('dashboard_joined', {'user_id': user_id})


def emit_dashboard_update(user_id, stats):
    """Emit a dashboard update event to a specific user's room.

    Args:
        user_id: The string user id.
        stats: A dict with the updated dashboard stats payload.
    """
    socketio.emit(
        'dashboard_update',
        {'stats': stats},
        room=user_room(user_id),
    )