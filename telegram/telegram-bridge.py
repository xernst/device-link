#!/usr/bin/env python3
"""
Device-Link Telegram Bridge — Smart chatbot with collaborative dual-brain pipeline.
Keyword routing for brain dispatch. Live progress streaming for collaborations.
"""

import os
import re
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime, time
from functools import wraps
from collections import deque

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# --- Config ---
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
AUTHORIZED_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
RESULTS_DIR = Path.home() / ".device-link" / "results"
TRIGGER_SCRIPT = str(Path.home() / ".device-link" / "trigger" / "trigger.sh")

LEFT_HOST = os.environ.get("DEVICE_LINK_LEFT_HOST", "helper-left")
RIGHT_HOST = os.environ.get("DEVICE_LINK_RIGHT_HOST", "helper-right")
DEFAULT_ROUNDS = int(os.environ.get("DEVICE_LINK_COLLAB_ROUNDS", "2"))
LEDGER_DIR = Path.home() / "Documents" / "second-brain" / "_ledger" / "tasks"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("device-link")

# --- Conversation memory (last 20 exchanges) ---
conversation_history = deque(maxlen=20)

# --- System context ---
SYSTEM_CONTEXT = """You are Josh's AI assistant running on his Device Link swarm — a multi-machine system with 3 Mac laptops connected via Tailscale. You are talking to Josh through Telegram.

## Who You Are
You are the central brain of Device Link, a personal AI command center. You're smart, direct, and capable. You know Josh's setup inside and out. You don't give generic AI answers — you give answers informed by his actual infrastructure and projects.

## Josh's Setup
- **Main Mac**: Orchestrator running OpenClaw gateway, Mission Control dashboard (localhost:3000), and this Telegram bot
- **Left Brain** (helper-left): Analytical engine — code analysis, testing, debugging, security audits, performance benchmarking
- **Right Brain** (helper-right): Creative engine — architecture design, UX, documentation, brainstorming, wireframes
- **Collaboration**: Both brains collaborate iteratively — LEFT proposes, RIGHT critiques and builds, they refine through rounds, then produce a unified result
- Connected via Tailscale VPN, dispatched via trigger.sh scripts
- Results stored in ~/.device-link/results/

## Current Projects
- **AI Screening Assistant**: Cloud-based recruiting tool for Naples/Xwell salon & spa locations. Uses voice AI for 5-10 min phone screens, Slack integration for recruiters, AWS infrastructure (Lambda, Connect/Twilio, DynamoDB, S3). Full architecture plan completed via dual-brain collaboration.
- **Device Link itself**: The multi-machine AI swarm you're running on.

## What You Can Do
- Answer questions directly (you're smart and have context)
- Dispatch tasks to left brain (analytical), right brain (creative), or start a collaboration (both)
- Check swarm status and recent results
- Help with Josh's work projects, coding, planning, and decision-making

## How You Talk
- Direct and concise, no fluff
- Reference Josh's actual setup when relevant
- If a task needs the brains, say so and route it
- If you can answer it yourself, just answer it — don't overthink routing
- Remember what Josh said earlier in the conversation

## Recent Results Summary
{recent_results}
"""


def get_last_activity(brain_name):
    """Get mtime of most recent result file for a brain."""
    patterns = {
        "left": "left-*.md",
        "right": "right-*.md",
        "collab": "collab-*.md",
    }
    pat = patterns.get(brain_name, f"{brain_name}-*.md")
    files = sorted(RESULTS_DIR.glob(pat), key=os.path.getmtime, reverse=True)
    if not files:
        return "\u2014"
    return datetime.fromtimestamp(files[0].stat().st_mtime).strftime("%H:%M")


def parse_ledger_entry(filepath):
    """Parse YAML frontmatter from a ledger task file."""
    try:
        text = Path(filepath).read_text()
    except Exception:
        return None
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    entry = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip().strip('"')
            entry[key.strip()] = val
    return entry if entry else None


def get_overnight_results():
    """Get results from last 24h grouped by brain type."""
    if not RESULTS_DIR.exists():
        return {"left": [], "right": [], "collab": []}
    cutoff = datetime.now().timestamp() - 86400
    grouped = {"left": [], "right": [], "collab": []}
    for f in sorted(RESULTS_DIR.glob("*.md"), key=os.path.getmtime, reverse=True):
        if f.stat().st_mtime < cutoff:
            continue
        # Determine brain from filename
        name = f.stem
        if name.startswith("left-"):
            brain = "left"
        elif name.startswith("right-"):
            brain = "right"
        elif name.startswith("collab-"):
            brain = "collab"
        else:
            continue
        # Extract task name and preview
        try:
            content = f.read_text()
            task_name = ""
            for line in content.split("\n"):
                if line.startswith("## Task:"):
                    task_name = line[8:].strip()[:80]
                    break
            # Get content after the --- header block
            preview = ""
            in_header = False
            for line in content.split("\n"):
                if line.strip() == "---":
                    if in_header:
                        in_header = False
                        continue
                    in_header = True
                    continue
                if not in_header and line.strip() and not line.startswith("#"):
                    preview = line.strip()[:150]
                    break
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%H:%M")
            grouped[brain].append({
                "task": task_name or name,
                "time": mtime,
                "preview": preview,
                "file": f.name,
            })
        except Exception:
            pass
    return grouped


