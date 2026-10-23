"""Generate skill roadmaps and turn approved plans into playable missions."""
import json
import re
import urllib.error
import urllib.request

from django.conf import settings

SHORT = {"type": "string", "maxLength": 180}
ID = {"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$", "maxLength": 60}
ROADMAP_SCHEMA = {
    "type": "object",
    "properties": {
        "title": SHORT,
        "intro": SHORT,
        "topic": SHORT,
        "goal": SHORT,
        "level": {"type": "string", "enum": ["Beginner", "Intermediate", "Advanced"]},
        "core_concepts": {"type": "array", "minItems": 4, "maxItems": 12, "items": {
            "type": "object", "properties": {"id": ID, "name": SHORT, "why": SHORT},
            "required": ["id", "name", "why"], "additionalProperties": False,
        }},
        "steps": {"type": "array", "minItems": 4, "maxItems": 4, "items": {
            "type": "object", "properties": {
                "id": ID, "name": SHORT, "concept": SHORT,
                "concept_ids": {"type": "array", "minItems": 1, "items": ID},
                "outcome": SHORT, "prerequisite_ids": {"type": "array", "items": ID},
                "practice_preview": SHORT,
            },
            "required": ["id", "name", "concept", "concept_ids", "outcome", "prerequisite_ids", "practice_preview"],
            "additionalProperties": False,
        }},
    },
    "required": ["title", "intro", "topic", "goal", "level", "core_concepts", "steps"],
    "additionalProperties": False,
}

MISSION_SCHEMA = {
    "type": "object",
    "properties": {
        "intro": SHORT,
        "missions": {"type": "array", "minItems": 4, "maxItems": 4, "items": {
            "type": "object", "properties": {
                "step_id": ID, "name": SHORT, "story": SHORT, "explanation": SHORT,
                "example": SHORT, "question": SHORT,
                "choices": {"type": "array", "minItems": 3, "maxItems": 3, "items": SHORT},
                "answer": SHORT, "hint": SHORT, "practice": SHORT,
                "difficulty": {"type": "integer", "minimum": 1, "maximum": 3},
            },
            "required": ["step_id", "name", "story", "explanation", "example", "question", "choices", "answer", "hint", "practice", "difficulty"],
            "additionalProperties": False,
        }},
        "boss": {"type": "object", "properties": {
            "story": SHORT, "question": SHORT,
            "choices": {"type": "array", "minItems": 3, "maxItems": 3, "items": SHORT},
            "answer": SHORT, "hint": SHORT,
        }, "required": ["story", "question", "choices", "answer", "hint"], "additionalProperties": False},
    },
    "required": ["intro", "missions", "boss"], "additionalProperties": False,
}


def _decode_json_object(content):
    """Extract a complete JSON object even if the model adds prose or fences."""
    content = re.sub(r"<think>.*?</think>", "", content or "", flags=re.DOTALL).strip()
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", content):
        try:
            value, _ = decoder.raw_decode(content[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("The model response did not contain a complete JSON object.")


def _ask_gemini(system, user, schema, max_tokens):
    """Use Google's hosted Gemini API and ask it for schema-shaped JSON."""
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": 0.15,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
    }
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.GEMINI_MODEL}:generateContent"
    )
    request = urllib.request.Request(
        endpoint, data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": settings.GEMINI_API_KEY,
        }, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.AI_API_TIMEOUT) as response:
            result = json.loads(response.read().decode())
        parts = result["candidates"][0]["content"]["parts"]
        text_parts = [
            part["text"] for part in parts
            if isinstance(part, dict) and isinstance(part.get("text"), str) and not part.get("thought")
        ]
        content = "\n".join(text_parts)
        if not content:
            raise TypeError("The API response did not include text content.")
        return _decode_json_object(content)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:700]
        raise RuntimeError(f"Gemini API returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not connect to the Gemini API: {exc}") from exc
    except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"Gemini returned an unusable response: {exc}") from exc


def _ask_local_qwen(system, user, schema, max_tokens):
    """Use the installed local model when the Gemini API key is not configured."""
    payload = {
        "model": settings.OLLAMA_MODEL,
        "stream": False,
        "format": schema,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "options": {"temperature": 0.15, "num_predict": max_tokens},
    }
    request = urllib.request.Request(
        settings.OLLAMA_BASE_URL + "/api/chat", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.AI_API_TIMEOUT) as response:
            result = json.loads(response.read().decode())
        content = result["message"]["content"]
        if not isinstance(content, str):
            raise TypeError("Ollama did not return text content.")
        return _decode_json_object(content)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        raise RuntimeError(f"Local Ollama returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(
            f"GEMINI_API_KEY is not configured and local Ollama is unreachable at {settings.OLLAMA_BASE_URL}. "
            f"Start Ollama with {settings.OLLAMA_MODEL} available, or configure GEMINI_API_KEY. Details: {exc}"
        ) from exc
    except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"Local Qwen returned an unusable response: {exc}") from exc


