import os
import time
import json
import re
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

MODEL_NAME = "gemini-2.0-flash"

is_placeholder = (
    (not api_key)
    or ("your_gemini" in api_key.lower())
    or (not api_key.startswith("AIzaSy"))
)

# ── Role keyword table ────────────────────────────────────────────────────────
ROLE_PATTERNS = [
    (r"machine learning|ml engineer|ml developer",         "machine learning engineer"),
    (r"data scientist",                                     "data scientist"),
    (r"data analyst",                                       "data analyst"),
    (r"data engineer",                                      "data engineer"),
    (r"python\s*(developer|engineer|dev)",                  "python developer"),
    (r"java\s*(developer|engineer|dev)",                    "java developer"),
    (r"javascript|js\s*(developer|engineer)",               "javascript developer"),
    (r"sql\s*(developer|analyst|engineer)",                 "sql developer"),
    (r"devops\s*(engineer)?",                               "devops engineer"),
    (r"qa\s*(engineer|analyst|tester)?|quality assurance",  "qa engineer"),
    (r"project manager|pm\b",                               "project manager"),
    (r"product manager",                                    "product manager"),
    (r"frontend|front-end\s*(developer|engineer)",          "frontend developer"),
    (r"backend|back-end\s*(developer|engineer)",            "backend developer"),
    (r"full[ -]?stack\s*(developer|engineer)",              "fullstack developer"),
    (r"software\s*(developer|engineer)",                    "software engineer"),
    (r"android\s*(developer|engineer)",                     "android developer"),
    (r"ios\s*(developer|engineer)",                         "ios developer"),
    (r"cloud\s*(engineer|architect)",                       "cloud engineer"),
    (r"sales\s*(manager|executive|representative)?",        "sales manager"),
    (r"hr\s*(manager|executive)?|human resources",          "hr manager"),
    (r"finance\s*(analyst|manager)?",                       "finance analyst"),
    # ── Standalone tech keyword fallbacks (no 'developer'/'engineer' suffix needed)
    # These MUST come after the more-specific patterns above
    (r"\bjava\b",              "java developer"),
    (r"\bpython\b",            "python developer"),
    (r"\bsql\b",               "sql developer"),
    (r"\bjavascript\b|\bjs\b", "javascript developer"),
    (r"\bml\b|\bai\b",         "machine learning engineer"),
    (r"\breact\b",             "frontend developer"),
    (r"\bangular\b|\bvue\b",   "frontend developer"),
    (r"\bnode\b|\bnodejs\b",   "backend developer"),
    (r"\bphp\b",               "backend developer"),
    (r"\bruby\b|\brails\b",    "backend developer"),
    (r"\brust\b|\bgolang\b|\bgo\b", "software engineer"),
    (r"\bkotlin\b|\bswift\b",  "android developer"),
    (r"\bflutter\b",           "android developer"),
    (r"\bdocker\b|\bkubernetes\b|\bk8s\b", "devops engineer"),
    (r"\baws\b|\bgcp\b|\bazure\b",          "cloud engineer"),
    # generic fallback
    (r"(senior|junior|mid|lead)?\s*(\w+)\s*(developer|engineer|analyst|manager|scientist|designer|architect)", None),
]


def extract_role(text: str) -> str | None:
    """Return the job role mentioned in text, or None."""
    t = text.lower()
    for pattern, label in ROLE_PATTERNS:
        m = re.search(pattern, t)
        if m:
            if label:
                return label
            # Generic match: reassemble from capture groups
            groups = [g for g in m.groups() if g]
            return " ".join(groups).strip()
    return None

SENIORITY_PATTERN = re.compile(
    r"\b(junior|entry[ -]?level|mid[ -]?level|mid|middle|senior|lead|principal|"
    r"[1-9]\s*(?:\+?\s*years?|yrs?))\b",
    re.IGNORECASE
)

def extract_seniority(text: str) -> str | None:
    m = SENIORITY_PATTERN.search(text)
    if not m:
        return None
    val = m.group(1).lower()
    if any(k in val for k in ("senior", "lead", "principal")):
        return "senior"
    if any(k in val for k in ("junior", "entry")):
        return "junior"
    if any(k in val for k in ("mid", "middle")):
        return "mid"
    # years-based heuristic
    yr_match = re.search(r"(\d+)", val)
    if yr_match:
        yrs = int(yr_match.group(1))
        if yrs <= 2:  return "junior"
        if yrs <= 5:  return "mid"
        return "senior"
    return None

