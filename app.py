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

from flask import Flask, request, render_template, Response, jsonify

# Import after Flask so we can set env before scraper loads if needed
from contact_info_scraper import gather_contact_info, clean_url, OPENROUTER_API_KEY

# Resolve template folder relative to this file so it works when cwd differs (e.g. on Render)
_this_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(_this_dir, "templates"))
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB max upload

# Max URLs per request (free tier may timeout with many URLs; use 1–3 for reliability)
MAX_URLS_PER_REQUEST = 10

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


def _collect_urls_from_request():
    """Return (urls, extra_rows) from either CSV file or 'urls' form field. extra_rows is list of (url, [extra_cols]) for CSV."""
    urls_text = (request.form.get("urls") or "").strip()
    if urls_text:
        urls = []
        for line in urls_text.splitlines():
            u = _normalize_url(line)
            if u and _is_valid_url(u):
                urls.append(u)
        return urls, [(u, []) for u in urls]

    f = request.files.get("csv")
    if not f or not f.filename or not f.filename.lower().endswith((".csv", ".txt")):
        return None, None

    try:
        stream = io.StringIO(f.stream.read().decode("utf-8", errors="replace"))
        reader = csv.reader(stream)
        rows = list(reader)
    except Exception as e:
        raise ValueError(f"Invalid CSV: {e}")

    if not rows:
        raise ValueError("CSV file is empty")

    headers = rows[0]
    url_index = _detect_url_column(headers)
    urls = []
    extra_rows = []
    for r in rows[1:]:
        if len(r) > url_index:
            u = _normalize_url(r[url_index])
            if u and _is_valid_url(u):
                urls.append(u)
                extra_cols = [c for i, c in enumerate(r) if i != url_index]
                extra_rows.append((u, extra_cols))
    return urls, extra_rows


@app.route("/enrich", methods=["POST"])
def enrich():
    try:
        urls, extra_rows = _collect_urls_from_request()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if urls is None:
        return jsonify({"error": "Add website URLs in the text box, or upload a CSV file."}), 400

    if not urls:
        return jsonify({
            "error": "No valid website URLs found. Enter one URL per line, or use a CSV with a 'website' or 'url' column.",
        }), 400

    if len(urls) > MAX_URLS_PER_REQUEST:
        return jsonify({
            "error": f"Too many URLs ({len(urls)}). Maximum is {MAX_URLS_PER_REQUEST} per request.",
        }), 400

    if not (OPENROUTER_API_KEY or "").strip():
        return jsonify({
            "error": "OpenRouter API key is not set. Add OPENROUTER_API_KEY in Render Environment (or in .env locally).",
        }), 500

    try:
        url_to_contact = {}
        for u in urls:
            contact = gather_contact_info(u)
            url_to_contact[clean_url(u)] = contact
            url_to_contact[u] = contact
            if contact and contact.get("Website"):
                url_to_contact[contact["Website"]] = contact

        results = []
        for i, u in enumerate(urls):
            contact = url_to_contact.get(clean_url(u)) or url_to_contact.get(u)
            row = {
                "website": u,
                "email": ", ".join(contact.get("Email") or []) if contact else "",
                "phone": ", ".join(contact.get("Phone") or []) if contact else "",
                "ai_summary": (contact.get("AI Summary") or "").strip() if contact else "",
            }
            if extra_rows and i < len(extra_rows):
                row["_extra"] = extra_rows[i][1]
            results.append(row)

        return jsonify({"results": results})
    except Exception as e:
        return jsonify({
            "error": f"Enrichment failed: {str(e)}",
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(__import__("os").environ.get("PORT", 5001)))
