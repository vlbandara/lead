"""
Contact Enricher web app.
- /enrich      POST  multipart CSV  → download enriched CSV
- /enrich-urls POST  JSON {urls:[]} → JSON results for in-UI table
"""
import csv
import io
import os
import re
from typing import Optional
from urllib.parse import urlparse

from flask import Flask, request, render_template, Response, jsonify

from contact_info_scraper import gather_contact_info, clean_url, OPENROUTER_API_KEY

_this_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(_this_dir, "templates"))
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB max upload

MAX_URLS_PER_REQUEST = 3  # gunicorn --timeout 120 handles ~3 URLs comfortably

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
    for i, h in enumerate(headers):
        if (h or "").strip().lower() in URL_COLUMN_NAMES:
            return i
    return 0


def _enrich_row(row: list, url_index: int, contact: Optional[dict]) -> list:
    out = list(row)
    if contact:
        out.append(", ".join(contact.get("Email") or []) or "")
        out.append(", ".join(contact.get("Phone") or []) or "")
        out.append((contact.get("AI Summary") or "").strip())
    else:
        out.extend(["", "", ""])
    return out


def _check_api_key():
    if not (OPENROUTER_API_KEY or "").strip():
        return jsonify({
            "error": "OpenRouter API key is not set. Add OPENROUTER_API_KEY in Render Environment.",
        }), 500
    return None


def _run_enrichment(urls: list) -> dict:
    """Run gather_contact_info for each URL and return a lookup dict."""
    url_to_contact = {}
    for u in urls:
        contact = gather_contact_info(u)
        url_to_contact[clean_url(u)] = contact
        url_to_contact[u] = contact
        if contact and contact.get("Website"):
            url_to_contact[contact["Website"]] = contact
    return url_to_contact


@app.route("/")
def index():
    return render_template("index.html", max_urls=MAX_URLS_PER_REQUEST)


# ── Text / textarea endpoint → returns JSON for in-UI table ──────────────────

@app.route("/enrich-urls", methods=["POST"])
def enrich_urls():
    err = _check_api_key()
    if err:
        return err

    body = request.get_json(silent=True) or {}
    raw_urls = body.get("urls") or []

    if isinstance(raw_urls, str):
        raw_urls = [line.strip() for line in raw_urls.splitlines() if line.strip()]

    urls = []
    for u in raw_urls:
        n = _normalize_url(u)
        if n and _is_valid_url(n) and n not in urls:
            urls.append(n)

    if not urls:
        return jsonify({"error": "No valid URLs provided."}), 400

    if len(urls) > MAX_URLS_PER_REQUEST:
        return jsonify({
            "error": f"Too many URLs ({len(urls)}). Max is {MAX_URLS_PER_REQUEST} per request.",
        }), 400

    try:
        url_to_contact = _run_enrichment(urls)
        results = []
        for u in urls:
            contact = url_to_contact.get(clean_url(u)) or url_to_contact.get(u) or {}
            results.append({
                "website": contact.get("Website") or u,
                "email":   ", ".join(contact.get("Email") or []),
                "phone":   ", ".join(contact.get("Phone") or []),
                "summary": (contact.get("AI Summary") or "").strip(),
            })
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": f"Enrichment failed: {e}"}), 500


# ── CSV upload endpoint → returns enriched CSV download ─────────────────────

@app.route("/enrich", methods=["POST"])
def enrich():
    err = _check_api_key()
    if err:
        return err

    if "csv" not in request.files:
        return jsonify({"error": "No CSV file uploaded"}), 400
    f = request.files["csv"]
    if not f.filename or not f.filename.lower().endswith((".csv", ".txt")):
        return jsonify({"error": "Please upload a CSV file"}), 400

    try:
        stream = io.StringIO(f.stream.read().decode("utf-8", errors="replace"))
        rows = list(csv.reader(stream))
    except Exception as e:
        return jsonify({"error": f"Invalid CSV: {e}"}), 400

    if not rows:
        return jsonify({"error": "CSV file is empty"}), 400

    headers = rows[0]
    url_index = _detect_url_column(headers)
    new_headers = headers + ["Email", "Phone", "AI Summary"]

    urls = []
    for r in rows[1:]:
        if len(r) > url_index:
            u = _normalize_url(r[url_index])
            if u and _is_valid_url(u) and u not in urls:
                urls.append(u)

    if not urls:
        return jsonify({"error": "No valid website URLs found. Use a column named 'website' or 'url'."}), 400

    if len(urls) > MAX_URLS_PER_REQUEST:
        return jsonify({
            "error": f"Too many URLs ({len(urls)}). Max is {MAX_URLS_PER_REQUEST} per file.",
        }), 400

    try:
        url_to_contact = _run_enrichment(urls)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(new_headers)
        for r in rows[1:]:
            u = _normalize_url(r[url_index]) if len(r) > url_index else ""
            contact = (url_to_contact.get(clean_url(u)) or url_to_contact.get(u)) if u and _is_valid_url(u) else None
            writer.writerow(_enrich_row(r, url_index, contact))

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=enriched_contacts.csv"},
        )
    except Exception as e:
        return jsonify({"error": f"Enrichment failed: {e}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