def build_system_context():
    """Build system context with recent results."""
    results = get_recent_results(3)
    result_summaries = []
    for f in results:
        try:
            content = f.read_text()
            preview = content[:200].replace("\n", " ")
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            result_summaries.append(f"- {f.stem} ({mtime}): {preview}...")
        except:
            pass
    recent = "\n".join(result_summaries) if result_summaries else "(no recent results)"
    return SYSTEM_CONTEXT.format(recent_results=recent)


def build_prompt_with_history(user_message):
    """Build prompt including conversation history and system context."""
    system = build_system_context()
    history_lines = []
    for role, msg in conversation_history:
        prefix = "Josh" if role == "user" else "Assistant"
        truncated = msg[:300] + "..." if len(msg) > 300 else msg
        history_lines.append(f"{prefix}: {truncated}")

    parts = [system]
    if history_lines:
        parts.append("\n## Recent Conversation\n" + "\n".join(history_lines[-10:]))
    parts.append(f"\n## Current Message from Josh\n{user_message}")
    parts.append("\nRespond directly and helpfully. Be concise for simple questions, detailed for complex ones.")
    return "\n".join(parts)


# --- Auth ---
def authorized(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != AUTHORIZED_CHAT_ID:
            await update.message.reply_text("Unauthorized.")
            return
        return await func(update, context)
    return wrapper


# --- LLM ---
async def ask_llm(prompt, timeout=90):
    """Ask OpenClaw agent with full context."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "openclaw", "agent", "--agent", "main",
            "--message", prompt, "--timeout", str(timeout), "--json",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout + 15)
        raw = stdout.decode().strip()
        if not raw:
            return "(No response)"
        try:
            data = json.loads(raw)
            text = data.get("result", {}).get("payloads", [{}])[0].get("text", "")
            return text if text else data.get("summary", "(empty)")
        except (json.JSONDecodeError, IndexError, KeyError):
            return raw[:3000]
    except asyncio.TimeoutError:
        return "(Timed out — try a shorter question or dispatch to a brain)"
    except Exception as e:
        return "(Error: " + str(e) + ")"


# --- Task Ledger ---
def log_to_ledger(brain, task, mode, status, result_preview=""):
    """Write a task entry to the second-brain ledger."""
    try:
        LEDGER_DIR.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        ts = now.strftime("%Y%m%d-%H%M%S")
        iso = now.strftime("%Y-%m-%dT%H:%M:%S")
        fname = f"{ts}-{brain}.md"
        preview = result_preview[:300].replace("\n", " ") if result_preview else ""
        entry = (
            f"---\n"
            f"brain: {brain}\n"
            f'task: "{task[:200]}"\n'
            f"mode: {mode}\n"
            f"status: {status}\n"
            f"timestamp: {iso}\n"
            f"tags: [task-log, from/telegram]\n"
            f"---\n\n"
            f"# {brain.capitalize()} Brain \u2014 {task[:100]}\n\n"
            f"**Status**: {status}\n"
            f"**Mode**: {mode}\n"
            f"**Time**: {iso}\n"
        )
        if preview:
            entry += f"\n## Result Preview\n{preview}\n"
        (LEDGER_DIR / fname).write_text(entry)
        logger.info("Ledger: %s -> %s", fname, status)
    except Exception as e:
        logger.error("Ledger write failed: %s", e)


# --- Review Gate ---
async def review_result(brain, task, result_text):
    """Run result through Claude review gate. Returns 2-3 sentence summary flagging issues."""
    if not result_text or len(result_text.strip()) < 50:
        return None
    review_prompt = (
        f"You are reviewing a task result from the {brain} brain of an AI swarm.\n"
        f"Task: {task[:200]}\n\n"
        f"Result (first 1500 chars):\n{result_text[:1500]}\n\n"
        "Give a 2-3 sentence executive summary. Flag any issues, gaps, or concerns. "
        "If the result looks solid, say so briefly. Be direct."
    )
    try:
        review = await ask_llm(review_prompt, timeout=30)
        if review and not review.startswith("("):
            return review
    except Exception:
        pass
    return None


# --- Task dispatch ---
async def dispatch_task(brain, task):
    proc = await asyncio.create_subprocess_exec(
        "bash", TRIGGER_SCRIPT, brain, task,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
        return proc.returncode, stdout.decode(), stderr.decode()
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise


async def ssh_check(host):
    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "ConnectTimeout=3", host, "echo", "ok",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=5)
        return "online" if proc.returncode == 0 else "unreachable"
    except:
        return "offline"


async def deep_health_check(host, brain_name):
    """Run comprehensive health check on a helper. Returns dict of component statuses."""
    health = {"ssh": "offline", "tmux": "?", "ollama": "?", "claude": "?", "disk": "?"}

    # SSH check
    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "ConnectTimeout=3", host, "echo", "ok",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=5)
        if proc.returncode != 0:
            return health
        health["ssh"] = "ok"
    except:
        return health

    # Tmux session
    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "ConnectTimeout=3", host,
            f"tmux has-session -t {brain_name}-brain 2>/dev/null && echo yes || echo no",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        health["tmux"] = "ok" if "yes" in stdout.decode() else "no"
    except:
        health["tmux"] = "?"

    # Ollama
    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "ConnectTimeout=3", host,
            "curl -s http://localhost:11434/api/tags >/dev/null 2>&1 && echo yes || echo no",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        health["ollama"] = "ok" if "yes" in stdout.decode() else "no"
    except:
        health["ollama"] = "?"

    # Claude Code
    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "ConnectTimeout=3", host,
            "command -v claude >/dev/null 2>&1 && echo yes || echo no",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        health["claude"] = "ok" if "yes" in stdout.decode() else "no"
    except:
        health["claude"] = "?"

    # Disk space
    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "ConnectTimeout=3", host,
            "df -h / | tail -1 | awk '{print $4}'",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        health["disk"] = stdout.decode().strip() or "?"
    except:
        health["disk"] = "?"

    return health


def truncate(text, max_len=3000):
    return text if len(text) <= max_len else text[:max_len] + "\n...(truncated)"


def _log_task_error(task):
    """Safe done-callback for asyncio tasks — handles CancelledError."""
    if task.cancelled():
        return
    exc = task.exception()
    if exc:
        logger.error("async task failed: %s", exc)


def get_recent_results(count=5):
    if not RESULTS_DIR.exists():
        return []
    return sorted(RESULTS_DIR.glob("*.md"), key=os.path.getmtime, reverse=True)[:count]


# --- Fast keyword router (NO LLM) ---
LEFT_KEYWORDS = [
    "debug", "test", "fix bug", "analyze code", "security audit",
    "benchmark", "profile", "lint", "code review", "refactor",
    "optimize", "unit test", "integration test",
]
RIGHT_KEYWORDS = [
    "design", "brainstorm", "write doc", "create logo", "ux",
    "mockup", "ideate", "diagram", "wireframe",
]


def classify(text):
    """Instant keyword-based routing. No LLM needed."""
    lower = text.strip().lower()

    # Explicit prefix overrides
    if lower.startswith("left:"):
        return "left", text[5:].strip()
    if lower.startswith("right:"):
        return "right", text[6:].strip()
    if lower.startswith(("both:", "collab:")):
        for prefix in ("both:", "collab:"):
            if lower.startswith(prefix):
                return "collab", text[len(prefix):].strip()
    if lower.startswith("project:"):
        return "project", text[8:].strip()

    # Brain keywords
    for kw in LEFT_KEYWORDS:
        if kw in lower:
            return "left", text
    for kw in RIGHT_KEYWORDS:
        if kw in lower:
            return "right", text

    # Long messages (>300 chars) default to collab — likely a project
    if len(text.strip()) > 300:
        return "collab", text

    # Default: answer locally with full context
    return "local", text


# --- Command handlers ---
@authorized
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Running deep health check...")
    left_h, right_h = await asyncio.gather(
        deep_health_check(LEFT_HOST, "left"),
        deep_health_check(RIGHT_HOST, "right"),
    )

    def format_health(name, h):
        if h["ssh"] == "offline":
            return f"{name}: OFFLINE"
        components = []
        for key in ("ssh", "tmux", "ollama", "claude"):
            icon = "+" if h[key] == "ok" else "-"
            components.append(f"{icon}{key}")
        return f"{name}: {' '.join(components)} | disk: {h['disk']}"

    recent = get_recent_results(5)
    lines = [
        "Swarm Status",
        "=" * 20,
        format_health("Left brain ", left_h),
        format_health("Right brain", right_h),
        "",
        "Recent results (" + str(len(recent)) + "):",
    ]
    for f in recent:
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%H:%M")
        lines.append("  " + f.stem + " (" + mtime + ")")
    if not recent:
        lines.append("  (none)")
    await update.message.reply_text("\n".join(lines))


@authorized
async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the full rich daily brief on demand."""
    await update.message.reply_text("Building brief...")
    try:
        chunks = await build_daily_brief()
        for chunk in chunks:
            await update.message.reply_text(chunk)
    except Exception as e:
        await update.message.reply_text(f"Brief failed: {e}")


@authorized
async def cmd_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    results = get_recent_results(5)
    if not results:
        await update.message.reply_text("No results yet.")
        return
    for f in results:
        content = f.read_text()
        await update.message.reply_text(truncate(f.stem + "\n" + content, 3500))


@authorized
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Device Link\n"
        + "=" * 20 + "\n\n"
        + "Just talk to me. I know your setup.\n\n"
        + "Short questions -> I answer directly\n"
        + "Code tasks -> left brain (analytical)\n"
        + "Design tasks -> right brain (creative)\n"
        + "Big projects -> both brains collaborate\n\n"
        + "Prefixes:\n"
        + "  left: <task>    - analytical work\n"
        + "  right: <task>   - creative work\n"
        + "  both: <task>    - iterative collaboration\n"
        + "  project: <desc> - auto-split across brains\n\n"
        + "Core:\n"
        + "  /status /brief /results /help\n\n"
        + "Left Brain Skills:\n"
        + "  /codereview /tdd /buildfix /verify\n"
        + "  /testcoverage /refactorclean /e2e /securityaudit\n\n"
        + "Right Brain Skills:\n"
        + "  /plan /research /prd /architect\n\n"
        + "Second Brain:\n"
        + "  /inbox    - triage inbox items\n"
        + "  /note     - quick capture to inbox\n"
        + "  /journal  - journal entry\n"
        + "  /digest   - generate task digest\n"
        + "  /connections - find Galaxy links\n\n"
        + "All skills take an argument:\n"
        + "  /plan build user auth system\n"
        + "  /research voice AI APIs for recruiting"
    )


