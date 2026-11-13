import argparse

from app.services.terrain_service import process_dem, write_summary


def main():
    parser = argparse.ArgumentParser(description="Process a projected metric DEM into a terrain feature summary")
    parser.add_argument("--input", required=True)
    parser.add_argument("--site-id", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    write_summary(process_dem(args.input, args.site_id), args.output)


if __name__ == "__main__":
    main()

