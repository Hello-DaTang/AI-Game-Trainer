"""Start the no-build local desktop dashboard: py -m trainer."""
import argparse
import threading
import webbrowser

from .service import TrainerService
from .web import serve


def main():
    parser = argparse.ArgumentParser(description="AI Game Trainer (local MVP)")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    server = serve(TrainerService(), args.port)
    if not args.no_browser:
        threading.Timer(
            0.5, lambda: webbrowser.open("http://127.0.0.1:" + str(server.server_port))
        ).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping AI Game Trainer...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