# --- Brain skill commands ---
# Left brain skills: analytical tasks with specific prompts
BRAIN_SKILLS = {
    # Left brain (analytical)
    "codereview": ("left", "Run a comprehensive code review. Check for: security issues (hardcoded creds, SQL injection, XSS, missing validation), code quality (functions >50 lines, deep nesting, missing error handling), and best practices (mutation patterns, missing tests, accessibility). Report with severity, location, and suggested fixes."),
    "tdd": ("left", "Use test-driven development. Write failing tests first, then implement minimal code to pass, then refactor. Follow RED-GREEN-REFACTOR cycle."),
    "buildfix": ("left", "Fix build errors minimally. Identify the root cause, apply the smallest fix possible, verify the build passes."),
    "verify": ("left", "Run all quality checks: tests, type checking, linting. Report pass/fail for each."),
    "testcoverage": ("left", "Analyze test coverage. Identify untested code paths and generate tests for critical gaps."),
    "refactorclean": ("left", "Safe dead code removal and refactoring. Identify unused exports, unreachable code, and redundant logic. Remove safely with verification."),
    "e2e": ("left", "Generate and run end-to-end tests for critical user flows."),
    "securityaudit": ("left", "Security audit: check auth flows, API endpoints, input handling, dependency vulnerabilities, secrets management."),
    # Right brain (creative)
    "plan": ("right", "Create a comprehensive implementation plan. Restate requirements, break into phases, identify dependencies, assess risks, estimate complexity. Present the plan clearly."),
    "research": ("right", "Multi-source research. Search across web, social, and technical sources. Rank by engagement and credibility. Include contrarian evidence. Deliver a decision-oriented brief with: executive summary, key findings, evidence, risks, recommendation, sources."),
    "prd": ("right", "Create a Product Requirements Document. Include: problem statement, user stories, requirements (functional + non-functional), success metrics, constraints, timeline."),
    "architect": ("right", "System architecture design. Consider multiple approaches, document tradeoffs, include data flow diagrams, component designs, scaling strategy, and tech stack recommendations."),
}


