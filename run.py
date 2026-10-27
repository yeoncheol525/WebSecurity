import argparse

from minishop import create_app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MiniShop development server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    create_app().run(host=args.host, port=args.port, debug=False, use_reloader=False)
