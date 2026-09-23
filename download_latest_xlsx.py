"""Download the Akoakoa restoration spreadsheet from Dropbox into Updates/YYYYMMDD/."""

import os
import sys
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
XLSX_NAME = "Akoakoa_Restoration_Activities.xlsx"


def download_xlsx(url: str) -> Path:
    datestr = date.today().strftime("%Y%m%d")
    loc_path = ROOT / "Updates" / datestr
    loc_path.mkdir(parents=True, exist_ok=True)
    dest = loc_path / XLSX_NAME.replace(".xlsx", f"_{datestr}.xlsx")
    if not os.path.exists(dest):
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        if "html" in resp.headers.get("content-type", ""):
            raise RuntimeError(
                "Got HTML instead of a spreadsheet; check the link ends in dl=1"
            )
        try:
            nbytes = len(resp.content)
            dest.write_bytes(resp.content)
        except Exception as exc:
            raise RuntimeError(f"Could not write {nbytes} bytes to {dest}: {exc}")
    print(dest)
    return dest


if __name__ == "__main__":
    url = os.environ.get("DROPBOX_XLSX_URL")
    if not url:
        sys.exit("Set DROPBOX_XLSX_URL to the Dropbox share link (dl=1)")
    download_xlsx(url)
