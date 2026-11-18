"""Helper functions used to scrape shops"""
import json, time, requests
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

HEADERS = {
    ""
}