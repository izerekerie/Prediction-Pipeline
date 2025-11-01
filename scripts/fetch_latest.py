"""scripts/fetch_latest.py

Simple helper to fetch the latest entry from the API for a given resource
(default: services-weekly). It prefers the list endpoint (assumes the API
returns items ordered by id DESC), falls back to a few common endpoints, and
prints the JSON of the latest record.

Usage (PowerShell):
    $env:API_BASE_URL = 'http://localhost:8000'
    python ./scripts/fetch_latest.py --resource services-weekly

"""
from __future__ import annotations
import os
import argparse
from typing import Optional

import requests
from dotenv import load_dotenv


load_dotenv()


def try_get(url: str, timeout: int = 10) -> Optional[requests.Response]:
    try:
        r = requests.get(url, timeout=timeout)
        return r
    except requests.RequestException as e:
        print(f"Request to {url} failed: {e}")
        return None


def fetch_latest(api_base: str, resource: str):
    """Try list endpoint first, then a few fallbacks to find latest record."""
    api_base = api_base.rstrip("/")
    candidates = [
        f"{api_base}/{resource}",
        f"{api_base}/{resource}/latest",
        f"{api_base}/{resource}/last",
        f"{api_base}/{resource}/1",
        f"{api_base}/{resource}/0",
    ]

    for url in candidates:
        print(f"Trying {url} ...")
        r = try_get(url)
        if not r:
            continue
        if r.status_code != 200:
            print(f"Received {r.status_code} from {url}: {r.text}")
            continue

        try:
            data = r.json()
        except Exception as e:
            print(f"Failed to parse JSON from {url}: {e}")
            continue

        # If list, take first element as latest
        if isinstance(data, list):
            if not data:
                print("No records returned in list.")
                return None
            latest = data[0]
            print("Latest record (from list endpoint):")
            print(latest)
            return latest

        # If object, assume it's the latest single record
        if isinstance(data, dict):
            print("Latest record (single object):")
            print(data)
            return data

    print("Could not fetch latest record. Check API and resource path.")
    return None


def fetch_all(api_base: str, resource: str):
    """Fetch entire resource (list endpoint) and return as Python list."""
    api_base = api_base.rstrip("/")
    url = f"{api_base}/{resource}"
    r = try_get(url)
    if not r:
        return None
    if r.status_code != 200:
        print(f"Received {r.status_code} from {url}: {r.text}")
        return None
    try:
        data = r.json()
    except Exception as e:
        print(f"Failed to parse JSON from {url}: {e}")
        return None
    if not isinstance(data, list):
        print("Expected a list from the resource endpoint but got a single object.")
        return None
    return data


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Fetch latest or all records from API resource",
    )
    parser.add_argument(
        "--api-base",
        default=os.environ.get("API_BASE_URL", "http://localhost:8000"),
        help="API base URL",
    )
    parser.add_argument(
        "--resource",
        default="services-weekly",
        help="Resource path (e.g. services-weekly or patients)",
    )
    parser.add_argument(
        "--mode",
        choices=("latest", "all"),
        default="latest",
        help="Fetch mode: latest or all",
    )
    parser.add_argument(
        "--out",
        help="Optional output file. If provided and format is csv, will write CSV",
    )
    parser.add_argument(
        "--format",
        choices=("json", "csv"),
        default="json",
        help="Output format when --out is provided",
    )

    args = parser.parse_args(argv)

    if args.mode == "latest":
        record = fetch_latest(args.api_base, args.resource)
        if record and args.out:
            # write single object to file as json
            import json

            with open(args.out, "w", encoding="utf8") as fh:
                json.dump(record, fh, ensure_ascii=False, indent=2)
            print(f"Wrote latest record to {args.out}")
    else:
        rows = fetch_all(args.api_base, args.resource)
        if rows is None:
            return
        if args.out:
            if args.format == "json":
                import json

                with open(args.out, "w", encoding="utf8") as fh:
                    json.dump(rows, fh, ensure_ascii=False, indent=2)
                print(f"Wrote {len(rows)} records to {args.out}")
            else:
                # write CSV using pandas if available
                try:
                    import pandas as pd

                    df = pd.DataFrame(rows)
                    df.to_csv(args.out, index=False)
                    print(f"Wrote {len(rows)} records to {args.out} (CSV)")
                except Exception as e:
                    print("Failed to write CSV. Install pandas or choose json:", e)
        else:
            print(f"Fetched {len(rows)} records")


if __name__ == "__main__":
    main()
