# SkillQuest · ORBIT-9

SkillQuest is a prompt-driven learning game aboard a damaged spaceship. It turns a learner's request into a step-by-step roadmap, checks that core concepts are covered, then turns each step into a ship-repair mission. Google Gemini generates roadmaps and missions when `GEMINI_API_KEY` is configured. Without that key, SkillQuest can use local Qwen through Ollama and builds playable missions from the approved roadmap. Django and SQLite store roadmaps, missions, answers, XP, and learner progress.

The story-led, step-gated gameplay takes inspiration from [SQL Island](https://sql-island.informatik.uni-kl.de/), reimagined for learner-selected topics rather than SQL-only challenges.

## Learning loop

1. Describe what you want to learn, your goal, current level, and any concepts that must be covered.
2. Gemini creates an ordered roadmap with four milestones and a checklist of core concepts, including topics explicitly named in the prompt.
3. Review how every core concept maps to the roadmap.
4. Choose **Launch the missions** to turn the approved plan into a short ship-repair story, lesson, example, practice question, hint, and XP reward for each step.
5. Complete all four missions to unlock the final escape challenge.

The app checks that every generated core concept is covered by at least one roadmap step. Name must-cover concepts explicitly in your prompt and review the generated checklist before launching missions.

NOVA is the shipboard co-pilot shown in the corner of the bridge, mission, and escape screens. NOVA celebrates restored systems, notices when a run of correct answers is interrupted, and opens a contextual hint after repeated misses.

## Requirements

- Python 3.10 or newer.
- Node.js and npm when rebuilding the Tailwind stylesheet; the compiled stylesheet is included for running Django.
- Either a Google Gemini API key or local Ollama with Qwen available.
- Internet access from the machine running Django when using Gemini.
- Docker is optional.

SkillQuest uses the public Gemini Developer API with `gemini-3.8-flash` by default. Create an API key in [Google AI Studio](https://aistudio.google.com/apikey), then put it in your local `.env`. Google controls model availability, rate limits, and any billing or free-tier eligibility for your account; see the [Gemini API documentation](https://ai.google.dev/gemini-api/docs) for current details.

## Run locally

From this folder, create the local configuration file:

```bash
cp .env.example .env
```

Set your Gemini key in `.env`:

```dotenv
GEMINI_API_KEY=your_google_ai_studio_key
```

Keep this key private and do not commit `.env`. Then install and run the app:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

When changing Tailwind classes or the dynamic bridge controls, build the local stylesheet with `npm install && npm run build:css`. During frontend work, use `npm run watch:css` in a second terminal. The app serves the generated `static/learning/tailwind.css`; it does not load Tailwind from a CDN.

If `GEMINI_API_KEY` is set, roadmap and mission generation use Gemini. If it is blank, the app uses local Ollama for roadmap generation and assembles launch-ready missions from the approved roadmap. To use that fallback, start Ollama and ensure the configured local model is available (`ollama run qwen:latest`).

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Restart Django after changing `.env` so it loads the new configuration.

SQLite stores data in `db.sqlite3` by default. Set `SQLITE_PATH` in `.env` to change the database file. Learner identity is stored in a signed browser cookie.

## Run with Docker Compose

Configure `.env` as described above, then run:

```bash
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000). Compose keeps SQLite data in a persistent `sqlite_data` volume. Stop with `Ctrl+C`; `docker compose down` keeps that saved data, while `docker compose down -v` deletes it.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | development placeholder | Set a long random value before hosting. |
| `DJANGO_DEBUG` | `True` | Set `False` for deployment. |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma-separated hostnames allowed to serve the app. |
| `SQLITE_PATH` | `db.sqlite3` in the project folder | SQLite database file path. |
| `GEMINI_API_KEY` | empty | Google AI Studio API key; sent only by the Django server. |
| `GEMINI_MODEL` | `gemini-3.8-flash` | Gemini model used to generate roadmaps and missions. |
| `AI_API_TIMEOUT` | `240` | Maximum request time in seconds for Gemini and Ollama. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local fallback endpoint when `GEMINI_API_KEY` is empty. |
| `OLLAMA_MODEL` | `qwen:latest` | Local fallback model tag. |

Gemini requests go to Google's `generativelanguage.googleapis.com` API. Keep the key on the server; never place it in frontend code. For hosted use, configure `GEMINI_API_KEY` as a server-side secret and allow outbound HTTPS to Google's API.

## Desktop and hackathon demo

The interface is desktop-first and runs in a browser. To share it on the same trusted Wi-Fi network:

```bash
python manage.py runserver 0.0.0.0:8000
```

Set `DJANGO_ALLOWED_HOSTS` to include your computer's LAN IP, then open `http://LAN-IP:8000` from another device on that network. Do not expose the Django development server publicly.

## Hosting

The included Docker image can run on a Docker host. Set a strong `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, and `DJANGO_ALLOWED_HOSTS` for the hosted domain. Attach a persistent disk or volume for SQLite. Configure `GEMINI_API_KEY` as a server-side secret in the hosting platform; never put it in frontend code. The hosted app also needs outbound access to Google's Gemini API.

## Troubleshooting

- **Missing or invalid API key:** set `GEMINI_API_KEY` in `.env`, restart Django, and check the key in [Google AI Studio](https://aistudio.google.com/apikey).
- **401 or 403 from Gemini:** verify the key and the API access available to your Google account. Do not paste the key into logs or the browser.
- **Model unavailable or quota error:** check `GEMINI_MODEL` and your current Gemini API model availability, quota, and billing settings.
- **Local fallback unavailable:** start Ollama and make sure the model in `OLLAMA_MODEL` is installed and responding.
- **Timeout:** check internet connectivity and increase `AI_API_TIMEOUT` if the selected provider is responding slowly.
- **Invalid generated roadmap:** try once more with a shorter prompt naming the goal and required concepts; generated output is checked for complete concept coverage before it is saved.
- **Port 8000 is busy:** run `python manage.py runserver 8001` and open [http://127.0.0.1:8001](http://127.0.0.1:8001).
- **Docker changes are not visible:** rebuild with `docker compose up --build`.

## Project layout

```text
skillquest/                         Django settings and URL configuration
learning/views.py                   Roadmap review and interactive mission views
learning/services/ai.py             Gemini API, local Qwen fallback, and course generation
learning/services/course_store.py   SQLite persistence and learner progress
learning/models.py                  Roadmap, course, and progress models
templates/learning/                 Bridge, flight plan, map, mission, and escape screens
static/learning/                    Spaceflight graphics and interface styles
docker-compose.yml                  Django plus persistent SQLite volume
```