@authorized
async def handle_skill_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle brain skill commands like /codereview, /plan, etc."""
    cmd = update.message.text.split()[0].lstrip("/").split("@")[0].lower()
    args = " ".join(context.args) if context.args else ""

    if cmd not in BRAIN_SKILLS:
        await update.message.reply_text(f"Unknown skill: {cmd}")
        return

    brain, skill_prompt = BRAIN_SKILLS[cmd]
    if not args:
        await update.message.reply_text(f"Usage: /{cmd} <target or description>")
        return

    full_task = f"{skill_prompt}\n\nTarget: {args}"
    conversation_history.append(("user", f"/{cmd} {args}"))
    await update.message.reply_text(f"/{cmd} -> {brain} brain: {args[:80]}...")
    t = asyncio.create_task(run_and_notify(update, brain, full_task))
    t.add_done_callback(_log_task_error)


# --- Second Brain commands ---
VAULT_DIR = Path.home() / "Documents" / "second-brain"


@authorized
async def cmd_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process inbox to zero — show items and route them."""
    inbox_dir = VAULT_DIR / "00-inbox"
    if not inbox_dir.exists():
        await update.message.reply_text("Inbox folder not found.")
        return
    files = list(inbox_dir.glob("*.md"))
    if not files:
        await update.message.reply_text("Inbox is empty. Nothing to triage.")
        return
    # List items
    lines = [f"Inbox ({len(files)} items):"]
    for f in files[:20]:
        lines.append(f"  - {f.stem}")
    await update.message.reply_text("\n".join(lines))
    # Ask LLM to suggest routing
    summaries = []
    for f in files[:10]:
        try:
            content = f.read_text()[:200]
            summaries.append(f"- {f.stem}: {content}")
        except:
            pass
    if summaries:
        prompt = (
            "You are triaging an Obsidian inbox. Route each item to the right folder:\n"
            "- 01-projects/ (has deadline)\n- 02-areas/ (ongoing responsibility)\n"
            "- 03-resources/ (reference/SOP)\n- 04-archives/ (done)\n- 05-galaxy/ (atomic concept)\n\n"
            "Items:\n" + "\n".join(summaries) + "\n\n"
            "For each item, say: FILENAME -> FOLDER (one-line reason). Be concise."
        )
        await update.message.reply_text("Analyzing routing...")
        routing = await ask_llm(prompt, timeout=30)
        if routing and not routing.startswith("("):
            await update.message.reply_text(truncate(routing, 4000))


