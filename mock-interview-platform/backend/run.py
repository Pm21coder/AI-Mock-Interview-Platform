from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    # Flask-SocketIO 5.5+ refuses to start Werkzeug unless this is explicit.
    # Without it the backend exits immediately and the Next.js rewrite exposes
    # the failure as a 500 response in the frontend.
    socketio.run(
        app,
        # Keep one stable local process. Socket.IO's debug reloader can leave
        # multiple processes bound to port 5000, producing intermittent proxy
        # connection resets after code changes.
        debug=False,
        host='0.0.0.0',
        port=5000,
        allow_unsafe_werkzeug=True,
        # The reloader launches a second process, which doubles the startup
        # delay when the optional MongoDB SRV host cannot be resolved.
        use_reloader=False,
    )
