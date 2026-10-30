"""Start the DAP viewer: uv run main.py DAP-0103169.txt"""

import argparse

from dap_viz.app import app_from_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualise a JET DAP key/value file.")
    parser.add_argument("path", nargs="?", default="DAP-0103169.txt", help="DAP file")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8050)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    app = app_from_file(args.path)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
