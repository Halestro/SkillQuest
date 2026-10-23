# SkillQuest · ORBIT-9

SkillQuest is a prompt-driven learning game aboard a damaged spaceship. It converts a learner's request into a step-by-step roadmap, lets them review the core concepts, then turns every step into a ship-repair mission. DeepSeek through Hugging Face is used when `HF_TOKEN` is configured. Without a token, local Qwen through Ollama creates the roadmap and SkillQuest immediately builds playable missions from that approved plan, so launching does not depend on a second long model response. Django and SQLite store roadmaps, missions, answers, XP, and learner progress.

The story-led, step-gated gameplay takes inspiration from [SQL Island](https://sql-island.informatik.uni-kl.de/), reimagined for learner-selected topics rather than SQL-only challenges.

## Learning loop

1. Describe what you want to learn, your goal, current level, and any concepts that must be covered.
2. The AI creates an ordered roadmap with four milestones and a checklist of core concepts, including topics explicitly named in the prompt.
3. Review how every core concept maps to the roadmap.
4. Choose **Launch the missions** to turn the approved plan into a short ship-repair story, lesson, example, practice question, hint, and XP reward for each step.
5. Complete all four missions to unlock the final escape challenge.

The app checks that every generated core concept is covered by at least one roadmap step. Name must-cover concepts explicitly in your prompt and review the generated checklist before launching missions.

NOVA is the shipboard co-pilot shown in the corner of the bridge, mission, and escape screens. NOVA celebrates restored systems, notices when a run of correct answers is interrupted, and opens a contextual hint after repeated misses.

## Requirements

- Python 3.10 or newer.
- Node.js and npm when rebuilding the Tailwind stylesheet; the compiled stylesheet is included for running Django.
- Either a Hugging Face token with **Make calls to Inference Providers** permission, or local Ollama with Qwen available.
- Internet access from the machine running Django.
- Docker is optional.

When `HF_TOKEN` is set, the default model is `deepseek-ai/DeepSeek-V3.2:novita`. Change `HF_MODEL` in `.env` to another chat-completion model available to your Hugging Face account. If `HF_TOKEN` is blank, SkillQuest uses `qwen:latest` from local Ollama instead. See the [DeepSeek model page](https://huggingface.co/deepseek-ai/DeepSeek-V3.2) and [Hugging Face Inference Providers guide](https://huggingface.co/docs/inference-providers/tasks/chat-completion).

## Run locally

From this folder, create the local configuration file:

```bash
cp .env.example .env
```

To use DeepSeek, create a fine-grained token in [Hugging Face token settings](https://huggingface.co/settings/tokens). Give it **Make calls to Inference Providers** permission, then set `HF_TOKEN` in `.env`:

```dotenv
HF_TOKEN=hf_your_token_here
```

Keep this token private and do not commit `.env`. Then install and run the app:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

When changing Tailwind classes or the dynamic bridge controls, build the local stylesheet with `npm install && npm run build:css`. During frontend work, use `npm run watch:css` in a second terminal. The app serves the generated `static/learning/tailwind.css`; it does not load Tailwind from a CDN.

Without an HF token, start Ollama and ensure the configured local model is available (`ollama run qwen:latest`). The app automatically uses that local model as its fallback.

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). If editing `.env` while the server is running, restart Django so it loads the new token. With `HF_TOKEN` configured, roadmap and mission generation each call DeepSeek separately. Without it, Ollama generates the roadmap and the mission set is assembled locally from the approved roadmap.

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
| `HF_API_BASE_URL` | `https://router.huggingface.co/v1` | Hugging Face's OpenAI-compatible Inference Providers endpoint. |
| `HF_TOKEN` | empty | Fine-grained Hugging Face token with Inference Providers permission. |
| `HF_MODEL` | `deepseek-ai/DeepSeek-V3.2:novita` | DeepSeek model and inference provider route. |
| `HF_API_TIMEOUT` | `240` | Maximum request time in seconds. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local fallback endpoint when `HF_TOKEN` is empty. |
| `OLLAMA_MODEL` | `qwen:latest` | Local fallback model tag. |

When DeepSeek is selected, Hugging Face forwards prompts to an inference provider; access or usage may depend on your account settings. Without a token, prompts go to local Ollama instead. Check Hugging Face's current [Inference Providers documentation](https://huggingface.co/docs/inference-providers/index) for access details.

## Desktop and hackathon demo

The interface is desktop-first and runs in a browser. To share it on the same trusted Wi-Fi network:

```bash
python manage.py runserver 0.0.0.0:8000
```

Set `DJANGO_ALLOWED_HOSTS` to include your computer's LAN IP, then open `http://LAN-IP:8000` from another device on that network. Do not expose the Django development server publicly.

## Hosting

The included Docker image can run on a Docker host. Set a strong `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, and `DJANGO_ALLOWED_HOSTS` for the hosted domain. Attach a persistent disk or volume for SQLite. Configure `HF_TOKEN` as a server-side secret in the hosting platform; never put it in frontend code. The hosted app also needs outbound access to `router.huggingface.co` and a Hugging Face account that can call the selected DeepSeek inference provider.

## Troubleshooting

- **Missing token:** set `HF_TOKEN` in `.env`, restart Django, and check that the token has **Make calls to Inference Providers** permission.
- **401 or 403 from Hugging Face:** verify the token and its permission. Do not paste the token into logs or the browser.
- **Model/provider unavailable:** check the current model and provider availability on the Hugging Face model page, then update `HF_MODEL`.
- **Local fallback unavailable:** start Ollama and make sure the model in `OLLAMA_MODEL` is installed and responding.
- **Timeout:** check internet connectivity and increase `HF_API_TIMEOUT` if the selected provider is responding slowly.
- **Invalid generated roadmap:** try once more with a shorter prompt naming the goal and required concepts; generated output is checked for complete concept coverage before it is saved.
- **Port 8000 is busy:** run `python manage.py runserver 8001` and open [http://127.0.0.1:8001](http://127.0.0.1:8001).
- **Docker changes are not visible:** rebuild with `docker compose up --build`.

## Project layout

```text
skillquest/                         Django settings and URL configuration
learning/views.py                   Roadmap review and interactive mission views
learning/services/ai.py             DeepSeek API, local Qwen fallback, and course generation
learning/services/course_store.py   SQLite persistence and learner progress
learning/models.py                  Roadmap, course, and progress models
templates/learning/                 Bridge, flight plan, map, mission, and escape screens
static/learning/                    Spaceflight graphics and interface styles
docker-compose.yml                  Django plus persistent SQLite volume
```
