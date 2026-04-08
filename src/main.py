import argparse
import json

from pipeline import run_daily, run_weekly


def main() -> None:
    parser = argparse.ArgumentParser(description="LinkedIn content automation")
    parser.add_argument("--mode", choices=["daily", "weekly"], required=True)
    args = parser.parse_args()

    if args.mode == "daily":
        result = run_daily()
    else:
        result = run_weekly()

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
