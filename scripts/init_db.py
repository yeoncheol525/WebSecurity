"""Initialize sample data, or explicitly reset it with --reset."""

import argparse

from minishop import create_app
from minishop.db import init_db


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the MiniShop SQLite database")
    parser.add_argument("--reset", action="store_true", help="Replace existing data with the initial sample data")
    args = parser.parse_args()
    app = create_app()
    if args.reset:
        with app.app_context():
            init_db(reset=True)
        print("Sample data reset.")
    else:
        print("Database ready. Existing data preserved.")
