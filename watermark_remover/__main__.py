import argparse

from .web.server import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local PDF watermark remover")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    parser.add_argument("--port", default=8765, type=int, help="HTTP port (default: 8765)")
    args = parser.parse_args()
    run(args.host, args.port)


if __name__ == "__main__":
    main()
