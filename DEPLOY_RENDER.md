# Host the Contact Enricher on Render (free)

Follow these steps to get your CSV enricher live at a URL like `https://contact-enricher-xxxx.onrender.com`.

---

## 1. Put your code on GitHub

Render deploys from a Git repo. If the project isn’t on GitHub yet:

1. Create a new repo on [github.com](https://github.com/new) (e.g. `ContactInfoScraper`).
2. On your machine, in the project folder, run:

   ```bash
   cd /path/to/ContactInfoScraper-master
   git init
   git add .
   git commit -m "Initial commit - Contact Enricher web app"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git push -u origin main
   ```

   Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` with your GitHub username and repo name.

**Important:** Don’t commit `.env` or your real API key. The repo already has `.gitignore` with `.env` in it, so you’re safe as long as you never `git add .env`.

---

## 2. Create a Render account and connect GitHub

1. Go to **[render.com](https://render.com)** and sign up (or log in).
2. Click **Get started** or **Dashboard**.
3. Connect GitHub: **Account Settings → Connect account → GitHub**, and authorize Render for the repo(s) you want to use.

---

## 3. Create a new Web Service

1. In the Render dashboard, click **New +** → **Web Service**.
2. **Connect a repository:**
   - If you see a list of repos, select your `ContactInfoScraper` (or whatever you named it).
   - If not, click **Configure account** and grant access to that repo, then select it.
3. Click **Connect** next to the repo.

---

## 4. Configure the service

Use these settings (Render will guess some of them):

| Field | Value |
|--------|--------|
| **Name** | `contact-enricher` (or any name you like) |
| **Region** | Choose the one closest to you |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn --bind 0.0.0.0:$PORT --timeout 120 app:app` |

- **Instance type:** leave as **Free** (or pick Free explicitly if you see a plan selector).

Do **not** click **Create Web Service** yet. Add the API key first.

---

## 5. Add your OpenRouter API key

1. In the same “Create Web Service” page, find the **Environment** section (often under “Advanced” or a similar section).
2. Click **Add Environment Variable**.
3. Add:
   - **Key:** `OPENROUTER_API_KEY`
   - **Value:** your OpenRouter API key (from [openrouter.ai](https://openrouter.ai) → Keys).

4. If you don’t have a key yet:
   - Go to [openrouter.ai](https://openrouter.ai), sign in, open **Keys**, create a key, and copy it into the **Value** field.

---

## 6. Deploy

1. Click **Create Web Service**.
2. Render will clone the repo, run `pip install -r requirements.txt`, then start the app with gunicorn. The first deploy can take a few minutes.
3. When the build and deploy finish, the **Logs** tab will show something like “Your service is live at …”.
4. Your app URL will look like:  
   `https://contact-enricher-xxxx.onrender.com`  
   (the exact name depends on the service name you chose).

---

## 7. Use the app

1. Open the URL in your browser (e.g. `https://contact-enricher-xxxx.onrender.com`).
2. You should see the “Contact Enricher” page with the drop zone.
3. Upload a CSV that has a `website` or `url` column (or URLs in the first column), click **Enrich & download**, and wait. The enriched CSV will download when processing finishes.

**Free tier note:** The app is limited to **5 URLs per CSV** so requests don’t hit Render’s request timeout. For more URLs per run, you’d need a paid plan or to run the CLI locally.

---

## Troubleshooting

- **Build fails:** Check the **Logs** tab for errors. Often it’s a missing dependency in `requirements.txt` or a typo in Build/Start command.
- **“Application failed to respond” / 503:** The free instance may have spun down. Reload the page; the first request after idle can take 30–60 seconds to wake the service.
- **WORKER TIMEOUT / “Something went wrong” after upload:** The app is limited to **1 URL per CSV** on free tier so the request can finish before the worker times out. Use a CSV with a single website URL. In Render → Service → Settings, set **Start Command** to `gunicorn --bind 0.0.0.0:$PORT --timeout 120 app:app` so the worker allows up to 2 minutes per request.
- **Enrich returns no data or errors:** Confirm `OPENROUTER_API_KEY` is set correctly in the Render **Environment** tab (no extra spaces, full key). Check the **Logs** tab for Python errors.
- **Need to change Build/Start later:** In the Render dashboard, open your service → **Settings** → update **Build Command** and **Start Command**, then trigger a **Manual Deploy** from the **Manual Deploy** menu.

---

## Optional: Deploy using the Blueprint (render.yaml)

If your repo is already connected and you prefer to use the Blueprint:

1. In Render dashboard, click **New +** → **Blueprint**.
2. Connect the same GitHub repo and branch.
3. Render will read `render.yaml` and create a Web Service with the build/start commands from the file.
4. After the service is created, go to the service → **Environment** and add `OPENROUTER_API_KEY` (the Blueprint doesn’t set the value, only the key name).

Then use the app URL Render shows for that service.
