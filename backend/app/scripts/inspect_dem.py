import argparse
import json

from app.services.terrain_service import inspect_dem


def main():
    parser = argparse.ArgumentParser(description="Inspect local DEM metadata without processing it")
    parser.add_argument("path")
    args = parser.parse_args()
    print(json.dumps(inspect_dem(args.path), indent=2))


if __name__ == "__main__":
    main()