@authorized
async def cmd_connections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Find hidden connections in Galaxy notes."""
    args = " ".join(context.args) if context.args else ""
    galaxy_dir = VAULT_DIR / "05-galaxy"
    if not galaxy_dir.exists():
        await update.message.reply_text("Galaxy folder not found.")
        return
    notes = list(galaxy_dir.glob("*.md"))
    if not notes:
        await update.message.reply_text("Galaxy is empty. Add some notes first.")
        return
    # Read all galaxy notes (they should be atomic/short)
    note_summaries = []
    for f in notes[:30]:
        try:
            content = f.read_text()[:300]
            note_summaries.append(f"### {f.stem}\n{content}")
        except:
            pass
    topic = args if args else "any surprising connections"
    prompt = (
        f"You are analyzing an Obsidian Zettelkasten Galaxy. Find hidden connections about: {topic}\n\n"
        "Notes:\n" + "\n".join(note_summaries) + "\n\n"
        "Find 2-3 non-obvious connections between these ideas. For each:\n"
        "- Which notes connect and why\n- The insight this reveals\n- Suggested new [[wikilink]] to add\n"
        "Be specific and insightful."
    )
    await update.message.reply_text("Searching for connections...")
    result = await ask_llm(prompt, timeout=45)
    if result:
        await update.message.reply_text(truncate(result, 4000))


@authorized
async def cmd_journal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick journal entry — saves to inbox for later routing."""
    args = " ".join(context.args) if context.args else ""
    if not args:
        await update.message.reply_text("Usage: /journal <your thoughts>")
        return
    now = datetime.now()
    fname = now.strftime("%Y-%m-%d") + "-journal.md"
    fpath = VAULT_DIR / "00-inbox" / fname
    fpath.parent.mkdir(parents=True, exist_ok=True)
    entry = (
        f"---\n"
        f"date: {now.strftime('%Y-%m-%d')}\n"
        f"time: {now.strftime('%H:%M')}\n"
        f"tags: [journal, from/telegram]\n"
        f"---\n\n"
        f"# Journal — {now.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"{args}\n"
    )
    # Append if file exists (multiple entries per day)
    if fpath.exists():
        with open(fpath, "a") as f:
            f.write(f"\n---\n\n## {now.strftime('%H:%M')}\n\n{args}\n")
    else:
        fpath.write_text(entry)
    await update.message.reply_text(f"Journaled to inbox: {fname}")