# Assessment pick tables (role → catalog names)
ROLE_PICKS = {
    "java":              ["Java Coding Test", "Verify Interactive - Deductive Reasoning", "Verify Interactive - Numerical Reasoning", "Verify Interactive - Inductive Reasoning", "Verify Interactive - Verbal Reasoning"],
    "python":            ["Python Coding Test", "Verify Interactive - Deductive Reasoning", "Verify Interactive - Numerical Reasoning", "Verify Interactive - Inductive Reasoning", "Verify Interactive - Verbal Reasoning"],
    "javascript":        ["JavaScript Development Test", "HTML5 and CSS3 Test", "Verify Interactive - Deductive Reasoning", "Verify Interactive - Numerical Reasoning", "Verify Interactive - Inductive Reasoning"],
    "sql":               ["SQL Database Test", "Verify Interactive - Numerical Reasoning", "Verify Interactive - Deductive Reasoning", "Verify Interactive - Inductive Reasoning", "Verify Interactive - Verbal Reasoning"],
    "machine learning":  ["Verify Interactive - Numerical Reasoning", "Verify Interactive - Inductive Reasoning", "Verify Interactive - Deductive Reasoning", "Verify Interactive - Verbal Reasoning", "Verify G+ Test"],
    "data scientist":    ["Verify Interactive - Numerical Reasoning", "Verify Interactive - Inductive Reasoning", "Verify Interactive - Deductive Reasoning", "Verify Interactive - Verbal Reasoning", "Verify G+ Test"],
    "data analyst":      ["Verify Interactive - Numerical Reasoning", "Verify Interactive - Verbal Reasoning", "Verify Interactive - Deductive Reasoning", "Verify Interactive - Inductive Reasoning", "Verify G+ Test"],
    "devops":            ["DevOps Practices Test", "Verify Interactive - Deductive Reasoning", "Verify Interactive - Numerical Reasoning", "Verify Interactive - Inductive Reasoning", "Agile Software Development Test"],
    "qa":                ["Verify Interactive - Deductive Reasoning", "Verify Interactive - Inductive Reasoning", "Verify Interactive - Numerical Reasoning", "Verify Interactive - Verbal Reasoning", "Agile Software Development Test"],
    "project manager":   ["Project Management Skills Test", "Occupational Personality Questionnaire (OPQ32)", "Verify Interactive - Verbal Reasoning", "Situational Judgement Test (SJT)", "Agile Software Development Test"],
    "product manager":   ["Occupational Personality Questionnaire (OPQ32)", "Verify Interactive - Verbal Reasoning", "Situational Judgement Test (SJT)", "Business Communication Test", "Agile Software Development Test"],
    "sales":             ["Sales Simulation", "Occupational Personality Questionnaire (OPQ32)", "Situational Judgement Test (SJT)", "Verify Interactive - Verbal Reasoning", "Business Communication Test"],
    "hr":                ["Occupational Personality Questionnaire (OPQ32)", "Situational Judgement Test (SJT)", "Verify Interactive - Verbal Reasoning", "Business Communication Test", "Global Skills Assessment (GSA)"],
    "frontend":          ["React Framework Coding Test", "HTML5 and CSS3 Test", "JavaScript Development Test", "Verify Interactive - Deductive Reasoning", "Verify Interactive - Numerical Reasoning"],
    "backend":           ["JavaScript Development Test", "Verify Interactive - Deductive Reasoning", "Verify Interactive - Numerical Reasoning", "Verify Interactive - Inductive Reasoning", "Agile Software Development Test"],
    "fullstack":         ["React Framework Coding Test", "HTML5 and CSS3 Test", "JavaScript Development Test", "Verify Interactive - Deductive Reasoning", "Verify Interactive - Numerical Reasoning"],
    "software":          ["Verify Interactive - Deductive Reasoning", "Verify Interactive - Numerical Reasoning", "Verify Interactive - Inductive Reasoning", "Verify Interactive - Verbal Reasoning", "Agile Software Development Test"],
    "android":           ["Verify Interactive - Deductive Reasoning", "Verify Interactive - Inductive Reasoning", "Verify Interactive - Numerical Reasoning", "Verify Interactive - Verbal Reasoning", "Basic Computer Literacy Test"],
    "ios":               ["Verify Interactive - Deductive Reasoning", "Verify Interactive - Inductive Reasoning", "Verify Interactive - Numerical Reasoning", "Verify Interactive - Verbal Reasoning", "Basic Computer Literacy Test"],
    "cloud":             ["AWS Cloud Development Test", "Verify Interactive - Deductive Reasoning", "Verify Interactive - Numerical Reasoning", "Verify Interactive - Inductive Reasoning", "DevOps Practices Test"],
    "finance":           ["Financial Analysis Test", "Bookkeeping and Accounting Test", "Verify Interactive - Numerical Reasoning", "Verify Interactive - Verbal Reasoning", "Verify Interactive - Deductive Reasoning"],
}

