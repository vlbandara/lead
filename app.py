"""
Simple web app: upload a CSV with website URLs, get back an enriched CSV
with Email, Phone, and AI Summary. Designed to run on Render.com free tier.
"""
import csv
import io
import os
import re
from typing import Optional
from urllib.parse import urlparse

from flask import Flask, request, render_template, Response

# Import after Flask so we can set env before scraper loads if needed
from contact_info_scraper import gather_contact_info, clean_url

# Resolve template folder relative to this file so it works when cwd differs (e.g. on Render)
_this_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(_this_dir, "templates"))
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB max upload

# Keep request within Render free tier timeout; each URL can take 15–30+ seconds
MAX_URLS_PER_REQUEST = 5

URL_COLUMN_NAMES = ("website", "url", "site", "domain", "link", "website_url")


def _normalize_url(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    if not urlparse(s).scheme:
        return "https://" + s
    return s


def _is_valid_url(s: str) -> bool:
    return bool(re.match(r"https?://[^\s/$.?#].[^\s]*", s))


def _detect_url_column(headers: list) -> int:
    """Return index of URL column, or 0 if not found."""
    for i, h in enumerate(headers):
        if (h or "").strip().lower() in URL_COLUMN_NAMES:
            return i
    return 0


def _enrich_row(row: list, url_index: int, contact: Optional[dict]) -> list:
    """Append Email, Phone, AI Summary to row. contact can be None on failure."""
    out = list(row)
    if contact:
        out.append(", ".join(contact.get("Email") or []) or "")
        out.append(", ".join(contact.get("Phone") or []) or "")
        out.append((contact.get("AI Summary") or "").strip())
    else:
        out.extend(["", "", ""])
    return out


@app.route("/")
def index():
    return render_template("index.html", max_urls=MAX_URLS_PER_REQUEST)


@app.route("/enrich", methods=["POST"])
def enrich():
    if "csv" not in request.files:
        return {"error": "No CSV file uploaded"}, 400
    f = request.files["csv"]
    if not f.filename or not f.filename.lower().endswith((".csv", ".txt")):
        return {"error": "Please upload a CSV file"}, 400

    try:
        stream = io.StringIO(f.stream.read().decode("utf-8", errors="replace"))
        reader = csv.reader(stream)
        rows = list(reader)
    except Exception as e:
        return {"error": f"Invalid CSV: {e}"}, 400

    if not rows:
        return {"error": "CSV file is empty"}, 400

    headers = rows[0]
    url_index = _detect_url_column(headers)
    new_headers = headers + ["Email", "Phone", "AI Summary"]

    # Collect URLs from first column or detected column (skip header)
    urls = []
    for r in rows[1:]:
        if len(r) > url_index:
            u = _normalize_url(r[url_index])
            if u and _is_valid_url(u):
                urls.append(u)

    if not urls:
        return {"error": "No valid website URLs found in the CSV. Use a column named 'website' or 'url', or put URLs in the first column."}, 400

    if len(urls) > MAX_URLS_PER_REQUEST:
        return {
            "error": f"Too many URLs ({len(urls)}). Maximum is {MAX_URLS_PER_REQUEST} per file on free tier.",
        }, 400

    # Enrich each URL (sequential to stay within timeout and rate limits)
    url_to_contact = {}
    for u in urls:
        contact = gather_contact_info(u)
        url_to_contact[clean_url(u)] = contact
        url_to_contact[u] = contact
        if contact and contact.get("Website"):
            url_to_contact[contact["Website"]] = contact

    # Build output CSV: original rows + enriched columns
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(new_headers)

    for r in rows[1:]:
        if len(r) <= url_index:
            writer.writerow(_enrich_row(r, url_index, None))
            continue
        u = _normalize_url(r[url_index])
        if not u or not _is_valid_url(u):
            writer.writerow(_enrich_row(r, url_index, None))
            continue
        contact = url_to_contact.get(clean_url(u)) or url_to_contact.get(u)
        writer.writerow(_enrich_row(r, url_index, contact))

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=enriched_contacts.csv"},
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(__import__("os").environ.get("PORT", 5001)))