@authorized
async def cmd_digest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate and show today's task digest."""
    await update.message.reply_text("Generating digest...")
    try:
        proc = await asyncio.create_subprocess_exec(
            "bash", str(Path.home() / ".device-link" / "trigger" / "digest.sh"),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        output = stdout.decode().strip()
        if proc.returncode == 0 and output:
            await update.message.reply_text(output)
            # Also show the digest content if it was written
            today = datetime.now().strftime("%Y-%m-%d")
            digest_file = VAULT_DIR / "_ledger" / "daily" / f"{today}.md"
            if digest_file.exists():
                content = digest_file.read_text()
                await update.message.reply_text(truncate(content, 4000))
        else:
            await update.message.reply_text(output or "No tasks to digest today.")
    except Exception as e:
        await update.message.reply_text(f"Digest failed: {e}")


@authorized
async def cmd_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick capture — drop a note into inbox."""
    args = " ".join(context.args) if context.args else ""
    if not args:
        await update.message.reply_text("Usage: /note <title> | <content>")
        return
    # Parse title and content
    if "|" in args:
        title, content = args.split("|", 1)
        title = title.strip()
        content = content.strip()
    else:
        title = args[:50]
        content = args
    # Sanitize filename
    safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-')[:50]
    fname = f"{safe_title}.md"
    fpath = VAULT_DIR / "00-inbox" / fname
    fpath.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    entry = (
        f"---\n"
        f"date: {now.strftime('%Y-%m-%d')}\n"
        f"tags: [from/telegram]\n"
        f"---\n\n"
        f"# {title}\n\n"
        f"{content}\n"
    )
    fpath.write_text(entry)
    await update.message.reply_text(f"Note saved: {fname}")


# --- Main message handler ---
@authorized
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        return

    route, task = classify(text)
    logger.info("Route: %s | %s", route, task[:80])

    # Store user message in history
    conversation_history.append(("user", text))

    if route == "local":
        await update.message.reply_text("...")
        full_prompt = build_prompt_with_history(text)
        response = await ask_llm(full_prompt, timeout=90)
        conversation_history.append(("assistant", response))
        await update.message.reply_text(truncate(response, 4000))

    elif route == "collab":
        t = asyncio.create_task(run_collab_pipeline(update, task, DEFAULT_ROUNDS))
        t.add_done_callback(_log_task_error)

    elif route == "project":
        t = asyncio.create_task(run_project(update, task))
        t.add_done_callback(_log_task_error)

    elif route in ("left", "right"):
        await update.message.reply_text("Sending to " + route + " brain...")
        t = asyncio.create_task(run_and_notify(update, route, task))
        t.add_done_callback(_log_task_error)


async def run_and_notify(update, brain, task):
    try:
        code, stdout, stderr = await dispatch_task(brain, task)
        if code == 0:
            result = truncate(stdout.strip(), 3000) if stdout.strip() else "(no output)"
            # Log to second-brain ledger
            log_to_ledger(brain, task[:200], "pipeline", "completed", stdout.strip()[:300])
            # Review gate — send executive summary before full result
            review = await review_result(brain, task, stdout.strip())
            if review:
                await update.message.reply_text(f"Review ({brain}):\n{review}")
            conversation_history.append(("assistant", f"[{brain} brain]: {result[:200]}"))
            await update.message.reply_text(brain + " brain done:\n" + result)
        else:
            log_to_ledger(brain, task[:200], "pipeline", "failed", stderr.strip()[:300])
            err = truncate(stderr.strip() or stdout.strip(), 2000)
            await update.message.reply_text(brain + " failed (exit " + str(code) + "):\n" + err)
    except asyncio.TimeoutError:
        log_to_ledger(brain, task[:200], "pipeline", "timeout")
        await update.message.reply_text(brain + " timed out: " + task[:100])
    except Exception as e:
        log_to_ledger(brain, task[:200], "pipeline", "error", str(e))
        await update.message.reply_text(brain + " error: " + str(e))


async def run_collab_pipeline(update, task, rounds=2):
    """Run collaborative pipeline with live progress streaming via @@COLLAB markers."""
    COLLAB_WALL_TIMEOUT = 900  # 15 min total wall-clock limit
    try:
        proc = await asyncio.create_subprocess_exec(
            "bash", TRIGGER_SCRIPT, "collab", "--rounds", str(rounds), task,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )

        final_result_path = None
        final_output_lines = []
        import time as _time
        wall_start = _time.monotonic()

        # Read stdout line by line for live progress
        while True:
            # Check wall-clock limit
            elapsed = _time.monotonic() - wall_start
            if elapsed > COLLAB_WALL_TIMEOUT:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass
                raise asyncio.TimeoutError("Wall-clock limit exceeded")

            try:
                line = await asyncio.wait_for(proc.stdout.readline(), timeout=180)
            except asyncio.TimeoutError:
                await update.message.reply_text("(waiting for brain response...)")
                continue

            if not line:
                break

            decoded = line.decode().strip()
            if not decoded:
                continue

            if decoded.startswith("@@COLLAB_STATUS:"):
                status_msg = decoded[len("@@COLLAB_STATUS:"):]
                await update.message.reply_text(status_msg)
            elif decoded.startswith("@@COLLAB_PREVIEW:"):
                preview = decoded[len("@@COLLAB_PREVIEW:"):]
                if preview:
                    await update.message.reply_text("  > " + preview[:200])
            elif decoded.startswith("@@COLLAB_FINAL:"):
                final_result_path = decoded[len("@@COLLAB_FINAL:"):]
            else:
                final_output_lines.append(decoded)

        await proc.wait()

        # Send the final result
        if final_result_path and Path(final_result_path).exists():
            content = Path(final_result_path).read_text()
            # Extract just the main deliverable (before "## Collaboration Log")
            log_marker = content.find("## Collaboration Log")
            if log_marker > 0:
                deliverable = content[:log_marker].strip()
            else:
                deliverable = content

            # Remove YAML frontmatter if present (only strip from start, not mid-content)
            if deliverable.startswith("---"):
                deliverable = deliverable[3:].strip()
                end_marker = deliverable.find("---")
                if end_marker >= 0:
                    deliverable = deliverable[end_marker + 3:].strip()

            if deliverable:
                log_to_ledger("collab", task[:200], "collab", "completed", deliverable[:300])
                await update.message.reply_text("Final Result:")
                chunks = [deliverable[i:i+3500] for i in range(0, len(deliverable), 3500)]
                for chunk in chunks:
                    await update.message.reply_text(chunk)
                conversation_history.append(("assistant", f"[collab result]: {deliverable[:300]}"))
            else:
                await update.message.reply_text("Collaboration complete but result was empty.")
        elif final_output_lines:
            # Fallback: send raw output
            output = "\n".join(final_output_lines)
            if output.strip():
                chunks = [output[i:i+3500] for i in range(0, len(output), 3500)]
                await update.message.reply_text("Collaboration result:")
                for chunk in chunks:
                    await update.message.reply_text(chunk)
                conversation_history.append(("assistant", f"[collab result]: {output[:300]}"))
            else:
                await update.message.reply_text("Collaboration completed but no output captured.")
        else:
            stderr_out = (await asyncio.wait_for(proc.stderr.read(), timeout=10)).decode().strip()
            if stderr_out:
                await update.message.reply_text("Collaboration error:\n" + truncate(stderr_out, 2000))
            else:
                await update.message.reply_text("Collaboration completed with no output.")

    except asyncio.TimeoutError:
        # Kill any orphaned subprocess
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass
        await update.message.reply_text("Collaboration timed out on: " + task[:100])
        # Check for partial results
        try:
            session_dirs = sorted(RESULTS_DIR.glob("collab-*/"), key=os.path.getmtime, reverse=True)
            if session_dirs:
                latest = session_dirs[0]
                round_files = sorted(latest.glob("round-*.md"))
                if round_files:
                    last_round = round_files[-1].read_text()
                    await update.message.reply_text(
                        "Partial result from " + round_files[-1].name + ":\n" + truncate(last_round, 3000)
                    )
        except:
            pass
    except Exception as e:
        await update.message.reply_text("Collaboration error: " + str(e))


# --- Project mode (auto-split across brains) ---
PLANNER_PROMPT = """You are a project planner for a two-brain AI swarm.

LEFT BRAIN is analytical: code, tests, debugging, security, performance, edge cases.
RIGHT BRAIN is creative: architecture, design, UX, documentation, research, multiple approaches.

Given the project below, break it into concrete tasks for each brain. Return ONLY valid JSON:
{
  "summary": "one-line project summary",
  "left": ["task 1", "task 2"],
  "right": ["task 1", "task 2"]
}

Keep each task list to 1-3 items. Tasks should be specific and actionable.

PROJECT: """


async def plan_project(description):
    """Use LLM to break a project into left/right brain tasks."""
    prompt = PLANNER_PROMPT + description[:1000]
    raw = await ask_llm(prompt, timeout=60)
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        plan = json.loads(raw[start:end])
        # Validate types and cap task strings for safety
        left = plan.get("left", [])
        right = plan.get("right", [])
        if not isinstance(left, list):
            left = [str(left)[:500]] if left else []
        if not isinstance(right, list):
            right = [str(right)[:500]] if right else []
        plan["left"] = [str(t)[:500] for t in left[:5]]
        plan["right"] = [str(t)[:500] for t in right[:5]]
        return plan
    raise ValueError(f"Could not parse task plan: {raw[:300]}")


async def run_project(update, description):
    """Orchestrate a full project across both brains with review gate."""
    await update.message.reply_text(f"Planning project: {description[:100]}...\nBreaking into tasks...")
    try:
        plan = await plan_project(description)
    except Exception as e:
        await update.message.reply_text(f"Planning failed: {e}")
        return

    left_tasks = plan.get("left", [])
    right_tasks = plan.get("right", [])
    summary = plan.get("summary", description[:100])

    plan_msg = f"Project: {summary}\n\n"
    if left_tasks:
        plan_msg += "LEFT BRAIN (analytical):\n"
        for i, t in enumerate(left_tasks, 1):
            plan_msg += f"  {i}. {t}\n"
    if right_tasks:
        plan_msg += "\nRIGHT BRAIN (creative):\n"
        for i, t in enumerate(right_tasks, 1):
            plan_msg += f"  {i}. {t}\n"
    plan_msg += f"\nDispatching {len(left_tasks) + len(right_tasks)} tasks..."
    await update.message.reply_text(plan_msg)

    results = []

    async def run_one(brain, task_text):
        try:
            code, stdout, stderr = await dispatch_task(brain, task_text)
            status = "done" if code == 0 else "failed"
            output = stdout.strip()[:500] if code == 0 else (stderr.strip() or stdout.strip())[:500]
            results.append((brain, task_text, status, output))
            # Review gate
            if code == 0:
                review = await review_result(brain, task_text, stdout.strip())
                if review:
                    await update.message.reply_text(f"Review ({brain}): {review}")
            await update.message.reply_text(
                f"{brain} {status}: {task_text[:60]}\n{truncate(output, 1500)}"
            )
        except Exception as e:
            results.append((brain, task_text, "error", str(e)))
            await update.message.reply_text(f"{brain} error: {task_text[:60]}\n{e}")

    await asyncio.gather(*(run_one(b, t) for b, t in
                           [(b, t) for b in ["left"] for t in left_tasks] +
                           [(b, t) for b in ["right"] for t in right_tasks]))

    done = sum(1 for _, _, s, _ in results if s == "done")
    total = len(results)
    conversation_history.append(("assistant", f"[project]: {summary} — {done}/{total} tasks done"))
    await update.message.reply_text(
        f"Project complete: {done}/{total} tasks succeeded.\n"
        f"Use /results to see full output."
    )


# --- Background ---
async def watch_results(app):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    seen = set(f.name for f in RESULTS_DIR.glob("*.md"))
    while True:
        await asyncio.sleep(10)
        try:
            current = set(f.name for f in RESULTS_DIR.glob("*.md"))
            for fname in (current - seen):
                fpath = RESULTS_DIR / fname
                content = fpath.read_text()
                preview = content[:500] + ("..." if len(content) > 500 else "")
                await app.bot.send_message(chat_id=AUTHORIZED_CHAT_ID, text=truncate("New result: " + fname + "\n" + preview, 4000))
            seen = current
        except Exception as e:
            logger.error("Watch error: %s", e)


async def build_daily_brief():
    """Build the full rich daily brief. Returns list of message strings."""
    today = datetime.now().strftime("%Y-%m-%d")
    parts = []

    # 1. Swarm Status
    left_status, right_status = await asyncio.gather(
        ssh_check(LEFT_HOST), ssh_check(RIGHT_HOST)
    )
    left_activity = get_last_activity("left")
    right_activity = get_last_activity("right")

    status_section = (
        f"# Daily Brief \u2014 {today}\n\n"
        "## Swarm Status\n"
        "| Brain | Status | Last Activity |\n"
        "|-------|--------|---------------|\n"
        f"| Left (Analytical) | {left_status.upper()} | {left_activity} |\n"
        f"| Right (Creative) | {right_status.upper()} | {right_activity} |"
    )
    parts.append(status_section)

    # 2. Overnight Results
    results = get_overnight_results()
    results_lines = ["\n## Overnight Results"]
    has_results = False

    for brain, label in [("left", "Left Brain"), ("right", "Right Brain"), ("collab", "Collaborative")]:
        items = results.get(brain, [])
        if items:
            has_results = True
            results_lines.append(f"### {label}")
            for item in items[:5]:
                line = f"- {item['task']} ({item['time']})"
                if item['preview']:
                    line += f": {item['preview']}"
                results_lines.append(line)

    if not has_results:
        results_lines.append("No results in the last 24h.")

    parts.append("\n".join(results_lines))

    # 3. Pending Tasks
    pending_lines = ["\n## Pending Tasks"]
    pending_found = False
    if LEDGER_DIR.exists():
        for f in sorted(LEDGER_DIR.glob("*.md"), key=os.path.getmtime, reverse=True)[:30]:
            entry = parse_ledger_entry(f)
            if entry and entry.get("status") != "completed":
                pending_found = True
                task_preview = entry.get("task", "unknown")[:80]
                brain = entry.get("brain", "?")
                pending_lines.append(f"- [{brain}] {task_preview}")
    if not pending_found:
        pending_lines.append("All clear.")
    parts.append("\n".join(pending_lines))

    # 4. Today's Focus
    try:
        results_summary = ""
        for brain in ("left", "right", "collab"):
            for item in results.get(brain, [])[:2]:
                results_summary += f"- {brain}: {item['task']}\n"
        if results_summary:
            focus_prompt = (
                "Based on these recent completed tasks from Josh's AI swarm:\n"
                + results_summary
                + "\nSuggest 2-3 concrete priorities for today in 2-3 short bullet points. "
                "Be specific and actionable. No fluff."
            )
            focus = await ask_llm(focus_prompt, timeout=30)
            if focus and not focus.startswith("("):
                parts.append("\n## Today's Focus\n" + focus)
            else:
                parts.append("\n## Today's Focus\n(Focus suggestions unavailable)")
        else:
            parts.append("\n## Today's Focus\nNo recent work to base suggestions on. Fresh start!")
    except Exception:
        parts.append("\n## Today's Focus\n(Focus suggestions unavailable)")

    # 5. Quick Actions
    parts.append(
        "\n## Quick Actions\n"
        "- `left: <task>` \u2014 analytical work\n"
        "- `right: <task>` \u2014 creative work\n"
        "- `both: <task>` \u2014 collaborative pipeline\n"
        "- /status \u2014 check swarm health\n"
        "- /results \u2014 show recent outputs"
    )

    # Join and chunk for Telegram (4096 char limit)
    full_text = "\n".join(parts)
    if len(full_text) <= 4000:
        return [full_text]
    return [full_text[i:i+4000] for i in range(0, len(full_text), 4000)]


async def scheduled_brief(context: ContextTypes.DEFAULT_TYPE):
    """Send full rich daily brief at 8 AM."""
    try:
        chunks = await build_daily_brief()
        for chunk in chunks:
            await context.bot.send_message(chat_id=AUTHORIZED_CHAT_ID, text=chunk)
    except Exception as e:
        logger.error("Scheduled brief failed: %s", e)
        today = datetime.now().strftime("%Y-%m-%d")
        await context.bot.send_message(
            chat_id=AUTHORIZED_CHAT_ID,
            text=f"Daily Brief \u2014 {today}\n(Brief generation failed: {e})\nUse /status to check manually."
        )


# --- Main ---
def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("brief", cmd_brief))
    app.add_handler(CommandHandler("results", cmd_results))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("start", cmd_help))

    # Brain skill commands
    for skill_name in BRAIN_SKILLS:
        app.add_handler(CommandHandler(skill_name, handle_skill_command))

    # Second brain commands
    app.add_handler(CommandHandler("inbox", cmd_inbox))
    app.add_handler(CommandHandler("connections", cmd_connections))
    app.add_handler(CommandHandler("journal", cmd_journal))
    app.add_handler(CommandHandler("digest", cmd_digest))
    app.add_handler(CommandHandler("note", cmd_note))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    if app.job_queue:
        app.job_queue.run_daily(scheduled_brief, time=time(hour=8, minute=0))

    logger.info("Device-Link bridge starting (collab mode)...")
    logger.info("Chat: %d | Rounds: %d | Left: %s | Right: %s",
                AUTHORIZED_CHAT_ID, DEFAULT_ROUNDS, LEFT_HOST, RIGHT_HOST)

    async def post_init(application):
        t = asyncio.create_task(watch_results(application))
        t.add_done_callback(_log_task_error)

    app.post_init = post_init
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
