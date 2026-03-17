```markdown
# ContactInfoScraper

## Overview

ContactInfoScraper is a Python script designed to extract email and phone numbers from given web pages and output the data into an Excel file (contacts.xlsx). It also logs all events and outputs them into a log.txt file.

## Features

- Extracts email and phone numbers from websites.
- Retrieves contact information from social media pages like Facebook.
- Enhanced logging with timestamps for tracking each step of the process.
- Readable output in Command Prompt windows of all sizes.
- User-friendly batch file (OpenCmdHere.bat) for opening the CMD in the correct folder (for Windows).

## How It Works

1. **Setup and Configuration**: The script initializes logging for monitoring its activity, and sets up necessary imports for web scraping and data handling.

2. **Data Collection**:

   - **URL Input**: Users can input multiple URLs directly, which will be validated before processing.
   - **Contact Information Gathering**: For each URL, the script fetches the main webpage, extracts emails and phone numbers, and searches for additional contact links.
   - **Social Media and Google Search**: If phone numbers are not found, it checks the associated Facebook page and uses Google Maps and Yelp for further data extraction.

3. **Output**:
   - The collected contact information is saved into a CSV file and formatted into an Excel file with appropriate styling for easy readability.

## Requirements

- Python 3.x
- Libraries: see `requirements.txt` (`requests`, `beautifulsoup4`, `lxml`, `openpyxl`, `googlesearch-python`, `python-dotenv`)
```

## Usage

1. Clone or download the repository.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your OpenRouter API key (get one at https://openrouter.ai):

```bash
cp .env.example .env
# Edit .env and set OPENROUTER_API_KEY=your_key_here
```

4. Run the scraper:

   - **Batch mode**: Put URLs in `web_urls.txt` (one per line), then run:

   ```bash
   python contact_info_scraper.py
   ```

   - **Interactive mode**: Prompt for URLs and append them to the file:

   ```bash
   python contact_info_scraper.py -i
   ```

   - **CLI options**:
     - `-f, --file FILE` — URL list file (default: `web_urls.txt`)
     - `-o, --output FILE` — Output Excel path (default: `contacts.xlsx`)
     - `-i, --interactive` — Also prompt for URLs; new URLs are appended to the file
     - `-w, --workers N` — Concurrent workers (default: 3; use 1 for sequential)

   The script will output progress to the console, log to `log.txt`, and save results to the chosen Excel file.

## Example of URL Input

```
Enter a URL (or "n" to start scraping): https://example.com
  Added: https://example.com

Enter a URL (or "n" to start scraping): n
```

## Sample Output

The script will display the contact information in the terminal:

```
Contact Info:
Website: https://example.com
Emails: contact@example.com
Phones: +1-234-567-8901
```

The output will also be saved in `contacts.xlsx` with columns for Website, Email, and Phone.

## Logging

A detailed log of the entire process, including errors and timestamps, is written to log.txt. Timestamps are displayed both in the Command Prompt and in the log file.

## Web app (drop CSV → download enriched CSV)

A simple web UI lets you upload a CSV of website URLs and download the same CSV with **Email**, **Phone**, and **AI Summary** columns added.

### Run locally

```bash
pip install -r requirements.txt
# Set OPENROUTER_API_KEY in .env
python app.py
```

Open http://localhost:5001 — drop a CSV or choose a file, then click **Enrich & download**. Your CSV should have a column named `website` or `url`, or URLs in the first column.

### Deploy on Render (free)

1. Push this repo to GitHub and connect it to [Render](https://render.com).
2. Create a **Web Service**, connect the repo, and use:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn --bind 0.0.0.0:$PORT --timeout 120 app:app`
3. In the service **Environment** tab, add:
   - **Key:** `OPENROUTER_API_KEY`  
   - **Value:** your OpenRouter API key (from https://openrouter.ai)
4. Deploy. Free tier allows a limited number of URLs per request (e.g. 5) to stay within request timeouts.

Alternatively, use the included `render.yaml` (Blueprint) and add `OPENROUTER_API_KEY` in the Render dashboard after the service is created.

### When sites block scraping (403 Forbidden)

Some sites block plain HTTP requests and return **403 Forbidden**. You can enable a **browser fallback** so that when a URL returns 403 (or 401/405/429), the scraper tries again using a headless Chromium browser (Playwright), which often succeeds because it looks like a real browser.

1. Install Playwright and its browser:
   ```bash
   pip install playwright
   playwright install chromium
   ```
2. Enable the fallback via environment variable:
   ```bash
   export USE_BROWSER_FALLBACK=1
   ```
   Or in `.env`: `USE_BROWSER_FALLBACK=1`
3. If Playwright is not installed, the scraper still works; it simply skips the browser fallback and continues to fail on blocked URLs.

**Note:** Browser fallback is not available on Render’s free tier (installing Chromium in the build requires root and fails). Use it when running locally or on a VPS/Docker where you can run `playwright install chromium`.

## Notes

- If you are using Windows, you can execute the ''OpenCmdHere.bat'' so you can run all the commands from there.
- Adjust the rate limiting (`time.sleep(1)`) as necessary based on your testing needs and the target website's policies.

## Contributions

Feel free to fork the repository and submit pull requests for any enhancements or bug fixes. Feedback and contributions are welcome!

## License

This project is licensed under the GNU GPL v3. See the [LICENSE](LICENSE) file for details.