def _ask_model(system, user, schema, max_tokens):
    if settings.GEMINI_API_KEY:
        return _ask_gemini(system, user, schema, max_tokens)
    return _ask_local_qwen(system, user, schema, max_tokens)


def _slug(value):
    return re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value or "") is not None


def _normalized_concept(value):
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").lower()))


def _concept_slug(value, used):
    slug = re.sub(r"[^a-z0-9]+", "-", _normalized_concept(value)).strip("-")[:52] or "core-skill"
    candidate = slug
    suffix = 2
    while candidate in used:
        candidate = f"{slug[:48]}-{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def _extract_required_concepts(prompt):
    """Pick out explicitly listed concepts so a small local model cannot omit them."""
    found = []
    directive = re.compile(
        r"\b(?:must[ -]cover|must[ -]include|cover|including|include|focus on|"
        r"topics?(?:\s+(?:include|like|such as))?|concepts?(?:\s+(?:include|like|such as)))\b"
        r"\s*[:\-]?\s*(.+?)(?:[.!?\n]|$)", re.IGNORECASE,
    )
    for match in directive.finditer(prompt):
        clause = match.group(1)
        # Keep uppercase technical names such as SELECT and multiword GROUP BY.
        for term in re.findall(r"\b[A-Z][A-Z0-9]*(?:\s+[A-Z][A-Z0-9]*)*\b", clause):
            if term.lower() not in {"and", "or", "with", "the"}:
                found.append(term.strip())
        for part in re.split(r",|;|\band\b|\bor\b", clause, flags=re.IGNORECASE):
            part = part.strip()
            if re.search(r"\s+with\s+", part, flags=re.IGNORECASE):
                part = re.split(r"\s+with\s+", part, flags=re.IGNORECASE)[-1]
            part = re.sub(r"^(?:also\s+)?(?:the\s+)?(?:basic\s+)?", "", part, flags=re.IGNORECASE)
            part = part.strip(" .:;!?-—")
            if part and len(part) <= 80:
                found.append(part)
    unique, seen = [], set()
    for item in found:
        key = _normalized_concept(item)
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _repair_roadmap(roadmap, prompt):
    """Repair concept IDs and explicitly named coverage before validation."""
    generic_names = {
        "examples", "faq", "practice", "quiz", "review", "summary", "introduction",
        "conclusion", "resources", "key takeaways", "learning objectives",
    }
    concepts, old_to_new, by_name, used_ids = [], {}, {}, set()
    for item in roadmap.get("core_concepts", []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        key = _normalized_concept(name)
        if not key or key in generic_names:
            continue
        old_id = item.get("id")
        if key in by_name:
            if old_id:
                old_to_new[old_id] = by_name[key]
            continue
        new_id = _concept_slug(name, used_ids)
        by_name[key] = new_id
        if old_id:
            old_to_new[old_id] = new_id
        concepts.append({"id": new_id, "name": name[:180], "why": str(item.get("why") or "Core skill for the learning goal.")[:180]})

    required_ids = set()
    for name in _extract_required_concepts(prompt):
        key = _normalized_concept(name)
        matched = next((item["id"] for item in concepts if
                       key == _normalized_concept(item["name"])
                       or key in _normalized_concept(item["name"])
                       or _normalized_concept(item["name"]) in key), None)
        if matched is None:
            matched = _concept_slug(name, used_ids)
            concepts.append({"id": matched, "name": name[:180], "why": "Explicitly requested in your learning prompt."})
            by_name[key] = matched
        required_ids.add(matched)

    if len(concepts) > 12:
        required = [item for item in concepts if item["id"] in required_ids]
        extras = [item for item in concepts if item["id"] not in required_ids]
        concepts = required + extras[:max(0, 12 - len(required))]
    if len(concepts) < 4:
        for step in roadmap.get("steps", []):
            name = str(step.get("name", "")).strip()
            key = _normalized_concept(name)
            if key and key not in by_name and key not in generic_names:
                new_id = _concept_slug(name, used_ids)
                by_name[key] = new_id
                concepts.append({"id": new_id, "name": name[:180], "why": "Builds toward the learning goal."})
            if len(concepts) >= 4:
                break

    roadmap["core_concepts"] = concepts
    known = {item["id"] for item in concepts}
    steps = roadmap.get("steps", [])
    for step in steps:
        step["concept_ids"] = list(dict.fromkeys(
            old_to_new.get(item, item) for item in step.get("concept_ids", [])
            if old_to_new.get(item, item) in known
        ))
    for concept in concepts:
        if any(concept["id"] in step["concept_ids"] for step in steps):
            continue
        terms = set(_normalized_concept(concept["name"]).split()) - {"and", "or", "the", "a", "an", "of", "with", "for", "to", "in", "on", "by"}
        scores = []
        for index, step in enumerate(steps):
            step_text = " ".join(str(step.get(key, "")) for key in ("name", "concept", "outcome", "practice_preview"))
            words = set(_normalized_concept(step_text).split())
            scores.append((len(terms & words), -len(step["concept_ids"]), -index))
        best = max(range(len(steps)), key=lambda index: scores[index])
        steps[best]["concept_ids"].append(concept["id"])
    return roadmap


def generate_roadmap(prompt):
    system = (
        "You are an instructional designer. Turn the learner's request into a complete, ordered skill roadmap. "
        "Return one compact JSON object matching the supplied schema, with no markdown or commentary. Identify 4 to 12 essential core concepts, then map every one to "
        "one or more of exactly four steps. Steps must build from prerequisite knowledge to applied use. "
        "State measurable outcomes and a short practice preview for each. Infer topic, goal, and level from the request. "
        "If the learner explicitly names must-cover concepts, preserve each named concept and map it to a step. "
        "Keep wording concrete and compact. Do not gamify yet: no XP, quests, characters, or rewards."
    )
    user = "Learner request:\n" + prompt
    for attempt in range(2):
        # Four fully mapped steps need more room than the model's default short
        # response budget. Keep the schema fields concise, but avoid truncating
        # the JSON before it can be parsed.
        raw = _ask_model(system, user, ROADMAP_SCHEMA, 3000)
        try:
            return validate_roadmap(_repair_roadmap(raw, prompt))
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            if attempt:
                raise ValueError(f"The generated roadmap failed its core-concept coverage check: {exc}") from exc
            user += "\n\nYour previous JSON failed validation: " + str(exc) + ". Return a corrected complete roadmap. Keep every named must-cover concept and map all concepts to steps."


def validate_roadmap(roadmap):
    concepts = roadmap.get("core_concepts", [])
    steps = roadmap.get("steps", [])
    if not 4 <= len(concepts) <= 12 or len(steps) != 4:
        raise ValueError("The roadmap needs four steps and four to twelve core concepts.")
    concept_ids = [item.get("id") for item in concepts]
    step_ids = [item.get("id") for item in steps]
    if len(set(concept_ids)) != len(concept_ids) or len(set(step_ids)) != len(step_ids):
        raise ValueError("Roadmap identifiers must be unique.")
    if not all(_slug(item) for item in concept_ids + step_ids):
        raise ValueError("Roadmap identifiers must be lowercase URL-safe words.")
    known_concepts = set(concept_ids)
    covered = set()
    known_steps = set()
    for step in steps:
        refs = step.get("concept_ids", [])
        prereqs = step.get("prerequisite_ids", [])
        if not refs or not set(refs).issubset(known_concepts):
            raise ValueError("Every roadmap step must map to known core concepts.")
        # Keep the progression scaffold valid if the model invents a forward
        # prerequisite. The ordered roadmap itself remains the progression;
        # only references to already introduced steps are retained.
        step["prerequisite_ids"] = list(dict.fromkeys(
            prerequisite for prerequisite in prereqs if prerequisite in known_steps
        ))
        covered.update(refs)
        known_steps.add(step["id"])
    missing = [item["name"] for item in concepts if item["id"] not in covered]
    if missing:
        raise ValueError("Unmapped core concepts: " + ", ".join(missing))
    roadmap["core_concepts"] = concepts
    roadmap["steps"] = steps
    return roadmap


def gamify_roadmap(roadmap):
    # Mission generation should never block the learner from starting. When a
    # hosted API key is absent, turn the approved roadmap into a small
    # playable mission set locally instead of asking Ollama for a second, large
    # structured response (which can take minutes on modest hardware).
    if not settings.GEMINI_API_KEY:
        return _build_roadmap_missions(roadmap)

    system = (
        "You are a game-based learning designer. The learner woke alone on a damaged spaceship, ORBIT-9, and must "
        "restore its systems to get home. Turn the supplied approved roadmap into four engaging ship-repair missions "
        "and one final boss challenge. Return one compact JSON object matching the supplied schema, with no markdown or commentary. Preserve each step_id exactly and "
        "make one mission for every roadmap step in the same order. Teach the step's mapped core concepts in a "
        "short explanation and example. Each check must be applied, unambiguous, and have exactly one correct "
        "choice copied exactly into answer. Give each mission a short immersive ship emergency story, but keep the "
        "learning explanation accurate and focused on the supplied topic. Make the final boss an applied challenge "
        "that combines the roadmap skills and represents the ship's escape attempt. Give useful hints and practice "
        "advice. Keep fields concise."
    )
    user = "Approved roadmap:\n" + json.dumps(roadmap, ensure_ascii=False)
    for attempt in range(2):
        raw = _ask_model(system, user, MISSION_SCHEMA, 4500)
        try:
            return validate_missions(raw, roadmap)
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            if attempt:
                raise ValueError(f"The generated missions did not preserve the approved roadmap: {exc}") from exc
            user += "\n\nYour previous JSON failed validation: " + str(exc) + ". Return a corrected complete set of missions, preserving every step_id in the same order."


def _build_roadmap_missions(roadmap):
    """Create launch-ready applied checks directly from the approved roadmap."""
    systems = ("life support", "navigation", "communications", "the escape drive")
    missions = []
    concept_names = {item["id"]: item["name"] for item in roadmap["core_concepts"]}
    for index, step in enumerate(roadmap["steps"]):
        covers = [concept_names[item] for item in step["concept_ids"]]
        concepts = ", ".join(covers)
        practice = step["practice_preview"].strip()
        answer = f"Apply {concepts} to the task and verify the result."[:180]
        question = "Which action best completes the practice task shown above?"
        missions.append({
            "step_id": step["id"],
            "name": step["name"],
            "story": f"A fault has isolated {systems[index % len(systems)]}. Repair it by completing {step['name']}.",
            "explanation": f"{step['concept']} Core concepts in this mission: {concepts}.",
            "example": practice,
            "question": question,
            "choices": [
                answer,
                "Skip the listed concepts and submit without checking your result.",
                "Move to the next system without doing this practice task.",
            ],
            "answer": answer,
            "hint": f"Use {concepts} and check that your result matches the mission outcome.",
            "practice": practice,
            "difficulty": min(3, 1 + index // 2),
        })

    goal = roadmap["goal"].strip().rstrip(".")
    boss_answer = f"Combine all four steps in order to {goal.lower()}"[:180]
    result = {
        "intro": "ORBIT-9 is damaged. Each mission repairs a system and builds one more skill toward your goal.",
        "missions": missions,
        "boss": {
            "story": "The escape window is open. The ship needs every repaired system working together.",
            "question": f"Which plan gives ORBIT-9 the best chance to escape while achieving your learning goal: {goal}?"[:180],
            "choices": [
                boss_answer,
                "Skip the later missions and activate the escape drive immediately.",
                "Repeat only the first repair and ignore the remaining systems.",
            ],
            "answer": boss_answer,
            "hint": "Use the complete roadmap in order, then apply its final goal to the escape challenge.",
        },
    }
    return validate_missions(result, roadmap)


def validate_missions(result, roadmap):
    missions = result.get("missions", [])
    steps = roadmap["steps"]
    if len(missions) != len(steps):
        raise ValueError("Every roadmap step must become one mission.")
    built = []
    concepts = {item["id"]: item["name"] for item in roadmap["core_concepts"]}
    for step, mission in zip(steps, missions):
        if mission.get("step_id") != step["id"]:
            raise ValueError("Mission order or step IDs do not match the approved roadmap.")
        if mission.get("answer") not in mission.get("choices", []):
            raise ValueError("Every mission answer must exactly match one choice.")
        if len(mission.get("choices", [])) != 3:
            raise ValueError("Every mission must have three choices.")
        built.append({
            **mission,
            "id": step["id"],
            "concept": step["concept"],
            "covers": [concepts[item] for item in step["concept_ids"]],
            "outcome": step["outcome"],
            "difficulty": mission.get("difficulty", 1),
        })
    boss = result.get("boss", {})
    if boss.get("answer") not in boss.get("choices", []) or len(boss.get("choices", [])) != 3:
        raise ValueError("The boss must have three choices and one exact answer.")
    boss.setdefault("story", "The escape route is open. Use what you learned to bring ORBIT-9 home.")
    return {**roadmap, "intro": result.get("intro", roadmap["intro"]), "skills": built, "boss": boss}