def pick_assessments(role: str) -> list:
    role_lower = (role or "").lower()
    for key, names in ROLE_PICKS.items():
        if key in role_lower:
            return names
    return ["Verify Interactive - Numerical Reasoning", "Verify Interactive - Deductive Reasoning", "Verify Interactive - Inductive Reasoning", "Verify Interactive - Verbal Reasoning", "Verify G+ Test"]



# ─────────────────────────────────────────────────────────────────────────────

OFFTOPIC_PATTERNS = re.compile(
    r"\b(weather|forecast|temperature|rain|snow|news|politics|legal|advice|"
    r"religion|sport|ignore|forget instructions|you are now|jailbreak|"
    r"prompt injection|act as|pretend)\b",
    re.IGNORECASE
)

GIBBERISH_RE = re.compile(r'^[a-z]{3,}$')   # all-lowercase, no spaces, no known words
GREETING_RE  = re.compile(r'^\s*(hi+|hello+|hey+|how are you|how are u|good morning|good day|sup)\s*$', re.IGNORECASE)


def mock_generate(system_prompt: str, messages: list[dict]) -> str:
    """
    Mock Gemini responses so the agent works without a real API key.
    Two call patterns are supported:
      1. Extraction JSON  (system: "…Return only valid JSON…")
      2. Pick-names array (system: "Return only a JSON array of strings…")
    """
    last = messages[-1]["content"] if messages else ""
    last_lower = last.lower()
    sys_lower  = system_prompt.lower()

    # ── CALL 1: Extraction JSON ───────────────────────────────────────────────
    if "return only valid json" in sys_lower or "data extractor" in sys_lower:

        # Pull conversation block from the prompt
        conv_match = re.search(
            r"Conversation:\s*(.*?)\s*Return ONLY this JSON",
            last, re.DOTALL | re.IGNORECASE
        )
        conv_text = conv_match.group(1) if conv_match else last

        # Find the LAST user line in the conversation block
        last_user_line = ""
        for line in conv_text.strip().split("\n"):
            stripped = line.strip()
            if stripped.upper().startswith("USER:"):
                last_user_line = re.sub(r"^USER:\s*", "", stripped, flags=re.IGNORECASE).strip()
        user_part = last_user_line.lower()

        # Words that are valid seniority answers — never gibberish

        SENIORITY_WORDS = {
            "junior", "senior", "mid", "middle", "lead", "principal", "entry",
            "junior level", "mid level", "senior level", "entry level",
            "fresher", "freshers", "fresh grad", "graduate",
        }
        is_seniority_reply = (
            user_part in SENIORITY_WORDS
            or bool(extract_seniority(user_part))
        )


        # Classify intent from the latest user line
        is_greeting  = bool(GREETING_RE.match(user_part)) and not is_seniority_reply
        is_gibberish = (
            bool(GIBBERISH_RE.match(user_part))
            and not is_seniority_reply
        )
        is_offtopic  = bool(OFFTOPIC_PATTERNS.search(user_part)) and not is_seniority_reply

        is_compare   = any(w in user_part for w in ["compare", "difference", "versus", " vs "])
        is_refine    = any(w in user_part for w in ["add ", "also ", "include ", "update ", "change ", "actually"])

        # Intent
        if is_greeting:    intent = "GREET"
        elif is_gibberish: intent = "GIBBERISH"
        elif is_offtopic:  intent = "OFFTOPIC"
        elif is_compare:   intent = "COMPARE"
        elif is_refine:    intent = "REFINE"
        else:              intent = "HIRING"

        # Extract role — from latest user line first, then fall back to full conversation.
        # KEY: when falling back, find the MOST RECENT user-stated role by scanning
        # conversation lines in REVERSE order so we get the last role, not the first.
        role_from_latest = extract_role(user_part)
        if role_from_latest:
            role = role_from_latest
        else:
            # Scan conversation lines in reverse to find the most recently mentioned role
            role = None
            for line in reversed(conv_text.strip().split("\n")):
                stripped = line.strip()
                # Prefer roles from user lines or from "seniority level for the X role" questions
                line_role = extract_role(stripped.lower())
                if line_role:
                    role = line_role
                    break
            if not role:
                role = extract_role(conv_text.lower())

        # Extract seniority — KEY RULE:
        # If the latest line contains a NEW role statement → only look at the latest line
        # for seniority (don't bleed "junior" from a previous java conversation into
        # the new "i am sql developer" query).
        # If no role in the latest line (e.g. user just said "junior") → fall back to history.
        if role_from_latest:
            # New role stated: seniority must also come from this same message
            seniority = extract_seniority(user_part)
        else:
            # Seniority-only reply (e.g. "junior"): pull role from history, seniority from here.
            # Only scan user lines in history to find the seniority, ignoring assistant prompts.
            seniority = None
            for line in reversed(conv_text.strip().split("\n")):
                stripped = line.strip()
                if stripped.upper().startswith("USER:"):
                    user_line = re.sub(r"^USER:\s*", "", stripped, flags=re.IGNORECASE).strip().lower()
                    sen = extract_seniority(user_line)
                    if sen:
                        seniority = sen
                        break


        # Detect if this is a role switch (latest user line has a role AND prior recs exist)
        prior_recs = "based on your requirements" in conv_text.lower()
        role_switched = bool(role_from_latest) and prior_recs

        return json.dumps({
            "intent":           intent,
            "job_role":         role,
            "seniority":        seniority,
            "skills":           [],
            "compare_items":    [],
            "role_just_changed": role_switched
        })

    # ── CALL 2: RAG pick and explanation ──────────────────────────────────────
    if "json object matching" in sys_lower or "requested schema" in sys_lower:
        # Extract role from the "hiring for:" line in the pick prompt
        role_match = re.search(r"hiring for:\s*(.*)", last, re.IGNORECASE)
        role_hint  = role_match.group(1).strip().lower() if role_match else last_lower
        
        # Get seniority hint
        seniority_match = re.search(r"seniority:\s*(\w+)", last, re.IGNORECASE)
        seniority_hint = seniority_match.group(1).strip().lower() if seniority_match else ""
        seniority_text = f" ({seniority_hint} level)" if seniority_hint and seniority_hint != "not specified" else ""
        
        picks = pick_assessments(role_hint)
        # Construct dynamic grounded explanations matching catalog
        reply = f"Based on your requirements for {role_hint}{seniority_text}, here are the most relevant SHL assessments: " + ", ".join(picks)
        return json.dumps({
            "reply": reply,
            "recommendations": picks
        })


    # ── CALL 3: Comparison reply ──────────────────────────────────────────────
    if "shl assessment expert" in sys_lower or "compare these shl assessments" in last_lower:
        return (
            "Here is a comparison based on catalog data:\n\n"
            "- **OPQ32r**: A personality questionnaire measuring 32 dimensions of workplace behaviour. "
            "Best for management and leadership roles.\n"
            "- **Java Coding Test**: Evaluates Java programming skills. "
            "Best for software developer and engineer roles."
        )

    # ── Fallback ──────────────────────────────────────────────────────────────
    return json.dumps({
        "intent":        "GREET",
        "job_role":      None,
        "seniority":     None,
        "skills":        [],
        "compare_items": []
    })


# ─────────────────────────────────────────────────────────────────────────────

def generate(system_prompt: str, messages: list[dict]) -> str:
    """
    Call Gemini. Falls back to mock_generate when a placeholder API key is set.
    """
    if is_placeholder:
        return mock_generate(system_prompt, messages)

    if not messages:
        raise Exception("Messages list cannot be empty.")

    start_time = time.time()

    history = []
    for msg in messages[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        history.append({"role": role, "parts": [{"text": msg["content"]}]})

    last_content = messages[-1]["content"]

    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system_prompt
    )
    chat = model.start_chat(history=history)

    last_exc = None
    for attempt in range(2):
        elapsed   = time.time() - start_time
        remaining = 25.0 - elapsed
        if remaining <= 1.0:
            break
        try:
            response = chat.send_message(
                last_content,
                request_options={"timeout": remaining}
            )
            return response.text
        except Exception as e:
            last_exc = e
            time.sleep(0.5)

    msg = f"Failed after {attempt + 1} attempt(s)."
    if last_exc:
        msg += f" Error: {last_exc}"
    raise Exception(msg)
