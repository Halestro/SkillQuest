# SkillQuest · ORBIT-9

SkillQuest turns a learner's goal into a checked learning roadmap, then turns that roadmap into short, playable spaceship missions. Learners practice each concept, get hints and feedback, earn XP, and unlock the final escape challenge after mastering the required skills.

Roadmaps and missions use Google Gemini when `GEMINI_API_KEY` is configured. Otherwise the app can use local Qwen through Ollama for roadmap generation and assemble playable missions from the approved roadmap. Django saves roadmaps, courses, attempts, and learner progress in Supabase Postgres.

## Learning loop

1. Describe a learning goal, current level, and any concepts that must be covered.
2. Review the generated roadmap and its core-concept checklist.
3. Launch the roadmap as a sequence of ship-repair missions.
4. Learn a concept, study an example, then answer an applied challenge.
5. Use contextual hints, build mastery, and unlock the final escape challenge.

The app checks that every generated core concept appears in at least one roadmap step. NOVA, the shipboard co-pilot, celebrates progress and offers contextual hints after repeated misses.

## Requirements

- Python 3.10 or newer.
- A Supabase project and its Postgres connection string.
- A Gemini API key or local Ollama with the configured Qwen model.
- Node.js and npm only when rebuilding the Tailwind stylesheet; the compiled stylesheet is included.
- Docker is optional.

## Set up Supabase

1. Create a project in [Supabase](https://supabase.com/dashboard).
2. In the project dashboard, open **Connect** and copy a Postgres connection string. Use the direct connection for a persistent host; if your host only supports IPv4, choose the Session pooler connection string. See [Supabase connection options](https://supabase.com/docs/guides/database/connecting-to-postgres).
3. Put that URL in the `DATABASE_URL` setting in your local `.env` file or your hosting provider's server-side environment variables. Include `sslmode=require` if it is not already present. Django also enforces SSL in its PostgreSQL connection options.
4. Replace the password placeholder with your database password. URL-encode reserved password characters such as `@`, `#`, `?`, and spaces.
5. Run Django migrations to create the app's tables in Supabase.

Keep `DATABASE_URL` private. It contains database credentials; never place it in frontend code or commit it to GitHub. SkillQuest connects to Supabase Postgres through Django's ORM, so the browser does not need a Supabase API key.

## Run locally

Create your local environment file and set `DATABASE_URL` and the AI provider settings in it:

```shell
cp .env.example .env
```

Then install and run Django:

```shell
python3 -m venv .venv
source .venv/bin/activate         # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). If `GEMINI_API_KEY` is set, roadmap and mission generation use Gemini. If it is blank, start Ollama and ensure the configured model is available (for example, `ollama run qwen:latest`).

When changing Tailwind classes or the dynamic bridge controls, rebuild the stylesheet with `npm install && npm run build:css`. During frontend work, run `npm run watch:css` in a second terminal. Django serves the compiled file at `static/learning/tailwind.css`; Tailwind is not loaded from a CDN.

Learner identity is stored in a signed browser cookie. Existing local database records are not copied automatically into a new Supabase project.

## Run with Docker Compose

Create `.env` as described above, then run:

```shell
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000). The container runs `python manage.py migrate` before starting Django, so its `DATABASE_URL` must point to your Supabase project. Stop with `Ctrl+C`; `docker compose down` stops the container without affecting data stored in Supabase.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | empty | Required Supabase Postgres URL. The app exits with a clear error until this is configured. |
| `DJANGO_SECRET_KEY` | development placeholder | Set a long, random value before hosting. |
| `DJANGO_DEBUG` | `True` | Set to `False` for deployment. |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma-separated hostnames allowed to serve the app. |
| `GEMINI_API_KEY` | empty | Google AI Studio API key; sent only by the Django server. |
| `GEMINI_MODEL` | `gemini-3.8-flash` | Gemini model used to generate roadmaps and missions. |
| `AI_API_TIMEOUT` | `240` | Maximum request time in seconds for Gemini and Ollama. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local fallback endpoint when `GEMINI_API_KEY` is empty. |
| `OLLAMA_MODEL` | `qwen:latest` | Local fallback model tag. |

For a hosted app, configure all secrets in the hosting provider's server-side environment settings. The backend needs outbound network access to Supabase Postgres and, when Gemini is enabled, Google's Gemini API.

## Hosting

The included Docker image can run on a Docker host. Set a strong `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, and `DJANGO_ALLOWED_HOSTS` for the hosted domain. Set `DATABASE_URL` to the Supabase connection string as a server-side secret. Use a direct or Session pooler connection appropriate for the host's network; avoid exposing the database password in the frontend or repository. The Docker startup command applies Django migrations before serving requests.

## Troubleshooting

- **Missing database configuration:** Set `DATABASE_URL` to the Postgres URI from the Supabase dashboard, then restart Django.
- **Database connection or SSL error:** Check the project connection string, database password, host network support, and `sslmode=require`. Use the Session pooler if the host cannot reach the direct endpoint over IPv6.
- **Missing or invalid AI key:** Set `GEMINI_API_KEY` in `.env`, restart Django, and verify the key in [Google AI Studio](https://aistudio.google.com/apikey).
- **Gemini model or quota error:** Check `GEMINI_MODEL` and current API availability, quota, and billing settings.
- **Local fallback unavailable:** Start Ollama and make sure the model in `OLLAMA_MODEL` is installed and responding.
- **Timeout:** Check connectivity and increase `AI_API_TIMEOUT` if the selected provider is responding slowly.
- **Invalid generated roadmap:** Retry with a shorter prompt naming the goal and required concepts; generated output is checked for complete concept coverage before it is saved.
- **Port 8000 is busy:** Run `python manage.py runserver 8001` and open [http://127.0.0.1:8001](http://127.0.0.1:8001).
- **Docker changes are not visible:** Rebuild with `docker compose up --build`.

## Project layout

- `skillquest/` — Django settings and URL configuration.
- `learning/views.py` — Roadmap review and interactive mission views.
- `learning/services/ai.py` — Gemini API, local Qwen fallback, and course generation.
- `learning/services/course_store.py` — Django ORM persistence for roadmaps, courses, and learner progress.
- `learning/models.py` — Roadmap, course, and progress models.
- `templates/learning/` — Bridge, flight plan, map, mission, and escape screens.
- `static/learning/` — Spaceflight graphics and interface styles.
- `docker-compose.yml` — Django web service connected to Supabase through `DATABASE_URL`.
