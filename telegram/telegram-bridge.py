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
import sqlite3
from pathlib import Path
from datetime import datetime, time
from functools import wraps
from collections import deque

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
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
MEMORY_DIR = Path.home() / ".device-link" / "memory"
MAILBOX_DIR = Path.home() / ".device-link" / "mailbox"
SKILLS_DIR = Path.home() / ".device-link" / "skills"
VAULT_DIR = Path.home() / "Documents" / "second-brain"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("device-link")

# --- Persistent Memory (SQLite FTS5) ---
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
MAILBOX_DIR.mkdir(parents=True, exist_ok=True)
SKILLS_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_DB = MEMORY_DIR / "conversations.db"


def init_memory_db():
    """Initialize SQLite database with FTS5 for conversation search."""
    conn = sqlite3.connect(str(MEMORY_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            session_id TEXT,
            route TEXT
        )
    """)
    # FTS5 virtual table for full-text search
    try:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
            USING fts5(content, role, timestamp, content='messages', content_rowid='id')
        """)
        # Triggers to keep FTS in sync
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
                INSERT INTO messages_fts(rowid, content, role, timestamp)
                VALUES (new.id, new.content, new.role, new.timestamp);
            END
        """)
    except sqlite3.OperationalError:
        pass  # FTS5 not available, fall back to LIKE
    conn.commit()
    conn.close()


init_memory_db()
SESSION_ID = datetime.now().strftime("%Y%m%d-%H%M%S")


def save_message(role, content, route=None):
    """Persist a message to the memory database."""
    try:
        conn = sqlite3.connect(str(MEMORY_DB))
        conn.execute(
            "INSERT INTO messages (role, content, timestamp, session_id, route) VALUES (?, ?, ?, ?, ?)",
            (role, content[:5000], datetime.now().isoformat(), SESSION_ID, route or ""),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("Memory save failed: %s", e)


def search_memory(query, limit=5):
    """Search past conversations using FTS5 or LIKE fallback."""
    try:
        conn = sqlite3.connect(str(MEMORY_DB))
        # Try FTS5 first
        try:
            rows = conn.execute(
                "SELECT m.role, m.content, m.timestamp FROM messages m "
                "JOIN messages_fts f ON m.id = f.rowid "
                "WHERE messages_fts MATCH ? ORDER BY rank LIMIT ?",
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            # LIKE fallback
            rows = conn.execute(
                "SELECT role, content, timestamp FROM messages "
                "WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error("Memory search failed: %s", e)
        return []


def get_recent_memory(limit=10):
    """Get recent messages from memory DB (supplements in-memory deque)."""
    try:
        conn = sqlite3.connect(str(MEMORY_DB))
        rows = conn.execute(
            "SELECT role, content, timestamp FROM messages ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return list(reversed(rows))  # chronological order
    except Exception:
        return []


# --- Inter-Agent Mailbox ---
def send_mail(from_brain, to_brain, message):
    """Send a message from one brain to another via file-based mailbox."""
    mailfile = MAILBOX_DIR / f"{from_brain}-to-{to_brain}.md"
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"\n## [{timestamp}] From {from_brain}\n{message}\n"
    with open(mailfile, "a") as f:
        f.write(entry)


def read_mail(brain):
    """Read all messages addressed to a brain."""
    messages = []
    for f in MAILBOX_DIR.glob(f"*-to-{brain}.md"):
        content = f.read_text().strip()
        if content:
            sender = f.stem.split("-to-")[0]
            messages.append({"from": sender, "content": content})
    return messages


def clear_mail(brain):
    """Clear mailbox for a brain after reading."""
    for f in MAILBOX_DIR.glob(f"*-to-{brain}.md"):
        f.write_text("")


# --- Self-Installing Skills ---
def load_custom_skills():
    """Load user-created skills from ~/.device-link/skills/."""
    skills = {}
    for f in SKILLS_DIR.glob("*.md"):
        try:
            content = f.read_text()
            name = f.stem
            # Parse frontmatter
            brain = "left"  # default
            trigger = name
            description = ""
            if content.startswith("---"):
                end = content.find("---", 3)
                if end > 0:
                    header = content[3:end]
                    for line in header.strip().split("\n"):
                        if line.startswith("brain:"):
                            brain = line.split(":")[1].strip()
                        elif line.startswith("trigger:"):
                            trigger = line.split(":")[1].strip()
                        elif line.startswith("description:"):
                            description = line.split(":", 1)[1].strip()
                    content = content[end + 3:].strip()
            skills[name] = {
                "brain": brain,
                "trigger": trigger,
                "description": description,
                "prompt": content,
            }
        except Exception as e:
            logger.error("Failed to load skill %s: %s", f.name, e)
    return skills


CUSTOM_SKILLS = load_custom_skills()


# --- In-memory conversation buffer ---
conversation_history = deque(maxlen=50)


def restore_conversation_history():
    """On startup, reload last session context from memory flush + recent DB messages."""
    restored = 0

    # 1. Try the memory flush snapshot first (has conversation flow)
    flush_file = MEMORY_DIR / "last-session-context.md"
    if flush_file.exists():
        try:
            text = flush_file.read_text()
            # Skip YAML frontmatter
            if text.startswith("---"):
                end = text.find("---", 3)
                if end > 0:
                    text = text[end + 3:].strip()
            # Skip the markdown header
            if text.startswith("# Session Context Snapshot"):
                text = text[len("# Session Context Snapshot"):].strip()
            # Parse "role: message" lines
            for line in text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("user: "):
                    conversation_history.append(("user", line[6:]))
                    restored += 1
                elif line.startswith("assistant: "):
                    conversation_history.append(("assistant", line[11:]))
                    restored += 1
                elif line.startswith("[Fetched Content]: "):
                    conversation_history.append(("system", line[19:]))
                    restored += 1
        except Exception as e:
            logger.error("Failed to restore from flush file: %s", e)

    # 2. Also pull recent messages from SQLite (catches anything after last flush)
    try:
        recent = get_recent_memory(limit=15)
        for role, content, ts in recent:
            # Don't duplicate entries already restored from flush
            entry = (role, content[:500])
            already = False
            for existing_role, existing_msg in conversation_history:
                if existing_role == role and content[:100] in existing_msg:
                    already = True
                    break
            if not already:
                conversation_history.append((role, content[:500]))
                restored += 1
    except Exception:
        pass

    if restored:
        logger.info("Restored %d messages into conversation history from previous session", restored)


restore_conversation_history()

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
- Search the web for anything — competitors, tools, APIs, articles, tweets, reddit posts
- Dispatch tasks to left brain (analytical), right brain (creative), or start a collaboration (both)
- Check swarm status and recent results
- Help with Josh's work projects, coding, planning, and decision-making

## How You Talk
- Direct and concise, no fluff
- Reference Josh's actual setup when relevant
- If a task needs the brains, say so and route it
- If you can answer it yourself, just answer it — don't overthink routing
- Remember what Josh said earlier in the conversation — USE THE CONVERSATION HISTORY
- NEVER say "I can't search the internet" — you CAN search. Just do it.
- NEVER say "I can't access" a URL or tweet — the system handles URL fetching for you
- If Josh references "the tweet", "that link", "the article", etc — look in conversation history for the URL and its content
- If Josh asks you to find, search, look up, or compare anything online — search for it
- Be proactive — if a question would benefit from a web search, do the search
- When Josh asks you to CREATE, WRITE, BUILD, or DRAFT something — DO IT. Produce the actual content (survey, document, email, plan, etc.) directly in your response. Don't ask clarifying questions unless truly necessary. Just make it and let Josh iterate.
- You have FULL CONTEXT of everything Josh has said in this session. Use it.

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
    """Build prompt with conversation history, persistent memory, and system context."""
    system = build_system_context()

    # In-memory recent conversation (fast) — send last 20 entries with generous truncation
    history_lines = []
    for role, msg in conversation_history:
        if role == "system":
            # Include fetched content but keep it concise
            prefix = "[Fetched Content]"
            truncated = msg[:800] + "..." if len(msg) > 800 else msg
        elif role == "user":
            prefix = "Josh"
            truncated = msg[:500] + "..." if len(msg) > 500 else msg
        else:
            prefix = "Assistant"
            truncated = msg[:500] + "..." if len(msg) > 500 else msg
        history_lines.append(f"{prefix}: {truncated}")

    # Search persistent memory for relevant past context
    memory_context = ""
    try:
        # Search for messages related to current query
        keywords = " ".join(user_message.split()[:8])  # first 8 words
        memories = search_memory(keywords, limit=3)
        if memories:
            mem_lines = []
            for role, content, ts in memories:
                date_str = ts[:10] if ts else ""
                prefix = "Josh" if role == "user" else "Bot"
                mem_lines.append(f"[{date_str}] {prefix}: {content[:200]}")
            memory_context = "\n## Relevant Past Conversations\n" + "\n".join(mem_lines)
    except Exception:
        pass

    # Custom skills context
    skills_context = ""
    if CUSTOM_SKILLS:
        skill_list = ", ".join(f"/{k}" for k in CUSTOM_SKILLS)
        skills_context = f"\n## Custom Skills Available\n{skill_list}"

    # Mailbox context
    mail_context = ""
    mail = read_mail("main")
    if mail:
        mail_lines = [f"From {m['from']}:\n{m['content'][:200]}" for m in mail[:3]]
        mail_context = "\n## Unread Messages from Brains\n" + "\n---\n".join(mail_lines)

    parts = [system]
    if memory_context:
        parts.append(memory_context)
    if skills_context:
        parts.append(skills_context)
    if mail_context:
        parts.append(mail_context)
    if history_lines:
        parts.append("\n## Recent Conversation\n" + "\n".join(history_lines[-20:]))
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
async def ask_llm(prompt, timeout=90, retries=1):
    """Ask OpenClaw agent with full context. Retries once on failure."""
    last_error = None
    for attempt in range(retries + 1):
        try:
            proc = await asyncio.create_subprocess_exec(
                "openclaw", "agent", "--agent", "main",
                "--message", prompt, "--timeout", str(timeout), "--json",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout + 15)
            raw = stdout.decode().strip()
            if not raw:
                if attempt < retries:
                    await asyncio.sleep(2)
                    continue
                return "(No response)"
            try:
                data = json.loads(raw)
                text = data.get("result", {}).get("payloads", [{}])[0].get("text", "")
                return text if text else data.get("summary", "(empty)")
            except (json.JSONDecodeError, IndexError, KeyError):
                return raw[:3000]
        except asyncio.TimeoutError:
            last_error = "Timed out"
            if attempt < retries:
                await asyncio.sleep(2)
                continue
            return "(Timed out — try a shorter question or dispatch to a brain)"
        except Exception as e:
            last_error = str(e)
            if attempt < retries:
                await asyncio.sleep(2)
                continue
            return f"(Error: {e})"
    return f"(Failed after {retries + 1} attempts: {last_error})"


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


# --- Mission Control Sync ---
MC_DB_PATH = Path.home() / ".device-link" / "mission-control" / ".data" / "mission-control.db"

BRAIN_AGENT_MAP = {
    "left": {"name": "Left Brain", "role": "developer"},
    "right": {"name": "Right Brain", "role": "designer"},
    "collab": {"name": "Left Brain", "role": "developer"},  # collab uses left as primary
    "main": {"name": "Main (Orchestrator)", "role": "orchestrator"},
}


def mc_ensure_agents():
    """Ensure the 3 swarm agents exist in Mission Control DB."""
    if not MC_DB_PATH.exists():
        return
    try:
        conn = sqlite3.connect(str(MC_DB_PATH))
        now = int(datetime.now().timestamp())
        agents = [
            (1, "Main (Orchestrator)", "orchestrator", "busy", now, "Running Telegram bot", 1),
            (2, "Left Brain", "developer", "idle", now, "Awaiting tasks", 1),
            (3, "Right Brain", "designer", "idle", now, "Awaiting tasks", 1),
        ]
        for a in agents:
            conn.execute(
                "INSERT OR IGNORE INTO agents (id, name, role, status, last_seen, last_activity, workspace_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)", a
            )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("MC ensure_agents failed: %s", e)


def mc_update_agent(brain, status, activity=""):
    """Update an agent's status in Mission Control."""
    if not MC_DB_PATH.exists():
        return
    try:
        info = BRAIN_AGENT_MAP.get(brain, BRAIN_AGENT_MAP["main"])
        conn = sqlite3.connect(str(MC_DB_PATH))
        now = int(datetime.now().timestamp())
        conn.execute(
            "UPDATE agents SET status = ?, last_seen = ?, last_activity = ?, updated_at = ? "
            "WHERE name = ? AND workspace_id = 1",
            (status, now, activity[:200], now, info["name"])
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("MC update_agent failed: %s", e)


def mc_create_task(brain, task_title, task_description="", priority="medium"):
    """Create a task in Mission Control. Returns task_id or None."""
    if not MC_DB_PATH.exists():
        return None
    try:
        info = BRAIN_AGENT_MAP.get(brain, BRAIN_AGENT_MAP["main"])
        conn = sqlite3.connect(str(MC_DB_PATH))
        now = int(datetime.now().timestamp())

        # Get next ticket number
        row = conn.execute("SELECT ticket_counter FROM projects WHERE id = 1 AND workspace_id = 1").fetchone()
        ticket_no = (row[0] + 1) if row else 1
        conn.execute("UPDATE projects SET ticket_counter = ?, updated_at = ? WHERE id = 1 AND workspace_id = 1",
                      (ticket_no, now))

        conn.execute(
            "INSERT INTO tasks (title, description, status, priority, project_id, project_ticket_no, "
            "assigned_to, created_by, created_at, updated_at, tags, metadata, workspace_id) "
            "VALUES (?, ?, 'in_progress', ?, 1, ?, ?, 'josh', ?, ?, ?, '{}', 1)",
            (
                task_title[:200],
                task_description[:2000],
                priority,
                ticket_no,
                info["name"],
                now, now,
                json.dumps([brain, "telegram-dispatch"]),
            )
        )
        task_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()
        logger.info("MC task created: #%d [%s] %s", task_id, brain, task_title[:60])
        return task_id
    except Exception as e:
        logger.error("MC create_task failed: %s", e)
        return None


def mc_update_task(task_id, status, outcome="", result_preview=""):
    """Update a task status in Mission Control."""
    if not MC_DB_PATH.exists() or not task_id:
        return
    try:
        conn = sqlite3.connect(str(MC_DB_PATH))
        now = int(datetime.now().timestamp())
        completed_at = now if status == "done" else None
        conn.execute(
            "UPDATE tasks SET status = ?, outcome = ?, updated_at = ?, completed_at = COALESCE(?, completed_at) "
            "WHERE id = ? AND workspace_id = 1",
            (status, (outcome or result_preview)[:2000], now, completed_at, task_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("MC update_task failed: %s", e)


# Initialize MC agents on startup
mc_ensure_agents()


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


def html_escape(text):
    """Escape HTML special characters for Telegram HTML parse mode."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def send_typing(update):
    """Send typing indicator to show the bot is working."""
    try:
        await update.effective_chat.send_action(ChatAction.TYPING)
    except Exception:
        pass


async def reply_html(update_or_msg, text, **kwargs):
    """Send a message with HTML parse mode, falling back to plain text on error."""
    msg = update_or_msg.message if hasattr(update_or_msg, 'message') else update_or_msg
    try:
        return await msg.reply_text(text, parse_mode=ParseMode.HTML, **kwargs)
    except Exception:
        # Strip HTML tags and send plain
        import re as _re
        plain = _re.sub(r'<[^>]+>', '', text)
        return await msg.reply_text(plain, **kwargs)


async def edit_or_reply(msg, text, **kwargs):
    """Edit an existing message or send a new one if edit fails."""
    try:
        return await msg.edit_text(text, parse_mode=ParseMode.HTML, **kwargs)
    except Exception:
        try:
            return await msg.edit_text(text, **kwargs)
        except Exception:
            return msg


def build_quick_actions_keyboard(include_search=False):
    """Build inline keyboard with contextual quick actions."""
    buttons = [
        [
            InlineKeyboardButton("📊 Status", callback_data="action_status"),
            InlineKeyboardButton("📋 Brief", callback_data="action_brief"),
            InlineKeyboardButton("📁 Results", callback_data="action_results"),
        ],
    ]
    if include_search:
        buttons.append([
            InlineKeyboardButton("🔍 Search more", callback_data="action_search_more"),
        ])
    return InlineKeyboardMarkup(buttons)


def build_dispatch_keyboard(task_preview):
    """Build keyboard for dispatching a task to brains."""
    task_short = task_preview[:60]
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🧠 Left Brain", callback_data=f"dispatch_left"),
            InlineKeyboardButton("🎨 Right Brain", callback_data=f"dispatch_right"),
        ],
        [
            InlineKeyboardButton("🤝 Both Brains", callback_data=f"dispatch_collab"),
        ],
    ])


def get_recent_results(count=5):
    if not RESULTS_DIR.exists():
        return []
    return sorted(RESULTS_DIR.glob("*.md"), key=os.path.getmtime, reverse=True)[:count]


# --- URL Detection & Fetching ---
URL_PATTERN = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE)


def extract_urls(text):
    """Extract all URLs from a message."""
    return URL_PATTERN.findall(text)


def is_twitter_url(url):
    """Check if a URL is from Twitter/X."""
    return bool(re.match(r'https?://(www\.)?(twitter\.com|x\.com)/', url))


def get_tweet_id(url):
    """Extract tweet/status ID from a Twitter/X URL."""
    m = re.search(r'/status/(\d+)', url)
    return m.group(1) if m else None


async def fetch_tweet(url, max_chars=8000):
    """Fetch tweet content using fxtwitter.com API. Returns (text, title) or (None, error)."""
    import aiohttp
    tweet_id = get_tweet_id(url)
    if not tweet_id:
        return None, "Could not extract tweet ID"

    # Try fxtwitter API (returns JSON with tweet content)
    # Extract user from URL
    m = re.search(r'(?:twitter\.com|x\.com)/([^/]+)/status/', url)
    user = m.group(1) if m else "i"
    fx_url = f"https://api.fxtwitter.com/{user}/status/{tweet_id}"

    headers = {"User-Agent": "Device-Link Bot/1.0"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(fx_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    tweet = data.get("tweet", {})
                    author_name = tweet.get("author", {}).get("name", user)
                    author_handle = tweet.get("author", {}).get("screen_name", user)
                    text = tweet.get("text", "")
                    created = tweet.get("created_at", "")
                    likes = tweet.get("likes", 0)
                    retweets = tweet.get("retweets", 0)
                    replies = tweet.get("replies", 0)
                    # Handle Twitter articles (long-form content in blocks)
                    article = tweet.get("article", {})
                    article_text = ""
                    if article:
                        article_title = article.get("title", "")
                        content_obj = article.get("content", {})
                        blocks = content_obj.get("blocks", []) if isinstance(content_obj, dict) else []
                        if blocks:
                            alines = []
                            if article_title:
                                alines.append(f"# {article_title}\n")
                            for b in blocks:
                                btype = b.get("type", "")
                                btext = b.get("text", "")
                                if btype.startswith("header"):
                                    alines.append(f"\n## {btext}")
                                elif btype == "unordered-list-item":
                                    alines.append(f"- {btext}")
                                elif btype == "ordered-list-item":
                                    alines.append(f"• {btext}")
                                elif btype == "blockquote":
                                    alines.append(f"> {btext}")
                                else:
                                    alines.append(btext)
                            article_text = "\n".join(alines)

                    # Check for quote tweet
                    quote = tweet.get("quote", {})
                    quote_text = ""
                    if quote:
                        qt_author = quote.get("author", {}).get("name", "?")
                        qt_text = quote.get("text", "")
                        quote_text = f"\n\n[Quote tweet from {qt_author}]: {qt_text}"
                    # Check for media
                    media = tweet.get("media", {})
                    media_text = ""
                    if media and media.get("all"):
                        for m_item in media["all"][:3]:
                            m_type = m_item.get("type", "")
                            if m_type == "photo":
                                media_text += "\n[📷 Photo attached]"
                            elif m_type == "video":
                                media_text += "\n[🎬 Video attached]"
                    # Build output — prefer article content over tweet text
                    main_content = article_text if article_text else text
                    content = (
                        f"@{author_handle} ({author_name}):\n\n"
                        f"{main_content}"
                        f"{quote_text}"
                        f"{media_text}\n\n"
                        f"❤️ {likes:,} | 🔄 {retweets:,} | 💬 {replies:,}\n"
                        f"Posted: {created}"
                    )
                    title = f"{'Article' if article_text else 'Tweet'} by @{author_handle}"
                    return content[:max_chars], title
                else:
                    return None, f"fxtwitter returned HTTP {resp.status}"
    except asyncio.TimeoutError:
        return None, "Timeout fetching tweet"
    except Exception as e:
        return None, f"Tweet fetch error: {str(e)[:100]}"


async def fetch_url(url, max_chars=8000):
    """Fetch a URL and extract readable text. Returns (text, title) or (None, error)."""
    import aiohttp
    from bs4 import BeautifulSoup

    # Special handling for Twitter/X
    if is_twitter_url(url):
        return await fetch_tweet(url, max_chars)

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15), allow_redirects=True) as resp:
                if resp.status != 200:
                    return None, f"HTTP {resp.status}"
                content_type = resp.headers.get("Content-Type", "")
                if "text/html" not in content_type and "application/json" not in content_type:
                    return None, f"Non-HTML content: {content_type[:50]}"
                html = await resp.text(errors="replace")
    except asyncio.TimeoutError:
        return None, "Timeout fetching URL"
    except Exception as e:
        return None, str(e)[:200]

    # Parse HTML
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Remove script, style, nav, footer, header noise
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        # Try article/main content first
        main = soup.find("article") or soup.find("main") or soup.find(role="main")
        if main:
            text = main.get_text(separator="\n", strip=True)
        else:
            # Fall back to body
            body = soup.find("body")
            text = body.get_text(separator="\n", strip=True) if body else soup.get_text(separator="\n", strip=True)

        # Clean up: collapse whitespace, remove blank lines
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)

        # Truncate
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...(truncated)"

        if len(text) < 50:
            return None, "Page had no readable content"

        return text, title

    except Exception as e:
        return None, f"Parse error: {str(e)[:100]}"


async def fetch_and_analyze_url(url, user_message, update):
    """Fetch a URL, extract content, and have LLM analyze it with conversation context."""
    await send_typing(update)
    placeholder = await reply_html(update, f"🔗 <b>Fetching:</b> <code>{html_escape(url[:80])}</code>...")

    content, title_or_error = await fetch_url(url)

    if content is None:
        # Fetch failed — fall back to web search about the URL
        logger.info("URL fetch failed (%s), falling back to search: %s", title_or_error, url[:80])
        await edit_or_reply(placeholder, f"⚠️ Couldn't fetch page ({title_or_error}). Searching for context...")
        # Search for the URL or related content
        t = asyncio.create_task(search_and_summarize(url, update, raw_query=True))
        t.add_done_callback(_log_task_error)
        return

    # Store the raw fetched content in conversation history so the bot can reference it later
    content_entry = f"[FETCHED URL: {url}]\nTitle: {title_or_error}\nContent:\n{content[:2000]}"
    conversation_history.append(("system", content_entry))
    save_message("system", content_entry, route="url_content")

    await edit_or_reply(placeholder, f"📄 <b>{html_escape(title_or_error[:80])}</b>\n\nAnalyzing content...")
    await send_typing(update)

    # Build context from conversation
    recent = []
    for role, msg in list(conversation_history)[-10:]:
        if role == "system":
            continue  # Don't include raw content dumps in the summary
        recent.append(f"{role}: {msg[:300]}")
    conv_context = "\n".join(recent) if recent else ""

    # Strip the URL from user message to get any additional instructions
    user_text_without_url = user_message.replace(url, "").strip()
    instruction = user_text_without_url if len(user_text_without_url) > 3 else "Summarize the key points and explain how this is relevant."

    analysis_prompt = (
        f"Josh shared a URL: {url}\n"
        f"Page title: {title_or_error}\n\n"
    )
    if conv_context:
        analysis_prompt += f"Recent conversation context:\n{conv_context}\n\n"
    if user_text_without_url and len(user_text_without_url) > 3:
        analysis_prompt += f"Josh's note about this link: {user_text_without_url[:500]}\n\n"
    analysis_prompt += (
        f"Page content:\n{content[:6000]}\n\n"
        "Based on the ACTUAL page content above (which you CAN see — it was fetched for you):\n"
        "1. Summarize the key points (3-5 bullets)\n"
        "2. Extract any specific tools, products, or techniques mentioned\n"
        "3. Note how this relates to Josh's projects (Device Link AI swarm, AI recruiting screener)\n"
        "4. Flag any actionable ideas or things worth trying\n"
        "Be direct and specific — reference actual content from the page. Do NOT say you cannot access the content."
    )

    response = await ask_llm(analysis_prompt, timeout=60, retries=1)

    if response and not response.startswith("("):
        # Store a richer summary so follow-up questions can reference it
        conversation_history.append(("assistant", f"[Analysis of {url}]\n{response[:500]}"))
        save_message("assistant", f"[url: {url}]\n{response}", route="url")
        await reply_html(
            update, truncate(response, 4000),
            reply_markup=build_quick_actions_keyboard(include_search=True),
        )
    else:
        await update.message.reply_text(f"Couldn't analyze the page. Response: {response[:200]}")


# --- Web search ---
async def web_search(query, max_results=5):
    """Search the web using DuckDuckGo. Returns list of {title, href, body}."""
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        loop = asyncio.get_event_loop()
        def _search():
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))
        results = await loop.run_in_executor(None, _search)
        return results
    except Exception as e:
        logger.error("Web search failed: %s", e)
        return []


async def extract_search_query(user_message):
    """Use LLM + conversation history to turn a natural message into a good search query."""
    # Build context from recent conversation
    recent = []
    for role, msg in list(conversation_history)[-8:]:
        recent.append(f"{role}: {msg[:200]}")
    context = "\n".join(recent) if recent else "(no prior context)"

    prompt = (
        "You are a search query optimizer. The user is Josh, working on an AI recruiting screening "
        "assistant for salon/spa locations in Naples. He uses a multi-Mac AI swarm called Device Link.\n\n"
        "Given his message and recent conversation, extract 1-3 focused web search queries.\n\n"
        "Rules:\n"
        "- Return ONLY the search queries, one per line\n"
        "- If they mention twitter/X, add site:x.com to one query\n"
        "- If they mention reddit, add site:reddit.com to one query\n"
        "- Use conversation context to understand WHAT they're searching about\n"
        "- Strip filler words like 'search for', 'look up', 'find me'\n"
        "- Make queries specific and likely to return useful results\n"
        "- If the message is vague (like 'similar use cases'), use context to make it specific\n\n"
        f"Recent conversation:\n{context}\n\n"
        f"User message: {user_message[:300]}\n\n"
        "Search queries (one per line):"
    )
    try:
        raw = await ask_llm(prompt, timeout=20)
        # Clean up — get all query lines
        lines = [l.strip().strip('"').strip("'").lstrip("0123456789.-) ")
                 for l in raw.strip().split("\n") if l.strip()]
        # Filter out meta-text
        queries = [l for l in lines if len(l) > 5 and not l.lower().startswith(("search quer", "here", "note:"))]
        return queries[:3] if queries else [user_message]
    except Exception:
        return [user_message]


async def search_and_summarize(query, update, raw_query=False):
    """Search the web, then summarize results with LLM. Uses multi-query when needed."""
    await send_typing(update)

    # Extract proper search queries unless already refined
    if not raw_query:
        queries = await extract_search_query(query)
    else:
        queries = [query]

    # Run searches across all queries
    all_results = []
    search_status = []
    for q in queries[:3]:  # max 3 queries
        search_status.append(q)
        await reply_html(update, f"🔍 <code>{html_escape(q)}</code>")
        await send_typing(update)
        results = await web_search(q, max_results=5)
        all_results.extend(results)

    # Deduplicate by URL
    seen_urls = set()
    unique_results = []
    for r in all_results:
        url = r.get("href", "")
        if url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(r)

    if not unique_results:
        await update.message.reply_text("No results found. Try different keywords.")
        return

    # Format results for LLM
    formatted = []
    for i, r in enumerate(unique_results[:10], 1):
        title = r.get("title", "")
        url = r.get("href", "")
        snippet = r.get("body", "")
        formatted.append(f"{i}. {title}\n   {url}\n   {snippet}")

    results_text = "\n\n".join(formatted)

    # Build context from conversation
    recent = []
    for role, msg in list(conversation_history)[-8:]:
        if role != "system":
            recent.append(f"{role}: {msg[:300]}")
    conv_context = "\n".join(recent) if recent else ""

    await send_typing(update)

    # Have LLM analyze and summarize results with full context
    summary_prompt = (
        f"The user (Josh) asked: {query[:300]}\n"
        f"Queries searched: {', '.join(queries[:3])}\n\n"
        "Josh is building an AI recruiting screening assistant for salon/spa businesses. "
        "He's looking for relevant tools, competitors, approaches, and use cases.\n\n"
    )
    if conv_context:
        summary_prompt += f"Conversation context:\n{conv_context}\n\n"
    summary_prompt += (
        f"Web search results:\n{results_text[:3000]}\n\n"
        "Give Josh a useful, direct answer based on these results:\n"
        "- Key findings (3-5 bullet points)\n"
        "- Specific product names, companies, pricing if found\n"
        "- Most relevant URLs (max 3)\n"
        "- How this relates to his project\n"
        "- Be direct and opinionated — tell him what's worth looking at"
    )
    summary = await ask_llm(summary_prompt, timeout=60, retries=1)
    if summary and not summary.startswith("("):
        await reply_html(
            update, truncate(summary, 4000),
            reply_markup=build_quick_actions_keyboard(include_search=True),
        )
        search_entry = f"[search: {', '.join(queries)}]\n{summary}"
        conversation_history.append(("assistant", search_entry))
        save_message("assistant", search_entry, route="search")
    else:
        # Fallback: just show raw results
        await update.message.reply_text("📋 Results:\n\n" + truncate(results_text, 3800))


SEARCH_KEYWORDS = [
    "search for", "search the", "look up", "google", "find me",
    "search twitter", "search reddit", "search online", "search web",
    "what are people saying", "find similar", "find examples",
    "comparable", "competitors", "alternatives to",
]

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
    """Fast keyword routing with search intent detection."""
    lower = text.strip().lower()

    # Explicit prefix overrides (highest priority)
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

    # URL detection — fetch and analyze linked content
    urls = extract_urls(text)
    if urls:
        return "url", text

    # Search keywords — detect web search intent
    for kw in SEARCH_KEYWORDS:
        if kw in lower:
            return "search", text

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
    # (includes generative/action requests like "create a survey", "write an email", etc.)
    return "local", text


# Action-oriented keywords — when present, the LLM should PRODUCE content, not discuss it
ACTION_KEYWORDS = [
    "create", "write", "draft", "build", "make", "generate",
    "compose", "prepare", "put together", "come up with",
]


# --- Command handlers ---
@authorized
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_typing(update)
    left_h, right_h = await asyncio.gather(
        deep_health_check(LEFT_HOST, "left"),
        deep_health_check(RIGHT_HOST, "right"),
    )

    def format_health(name, emoji, h):
        if h["ssh"] == "offline":
            return f"{emoji} <b>{name}</b>: 🔴 OFFLINE"
        icons = []
        for key in ("ssh", "tmux", "ollama", "claude"):
            icon = "✅" if h[key] == "ok" else "❌"
            icons.append(f"{icon}{key}")
        return f"{emoji} <b>{name}</b>: {' '.join(icons)} | 💾{h['disk']}"

    recent = get_recent_results(5)
    lines = [
        "<b>📡 Swarm Status</b>",
        "",
        format_health("Left Brain", "🧠", left_h),
        format_health("Right Brain", "🎨", right_h),
        "",
        f"<b>📁 Recent Results ({len(recent)}):</b>",
    ]
    for f in recent:
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%H:%M")
        lines.append(f"  • {html_escape(f.stem)} ({mtime})")
    if not recent:
        lines.append("  (none)")
    await reply_html(update, "\n".join(lines))


@authorized
async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the full rich daily brief on demand."""
    await send_typing(update)
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
    await reply_html(update,
        "<b>🔗 Device Link</b>\n\n"
        "Just talk to me. I know your setup.\n\n"
        "<b>Routing:</b>\n"
        "• Short questions → I answer directly\n"
        "• Code tasks → 🧠 left brain\n"
        "• Design tasks → 🎨 right brain\n"
        "• Big projects → 🤝 both brains\n\n"
        "<b>Prefixes:</b>\n"
        "<code>left: &lt;task&gt;</code> — analytical work\n"
        "<code>right: &lt;task&gt;</code> — creative work\n"
        "<code>both: &lt;task&gt;</code> — collaboration\n"
        "<code>project: &lt;desc&gt;</code> — auto-split\n\n"
        "<b>Core:</b> /status /brief /results /help\n\n"
        "<b>🧠 Left Brain:</b>\n"
        "/codereview /tdd /buildfix /verify\n"
        "/testcoverage /refactorclean /e2e /securityaudit\n\n"
        "<b>🎨 Right Brain:</b>\n"
        "/plan /research /prd /architect\n\n"
        "<b>📓 Second Brain:</b>\n"
        "/inbox /note /journal /digest /connections\n\n"
        "<b>🔍 Web:</b> /search <i>or say 'search for...'</i>\n"
        "<b>📡 Trends:</b> /trends <i>topic</i> — last 30 days across platforms\n"
        "<b>📊 Predict:</b> /predict — LMSR market maker math\n"
        "<b>🎯 Signal:</b> /signal — Monte Carlo confidence scoring\n"
        "<b>💡 Suggest:</b> /suggest — let the bot suggest what to work on\n"
        "<b>🌙 Overnight:</b> /overnight <i>task</i> — queue for 2 AM\n"
        "<b>🔄 Ambient:</b> /ambient — always-on productive work\n"
        "<b>🧠 Memory:</b> /remember <i>query</i>\n"
        "<b>📬 Mailbox:</b> /mail • /mail left <i>msg</i>\n"
        "<b>⚡ Skills:</b> /skills • /newskill",
        reply_markup=build_quick_actions_keyboard(),
    )


# --- Web search command ---
@authorized
async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search the web from Telegram."""
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text("Usage: /search <query>\nExample: /search voice AI recruiting APIs")
        return
    await search_and_summarize(query, update, raw_query=True)


# --- LMSR Prediction Market Calculator ---
import math


def lmsr_cost(q, b):
    """LMSR cost function: C(q) = b * ln(sum(e^(qi/b)))"""
    return b * math.log(sum(math.exp(qi / b) for qi in q))


def lmsr_price(q, b, outcome_idx):
    """LMSR price for a specific outcome: softmax(qi/b)"""
    exps = [math.exp(qi / b) for qi in q]
    return exps[outcome_idx] / sum(exps)


def lmsr_prices(q, b):
    """All LMSR prices (probabilities) for each outcome."""
    exps = [math.exp(qi / b) for qi in q]
    total = sum(exps)
    return [e / total for e in exps]


def lmsr_buy_cost(q, b, outcome_idx, shares):
    """Cost to buy `shares` of outcome `outcome_idx`."""
    q_before = list(q)
    q_after = list(q)
    q_after[outcome_idx] += shares
    return lmsr_cost(q_after, b) - lmsr_cost(q_before, b)


def lmsr_edge(market_price, true_prob):
    """Expected value edge: EV = true_prob * (1 - market_price) - (1 - true_prob) * market_price"""
    return true_prob * (1.0 - market_price) - (1.0 - true_prob) * market_price


def lmsr_max_loss(b, n_outcomes=2):
    """Maximum loss for the market maker: b * ln(n)"""
    return b * math.log(n_outcomes)


@authorized
async def cmd_predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """LMSR prediction market calculator.

    Usage:
      /predict                          — show help
      /predict price 60                 — what does a 60% market look like
      /predict edge 0.60 0.72           — edge if market=60%, you think=72%
      /predict cost 0.55 100 50         — cost to buy 50 YES shares at 55%, b=100
      /predict analyze <question>       — LLM analyzes a prediction market question
    """
    args = " ".join(context.args).strip() if context.args else ""

    if not args:
        await reply_html(update,
            "<b>📊 LMSR Prediction Market Calculator</b>\n\n"
            "<b>Commands:</b>\n"
            "<code>/predict price 60</code> — market at 60%\n"
            "<code>/predict edge 0.60 0.72</code> — your edge (market vs your estimate)\n"
            "<code>/predict cost 0.55 100 50</code> — cost to buy 50 shares (price, b, qty)\n"
            "<code>/predict analyze Will X happen?</code> — LLM market analysis\n\n"
            "<b>Theory:</b>\n"
            "LMSR (Hanson 2002) uses C(q) = b·ln(Σe^(qi/b))\n"
            "Prices are softmax — always valid probabilities that sum to 1.\n"
            "Parameter b controls liquidity depth. Max maker loss = b·ln(n)."
        )
        return

    parts = args.split(None, 1)
    subcmd = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""

    if subcmd == "price":
        # /predict price 60  — show market state at this probability
        try:
            pct = float(rest.strip().rstrip("%"))
            if pct > 1:
                pct /= 100.0
            b = 100.0
            # Reverse-engineer q from desired price
            # For binary: price_yes = e^(q_yes/b) / (e^(q_yes/b) + e^(q_no/b))
            # With q_no=0: q_yes = b * ln(p/(1-p))
            if pct <= 0.01 or pct >= 0.99:
                await update.message.reply_text("Price must be between 1% and 99%")
                return
            q_yes = b * math.log(pct / (1.0 - pct))
            q = [q_yes, 0.0]
            prices = lmsr_prices(q, b)
            max_loss = lmsr_max_loss(b)

            # Cost to buy 10 more YES shares
            cost_10 = lmsr_buy_cost(q, b, 0, 10)
            new_prices = lmsr_prices([q[0] + 10, q[1]], b)

            await reply_html(update,
                f"<b>📊 Market State @ {pct*100:.1f}%</b>\n\n"
                f"YES price: <b>{prices[0]*100:.1f}%</b> (${prices[0]:.4f})\n"
                f"NO price: <b>{prices[1]*100:.1f}%</b> (${prices[1]:.4f})\n"
                f"Liquidity (b): {b}\n"
                f"Max maker loss: ${max_loss:.2f}\n\n"
                f"<b>If you buy 10 YES shares:</b>\n"
                f"Cost: ${cost_10:.2f} (avg ${cost_10/10:.4f}/share)\n"
                f"New YES price: {new_prices[0]*100:.1f}%\n"
                f"Price impact: +{(new_prices[0]-prices[0])*100:.1f}pp"
            )
        except (ValueError, ZeroDivisionError):
            await update.message.reply_text("Usage: /predict price 60 (percentage)")

    elif subcmd == "edge":
        # /predict edge 0.60 0.72  — market price vs your true estimate
        try:
            vals = rest.strip().split()
            market_p = float(vals[0])
            true_p = float(vals[1])
            if market_p > 1:
                market_p /= 100.0
            if true_p > 1:
                true_p /= 100.0

            ev = lmsr_edge(market_p, true_p)
            kelly = (true_p * (1.0 - market_p) - (1.0 - true_p) * market_p) / (1.0 - market_p) if market_p < 1 else 0

            direction = "BUY YES ✅" if ev > 0 else "BUY NO 🔴" if ev < 0 else "NO EDGE ⚪"
            await reply_html(update,
                f"<b>📊 Edge Analysis</b>\n\n"
                f"Market price: <b>{market_p*100:.1f}%</b>\n"
                f"Your estimate: <b>{true_p*100:.1f}%</b>\n"
                f"Edge (EV): <b>{ev*100:.2f}%</b>\n"
                f"Kelly fraction: <b>{kelly*100:.1f}%</b> of bankroll\n\n"
                f"Signal: <b>{direction}</b>\n\n"
                f"<i>EV = p_true × (1 - p_market) - (1 - p_true) × p_market</i>"
            )
        except (ValueError, IndexError):
            await update.message.reply_text("Usage: /predict edge 0.60 0.72 (market_price your_estimate)")

    elif subcmd == "cost":
        # /predict cost 0.55 100 50  — cost to buy shares at current price
        try:
            vals = rest.strip().split()
            market_p = float(vals[0])
            b = float(vals[1])
            shares = float(vals[2])
            if market_p > 1:
                market_p /= 100.0

            q_yes = b * math.log(market_p / (1.0 - market_p))
            q = [q_yes, 0.0]
            cost = lmsr_buy_cost(q, b, 0, shares)
            avg_price = cost / shares if shares else 0
            new_prices = lmsr_prices([q[0] + shares, q[1]], b)
            impact = new_prices[0] - market_p

            await reply_html(update,
                f"<b>📊 Trade Cost Calculator</b>\n\n"
                f"Current price: {market_p*100:.1f}%\n"
                f"Buying: {shares:.0f} YES shares\n"
                f"Liquidity (b): {b}\n\n"
                f"<b>Total cost: ${cost:.2f}</b>\n"
                f"Avg price: ${avg_price:.4f}/share\n"
                f"Slippage: {(avg_price - market_p)*100:.2f}pp\n"
                f"New market price: {new_prices[0]*100:.1f}%\n"
                f"Price impact: {impact*100:+.1f}pp\n\n"
                f"<b>Max payout if YES: ${shares:.2f}</b>\n"
                f"<b>Net profit if YES: ${shares - cost:.2f}</b>\n"
                f"<b>Loss if NO: -${cost:.2f}</b>"
            )
        except (ValueError, IndexError):
            await update.message.reply_text("Usage: /predict cost 0.55 100 50 (price, b, shares)")

    elif subcmd == "analyze":
        # LLM analysis of a prediction market question
        if not rest:
            await update.message.reply_text("Usage: /predict analyze Will AI replace recruiters by 2027?")
            return
        await send_typing(update)
        prompt = (
            "You are a prediction market analyst using LMSR (Logarithmic Market Scoring Rule) framework.\n\n"
            f"Question: {rest[:500]}\n\n"
            "Analyze this as a prediction market:\n"
            "1. **Base rate**: What's the historical/prior probability?\n"
            "2. **Current signals**: What evidence shifts the probability up or down?\n"
            "3. **Your estimate**: What probability would you assign? (be specific, e.g. 67%)\n"
            "4. **Key uncertainties**: What could swing this dramatically either way?\n"
            "5. **Edge opportunities**: If a market existed at X%, where's the mispricing?\n\n"
            "Be quantitative. Use numbers. Reference actual evidence. No hedging."
        )
        response = await ask_llm(prompt, timeout=60, retries=1)
        if response and not response.startswith("("):
            conversation_history.append(("assistant", f"[predict: {rest[:100]}]\n{response[:300]}"))
            save_message("assistant", response, route="predict")
            await reply_html(update, truncate(response, 4000))
        else:
            await update.message.reply_text(f"Analysis failed: {response[:200]}")
    else:
        await update.message.reply_text(f"Unknown subcommand: {subcmd}. Try /predict for help.")


# --- Monte Carlo Signal Generator ---
import random


def mc_dropout_simulate(base_prob, n_runs=50, dropout_noise=0.08):
    """Simulate Monte Carlo Dropout — run the 'model' n times with noise.
    Returns (mean_confidence, std_uncertainty, individual_predictions).
    In production this would be an actual LSTM. Here we simulate the concept:
    each run adds random noise to model the effect of dropout variability."""
    predictions = []
    for _ in range(n_runs):
        # Each 'analyst' sees slightly different data (dropout effect)
        noise = random.gauss(0, dropout_noise)
        pred = max(0.01, min(0.99, base_prob + noise))
        predictions.append(pred)
    mean_conf = sum(predictions) / len(predictions)
    std = (sum((p - mean_conf) ** 2 for p in predictions) / len(predictions)) ** 0.5
    return mean_conf, std, predictions


def generate_signal(mean_conf, std, confidence_threshold=0.70):
    """Generate BUY/HOLD signal from MC dropout results."""
    if mean_conf >= confidence_threshold and std < 0.12:
        return "BUY", "🟢"
    elif mean_conf >= confidence_threshold and std >= 0.12:
        return "WEAK BUY", "🟡"
    elif mean_conf < (1 - confidence_threshold) and std < 0.12:
        return "SELL", "🔴"
    else:
        return "HOLD", "⚪"


def calc_position_size(confidence, edge, bankroll=10000, max_pct=0.15):
    """Kelly-weighted position sizing. Caps at max_pct of bankroll."""
    if edge <= 0:
        return 0
    kelly = edge / (1.0 - confidence) if confidence < 1 else 0
    # Half-Kelly for safety
    half_kelly = kelly * 0.5
    size = bankroll * min(half_kelly, max_pct)
    return max(0, size)


@authorized
async def cmd_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Monte Carlo confidence signal generator for prediction markets.

    Usage:
      /signal                                — show help
      /signal 0.72                           — MC analysis at 72% base probability
      /signal 0.72 0.55                      — MC analysis + edge calc (your est vs market)
      /signal scan <topic>                   — LLM scans for high-confidence opportunities
    """
    args = " ".join(context.args).strip() if context.args else ""

    if not args:
        await reply_html(update,
            "<b>🎯 Monte Carlo Signal Generator</b>\n\n"
            "<b>Commands:</b>\n"
            "<code>/signal 0.72</code> — MC dropout analysis at 72% base prob\n"
            "<code>/signal 0.72 0.55</code> — with edge calc (yours vs market)\n"
            "<code>/signal scan AI recruiting</code> — LLM finds opportunities\n\n"
            "<b>Method (from @noisyb0y1):</b>\n"
            "Run model 50x with dropout noise → take mean + std.\n"
            "High mean + low std = consensus → BUY\n"
            "High mean + high std = disagreement → HOLD\n"
            "Threshold: 70% confidence, &lt;12% uncertainty"
        )
        return

    parts = args.split(None, 1)
    subcmd = parts[0].lower()

    if subcmd == "scan":
        # LLM scans for high-confidence prediction market opportunities
        topic = parts[1] if len(parts) > 1 else "current events and markets"
        await send_typing(update)
        placeholder = await reply_html(update, f"🎯 <b>Scanning for signals:</b> {html_escape(topic[:60])}...")

        prompt = (
            "You are a prediction market analyst scanning for high-confidence trading opportunities.\n\n"
            f"Topic: {topic}\n\n"
            "Identify 3-5 prediction market questions where you have HIGH confidence "
            "(>70%) in the outcome direction. For each:\n\n"
            "1. **Market question** (e.g., 'Will X happen by Y date?')\n"
            "2. **Your probability estimate** (be specific: 78%, not 'likely')\n"
            "3. **Likely market price** (what Polymarket/Kalshi would show)\n"
            "4. **Edge** (your estimate minus market price)\n"
            "5. **Confidence level** (how much your 50 'internal analysts' agree)\n"
            "6. **Key signal** (the one data point that makes this high-conviction)\n\n"
            "Focus on asymmetric bets — where the market is wrong and the payoff is large.\n"
            "Be specific. Use real events. No vague predictions."
        )
        response = await ask_llm(prompt, timeout=60, retries=1)
        if response and not response.startswith("("):
            conversation_history.append(("assistant", f"[signal scan: {topic[:60]}]\n{response[:300]}"))
            save_message("assistant", response, route="signal")
            await edit_or_reply(placeholder, "🎯 <b>Signal Scan Complete</b>")
            await reply_html(update, truncate(response, 4000),
                            reply_markup=build_quick_actions_keyboard(include_search=True))
        else:
            await edit_or_reply(placeholder, f"Scan failed: {response[:200]}")
        return

    # Numeric mode: /signal 0.72 [market_price]
    try:
        base_prob = float(subcmd)
        if base_prob > 1:
            base_prob /= 100.0

        market_price = None
        if len(parts) > 1:
            try:
                market_price = float(parts[1])
                if market_price > 1:
                    market_price /= 100.0
            except ValueError:
                pass

        # Run Monte Carlo simulation
        mean_conf, std, predictions = mc_dropout_simulate(base_prob, n_runs=50)
        signal, emoji = generate_signal(mean_conf, std)

        # Histogram of predictions
        buckets = [0] * 10  # 0-10%, 10-20%, ..., 90-100%
        for p in predictions:
            idx = min(9, int(p * 10))
            buckets[idx] += 1
        max_bucket = max(buckets) if buckets else 1
        hist_lines = []
        for i, count in enumerate(buckets):
            bar = "█" * int(count / max_bucket * 8) if max_bucket > 0 else ""
            pct = f"{i*10}-{(i+1)*10}%"
            hist_lines.append(f"{pct:>7} {bar} {count}")

        # Build response
        lines = [
            f"<b>🎯 Monte Carlo Signal Analysis</b>",
            f"",
            f"Base probability: <b>{base_prob*100:.1f}%</b>",
            f"MC runs: 50 (dropout noise σ=8%)",
            f"",
            f"<b>Results:</b>",
            f"Mean confidence: <b>{mean_conf*100:.1f}%</b>",
            f"Uncertainty (σ): <b>{std*100:.1f}%</b>",
            f"Signal: {emoji} <b>{signal}</b>",
            f"",
            f"<b>Distribution:</b>",
            f"<code>{''.join(hist_lines[5:])}</code>" if mean_conf > 0.5 else f"<code>{''.join(hist_lines[:5])}</code>",
        ]

        # Edge calc if market price provided
        if market_price is not None:
            edge = lmsr_edge(market_price, mean_conf)
            pos_size = calc_position_size(mean_conf, edge)
            direction = "BUY YES" if edge > 0 else "BUY NO" if edge < 0 else "NO EDGE"

            lines.extend([
                f"",
                f"<b>Edge vs Market:</b>",
                f"Market price: {market_price*100:.1f}%",
                f"Your edge: <b>{edge*100:.2f}%</b>",
                f"Direction: <b>{direction}</b>",
                f"Suggested size: <b>${pos_size:.0f}</b> (half-Kelly, $10k bankroll)",
            ])

        # Consensus check
        buys = sum(1 for p in predictions if p >= 0.70)
        holds = len(predictions) - buys
        lines.extend([
            f"",
            f"<b>Consensus:</b> {buys}/50 analysts say BUY, {holds}/50 say HOLD",
        ])

        if buys >= 40:
            lines.append("→ <b>Strong consensus. High conviction.</b>")
        elif buys >= 25:
            lines.append("→ <i>Mixed signals. Proceed with caution.</i>")
        else:
            lines.append("→ <i>No consensus. Skip this one.</i>")

        await reply_html(update, "\n".join(lines))

    except ValueError:
        await update.message.reply_text("Usage: /signal 0.72 or /signal 0.72 0.55\nSee /signal for help.")


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


# --- Memory & Mailbox & Skills Commands ---
@authorized
async def cmd_remember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search past conversations."""
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text("Usage: /remember <what to search for>\nSearches all past conversations.")
        return
    results = search_memory(query, limit=8)
    if not results:
        await update.message.reply_text("No memories found for: " + query)
        return
    lines = []
    for role, content, ts in results:
        date_str = ts[:10] if ts else "?"
        prefix = "Josh" if role == "user" else "Bot"
        lines.append(f"[{date_str}] {prefix}: {content[:150]}")
    await update.message.reply_text("🧠 Memories:\n\n" + truncate("\n\n".join(lines), 3800))


@authorized
async def cmd_mail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check the inter-agent mailbox."""
    args = " ".join(context.args) if context.args else ""

    # Send mail: /mail left Hey, check the test results
    if args and args.split()[0] in ("left", "right"):
        parts = args.split(None, 1)
        target = parts[0]
        message = parts[1] if len(parts) > 1 else ""
        if not message:
            await update.message.reply_text(f"Usage: /mail {target} <message>")
            return
        send_mail("main", target, message)
        await update.message.reply_text(f"📬 Mail sent to {target} brain.")
        return

    # Read mail
    all_mail = read_mail("main")
    if not all_mail:
        await update.message.reply_text("📭 No mail. Brains haven't sent any messages.")
        return
    lines = []
    for m in all_mail:
        lines.append(f"From {m['from']}:\n{m['content'][:500]}")
    await update.message.reply_text("📬 Mailbox:\n\n" + truncate("\n---\n".join(lines), 3800))

    # Clear after reading
    if args == "clear":
        clear_mail("main")
        await update.message.reply_text("Mailbox cleared.")


@authorized
async def cmd_newskill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new reusable skill."""
    args = " ".join(context.args) if context.args else ""
    if not args or "|" not in args:
        await update.message.reply_text(
            "Usage: /newskill name | brain | description | prompt\n\n"
            "Example:\n"
            "/newskill competitor-analysis | right | Analyze competitors for a product | "
            "Research and analyze the top 5 competitors for the given product. "
            "Include pricing, features, market position, strengths, weaknesses."
        )
        return

    parts = [p.strip() for p in args.split("|")]
    if len(parts) < 4:
        await update.message.reply_text("Need 4 parts separated by |: name | brain | description | prompt")
        return

    name, brain, description, prompt = parts[0], parts[1], parts[2], "|".join(parts[3:])

    # Validate
    safe_name = re.sub(r'[^\w-]', '', name.lower().replace(' ', '-'))[:30]
    if brain not in ("left", "right"):
        brain = "right"

    # Write skill file
    skill_path = SKILLS_DIR / f"{safe_name}.md"
    skill_content = (
        f"---\n"
        f"brain: {brain}\n"
        f"trigger: {safe_name}\n"
        f"description: {description}\n"
        f"created: {datetime.now().strftime('%Y-%m-%d')}\n"
        f"---\n\n"
        f"{prompt}\n"
    )
    skill_path.write_text(skill_content)

    # Reload skills
    global CUSTOM_SKILLS
    CUSTOM_SKILLS = load_custom_skills()

    await update.message.reply_text(
        f"✅ Skill '{safe_name}' created!\n"
        f"Brain: {brain}\n"
        f"Use: /{safe_name} <task>\n\n"
        f"Prompt: {prompt[:200]}..."
    )


@authorized
async def cmd_skills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all custom skills."""
    if not CUSTOM_SKILLS:
        await update.message.reply_text(
            "No custom skills yet.\n"
            "Create one: /newskill name | brain | description | prompt"
        )
        return
    lines = ["📋 Custom Skills:\n"]
    for name, info in CUSTOM_SKILLS.items():
        lines.append(f"/{name} — {info['description']} ({info['brain']} brain)")
    await update.message.reply_text("\n".join(lines))


@authorized
async def handle_custom_skill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle dynamically created skill commands."""
    cmd = update.message.text.split()[0].lstrip("/").split("@")[0]
    if cmd not in CUSTOM_SKILLS:
        return
    skill = CUSTOM_SKILLS[cmd]
    args = " ".join(context.args) if context.args else ""
    if not args:
        await update.message.reply_text(f"Usage: /{cmd} <task>\n{skill['description']}")
        return

    brain = skill["brain"]
    full_prompt = skill["prompt"] + "\n\nSpecific task: " + args[:500]
    await update.message.reply_text(f"Running /{cmd} on {brain} brain...")
    save_message("user", f"/{cmd} {args}", route="skill")
    t = asyncio.create_task(run_and_notify(update, brain, full_prompt))
    t.add_done_callback(_log_task_error)


# --- Main message handler ---
@authorized
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        return

    route, task = classify(text)
    logger.info("Route: %s | %s", route, task[:80])

    # Store user message in history + persistent memory
    conversation_history.append(("user", text))
    save_message("user", text, route=route)
    _last_user_message[update.effective_chat.id] = text

    if route == "url":
        urls = extract_urls(text)
        if urls:
            t = asyncio.create_task(fetch_and_analyze_url(urls[0], text, update))
            t.add_done_callback(_log_task_error)
            return

    if route == "search":
        await send_typing(update)
        t = asyncio.create_task(search_and_summarize(task, update))
        t.add_done_callback(_log_task_error)

    elif route == "local":
        await send_typing(update)
        placeholder = await update.message.reply_text("💭 Thinking...")
        full_prompt = build_prompt_with_history(text)

        # Detect action/generative requests and boost the prompt
        lower = text.lower()
        if any(kw in lower for kw in ACTION_KEYWORDS):
            full_prompt += (
                "\n\nIMPORTANT: Josh is asking you to CREATE/PRODUCE something. "
                "DO NOT ask for clarification. DO NOT say 'I can help with that'. "
                "Just PRODUCE the actual content right now — the full survey, document, email, "
                "plan, or whatever is requested. Make reasonable assumptions. Josh will iterate if needed."
            )

        response = await ask_llm(full_prompt, timeout=90, retries=1)

        # Catch useless "I can't search/access" responses — auto-search instead
        cant_phrases = [
            "can't search", "cannot search", "can't access the internet",
            "don't have access", "can't browse", "cannot browse",
            "no internet access", "can't look up", "unable to search",
            "can't access live", "don't have the ability to search",
            "can't pull up", "cannot pull up", "i can't visit",
            "can't access that", "cannot access that", "can't open",
            "i don't see the tweet", "i still don't see", "paste the text",
            "paste the actual", "paste it here", "copy and paste",
        ]
        if any(phrase in response.lower() for phrase in cant_phrases):
            # Check if there's a URL in recent history we should try fetching
            recent_url = None
            for role, msg in reversed(list(conversation_history)):
                urls = extract_urls(msg)
                if urls:
                    recent_url = urls[0]
                    break
            if recent_url:
                logger.info("LLM said it can't access — re-fetching recent URL: %s", recent_url[:80])
                await edit_or_reply(placeholder, f"🔗 Let me fetch that for you...")
                t = asyncio.create_task(fetch_and_analyze_url(recent_url, text, update))
                t.add_done_callback(_log_task_error)
            else:
                logger.info("LLM said it can't search — auto-triggering search for: %s", text[:80])
                await edit_or_reply(placeholder, "🔍 Searching the web...")
                t = asyncio.create_task(search_and_summarize(text, update))
                t.add_done_callback(_log_task_error)
        else:
            conversation_history.append(("assistant", response))
            save_message("assistant", response, route="local")
            # Edit placeholder with the actual response
            truncated = truncate(response, 4000)
            await edit_or_reply(placeholder, truncated)

    elif route == "collab":
        await send_typing(update)
        await reply_html(update, f"🤝 <b>Starting collaboration:</b> {html_escape(task[:100])}...")
        t = asyncio.create_task(run_collab_pipeline(update, task, DEFAULT_ROUNDS))
        t.add_done_callback(_log_task_error)

    elif route == "project":
        await send_typing(update)
        t = asyncio.create_task(run_project(update, task))
        t.add_done_callback(_log_task_error)

    elif route in ("left", "right"):
        await send_typing(update)
        emoji = "🧠" if route == "left" else "🎨"
        await reply_html(update, f"{emoji} <b>Dispatching to {route} brain:</b> {html_escape(task[:80])}...")
        t = asyncio.create_task(run_and_notify(update, route, task))
        t.add_done_callback(_log_task_error)


async def run_and_notify(update, brain, task):
    global _direct_tasks_active
    _direct_tasks_active += 1
    emoji = "🧠" if brain == "left" else "🎨" if brain == "right" else "🤝"
    # --- MC sync: mark agent busy + create task ---
    mc_update_agent(brain, "busy", task[:100])
    mc_task_id = mc_create_task(brain, task[:200], priority="medium")
    try:
        code, stdout, stderr = await dispatch_task(brain, task)
        if code == 0:
            result = truncate(stdout.strip(), 3000) if stdout.strip() else "(no output)"
            # Log to second-brain ledger
            log_to_ledger(brain, task[:200], "pipeline", "completed", stdout.strip()[:300])
            # --- MC sync: task done, agent idle ---
            mc_update_task(mc_task_id, "done", result_preview=stdout.strip()[:500])
            mc_update_agent(brain, "idle", f"Completed: {task[:80]}")
            # Review gate — send executive summary before full result
            review = await review_result(brain, task, stdout.strip())
            if review:
                await reply_html(update, f"<b>📝 Review ({brain}):</b>\n{html_escape(review)}")
            brain_entry = f"[{brain} brain]: {result[:200]}"
            conversation_history.append(("assistant", brain_entry))
            save_message("assistant", brain_entry, route=brain)
            await reply_html(
                update,
                f"{emoji} <b>{brain.capitalize()} brain done</b>\n\n{html_escape(result)}",
                reply_markup=build_quick_actions_keyboard(),
            )
        else:
            log_to_ledger(brain, task[:200], "pipeline", "failed", stderr.strip()[:300])
            # --- MC sync: task failed, agent idle ---
            mc_update_task(mc_task_id, "failed", outcome=stderr.strip()[:300])
            mc_update_agent(brain, "idle", f"Failed: {task[:80]}")
            err = truncate(stderr.strip() or stdout.strip(), 2000)
            await reply_html(update, f"❌ <b>{brain} failed</b> (exit {code}):\n<pre>{html_escape(err)}</pre>")
    except asyncio.TimeoutError:
        log_to_ledger(brain, task[:200], "pipeline", "timeout")
        mc_update_task(mc_task_id, "failed", outcome="timeout")
        mc_update_agent(brain, "idle", f"Timed out: {task[:80]}")
        await reply_html(update, f"⏰ <b>{brain} timed out:</b> {html_escape(task[:100])}")
    except Exception as e:
        log_to_ledger(brain, task[:200], "pipeline", "error", str(e))
        mc_update_task(mc_task_id, "failed", outcome=str(e)[:300])
        mc_update_agent(brain, "idle", f"Error: {task[:80]}")
        await reply_html(update, f"❌ <b>{brain} error:</b> {html_escape(str(e))}")
    finally:
        _direct_tasks_active = max(0, _direct_tasks_active - 1)


async def run_collab_pipeline(update, task, rounds=2):
    """Run collaborative pipeline with live progress streaming via @@COLLAB markers."""
    global _direct_tasks_active
    _direct_tasks_active += 1
    COLLAB_WALL_TIMEOUT = 900  # 15 min total wall-clock limit
    # --- MC sync: both brains busy + create collab task ---
    mc_update_agent("left", "busy", f"Collab: {task[:80]}")
    mc_update_agent("right", "busy", f"Collab: {task[:80]}")
    mc_task_id = mc_create_task("collab", task[:200], task_description="Collaborative pipeline", priority="high")
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
                # --- MC sync: collab done, both brains idle ---
                mc_update_task(mc_task_id, "done", result_preview=deliverable[:500])
                mc_update_agent("left", "idle", f"Collab done: {task[:80]}")
                mc_update_agent("right", "idle", f"Collab done: {task[:80]}")
                await update.message.reply_text("Final Result:")
                chunks = [deliverable[i:i+3500] for i in range(0, len(deliverable), 3500)]
                for chunk in chunks:
                    await update.message.reply_text(chunk)
                conversation_history.append(("assistant", f"[collab result]: {deliverable[:300]}"))
            else:
                mc_update_task(mc_task_id, "done", outcome="empty result")
                mc_update_agent("left", "idle", "Collab: empty result")
                mc_update_agent("right", "idle", "Collab: empty result")
                await update.message.reply_text("Collaboration complete but result was empty.")
        elif final_output_lines:
            # Fallback: send raw output
            output = "\n".join(final_output_lines)
            if output.strip():
                mc_update_task(mc_task_id, "done", result_preview=output[:500])
                mc_update_agent("left", "idle", f"Collab done: {task[:80]}")
                mc_update_agent("right", "idle", f"Collab done: {task[:80]}")
                chunks = [output[i:i+3500] for i in range(0, len(output), 3500)]
                await update.message.reply_text("Collaboration result:")
                for chunk in chunks:
                    await update.message.reply_text(chunk)
                conversation_history.append(("assistant", f"[collab result]: {output[:300]}"))
            else:
                mc_update_task(mc_task_id, "done", outcome="no output")
                mc_update_agent("left", "idle", "Collab: no output")
                mc_update_agent("right", "idle", "Collab: no output")
                await update.message.reply_text("Collaboration completed but no output captured.")
        else:
            stderr_out = (await asyncio.wait_for(proc.stderr.read(), timeout=10)).decode().strip()
            mc_update_task(mc_task_id, "failed", outcome=stderr_out[:300] if stderr_out else "no output")
            mc_update_agent("left", "idle", f"Collab failed: {task[:80]}")
            mc_update_agent("right", "idle", f"Collab failed: {task[:80]}")
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
        # --- MC sync: timeout ---
        mc_update_task(mc_task_id, "failed", outcome="timeout")
        mc_update_agent("left", "idle", f"Collab timed out: {task[:80]}")
        mc_update_agent("right", "idle", f"Collab timed out: {task[:80]}")
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
        mc_update_task(mc_task_id, "failed", outcome=str(e)[:300])
        mc_update_agent("left", "idle", f"Collab error: {task[:80]}")
        mc_update_agent("right", "idle", f"Collab error: {task[:80]}")
        await update.message.reply_text("Collaboration error: " + str(e))
    finally:
        _direct_tasks_active = max(0, _direct_tasks_active - 1)


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
    global _direct_tasks_active
    _direct_tasks_active += 1
    await update.message.reply_text(f"Planning project: {description[:100]}...\nBreaking into tasks...")
    try:
        plan = await plan_project(description)
    except Exception as e:
        await update.message.reply_text(f"Planning failed: {e}")
        _direct_tasks_active = max(0, _direct_tasks_active - 1)
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

    # --- MC sync: mark brains busy for project ---
    if left_tasks:
        mc_update_agent("left", "busy", f"Project: {summary[:80]}")
    if right_tasks:
        mc_update_agent("right", "busy", f"Project: {summary[:80]}")

    async def run_one(brain, task_text):
        # --- MC sync: create task for each sub-task ---
        mc_tid = mc_create_task(brain, task_text[:200], task_description=f"Project: {summary[:200]}", priority="medium")
        try:
            code, stdout, stderr = await dispatch_task(brain, task_text)
            status = "done" if code == 0 else "failed"
            output = stdout.strip()[:500] if code == 0 else (stderr.strip() or stdout.strip())[:500]
            results.append((brain, task_text, status, output))
            # --- MC sync: update task result ---
            mc_update_task(mc_tid, status, result_preview=output[:500])
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
            mc_update_task(mc_tid, "failed", outcome=str(e)[:300])
            await update.message.reply_text(f"{brain} error: {task_text[:60]}\n{e}")

    await asyncio.gather(*(run_one(b, t) for b, t in
                           [(b, t) for b in ["left"] for t in left_tasks] +
                           [(b, t) for b in ["right"] for t in right_tasks]))

    # --- MC sync: all project tasks done, brains idle ---
    done = sum(1 for _, _, s, _ in results if s == "done")
    total = len(results)
    if left_tasks:
        mc_update_agent("left", "idle", f"Project done: {done}/{total} tasks")
    if right_tasks:
        mc_update_agent("right", "idle", f"Project done: {done}/{total} tasks")
    conversation_history.append(("assistant", f"[project]: {summary} — {done}/{total} tasks done"))
    await update.message.reply_text(
        f"Project complete: {done}/{total} tasks succeeded.\n"
        f"Use /results to see full output."
    )
    _direct_tasks_active = max(0, _direct_tasks_active - 1)


# --- Inline Keyboard Callback Handler ---
# Store last user message per chat for dispatch callbacks
_last_user_message = {}


@authorized
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "action_status":
        # Simulate /status command
        fake_update = update
        fake_update.message = query.message
        await cmd_status(fake_update, context)
    elif data == "action_brief":
        fake_update = update
        fake_update.message = query.message
        await cmd_brief(fake_update, context)
    elif data == "action_results":
        fake_update = update
        fake_update.message = query.message
        await cmd_results(fake_update, context)
    elif data == "action_search_more":
        await query.message.reply_text("What should I search for?")
    elif data.startswith("dispatch_"):
        brain = data.replace("dispatch_", "")
        chat_id = update.effective_chat.id
        last_msg = _last_user_message.get(chat_id, "")
        if not last_msg:
            await query.message.reply_text("No recent message to dispatch. Send a task first.")
            return
        if brain == "collab":
            await query.message.reply_text(f"🤝 Starting collaboration: {last_msg[:80]}...")
            t = asyncio.create_task(run_collab_pipeline(update, last_msg, DEFAULT_ROUNDS))
            t.add_done_callback(_log_task_error)
        else:
            emoji = "🧠" if brain == "left" else "🎨"
            await query.message.reply_text(f"{emoji} Dispatching to {brain} brain: {last_msg[:80]}...")
            t = asyncio.create_task(run_and_notify_from_msg(query.message, brain, last_msg))
            t.add_done_callback(_log_task_error)


async def run_and_notify_from_msg(message, brain, task):
    """Like run_and_notify but works with a raw message object (for callbacks)."""
    global _direct_tasks_active
    _direct_tasks_active += 1
    emoji = "🧠" if brain == "left" else "🎨" if brain == "right" else "🤝"
    # --- MC sync: mark agent busy + create task ---
    mc_update_agent(brain, "busy", task[:100])
    mc_task_id = mc_create_task(brain, task[:200], priority="medium")
    try:
        code, stdout, stderr = await dispatch_task(brain, task)
        if code == 0:
            result = truncate(stdout.strip(), 3000) if stdout.strip() else "(no output)"
            log_to_ledger(brain, task[:200], "pipeline", "completed", stdout.strip()[:300])
            # --- MC sync: task done, agent idle ---
            mc_update_task(mc_task_id, "done", result_preview=stdout.strip()[:500])
            mc_update_agent(brain, "idle", f"Completed: {task[:80]}")
            review = await review_result(brain, task, stdout.strip())
            if review:
                await message.reply_text(f"📝 Review ({brain}):\n{review}")
            brain_entry = f"[{brain} brain]: {result[:200]}"
            conversation_history.append(("assistant", brain_entry))
            save_message("assistant", brain_entry, route=brain)
            await message.reply_text(f"{emoji} {brain.capitalize()} brain done:\n\n{result}")
        else:
            log_to_ledger(brain, task[:200], "pipeline", "failed", stderr.strip()[:300])
            # --- MC sync: task failed, agent idle ---
            mc_update_task(mc_task_id, "failed", outcome=stderr.strip()[:300])
            mc_update_agent(brain, "idle", f"Failed: {task[:80]}")
            err = truncate(stderr.strip() or stdout.strip(), 2000)
            await message.reply_text(f"❌ {brain} failed (exit {code}):\n{err}")
    except asyncio.TimeoutError:
        log_to_ledger(brain, task[:200], "pipeline", "timeout")
        mc_update_task(mc_task_id, "failed", outcome="timeout")
        mc_update_agent(brain, "idle", f"Timed out: {task[:80]}")
        await message.reply_text(f"⏰ {brain} timed out: {task[:100]}")
    except Exception as e:
        log_to_ledger(brain, task[:200], "pipeline", "error", str(e))
        mc_update_task(mc_task_id, "failed", outcome=str(e)[:300])
        mc_update_agent(brain, "idle", f"Error: {task[:80]}")
        await message.reply_text(f"❌ {brain} error: {e}")
    finally:
        _direct_tasks_active = max(0, _direct_tasks_active - 1)


# --- Global Error Handler ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and notify user if possible."""
    logger.error("Exception while handling an update: %s", context.error)
    if update and hasattr(update, 'effective_chat') and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ Something went wrong: {str(context.error)[:200]}"
            )
        except Exception:
            pass


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


# --- Reverse Prompting: /suggest ---
@authorized
async def cmd_suggest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Let the bot lead — reverse prompting. Suggests what to work on next."""
    await send_typing(update)
    placeholder = await reply_html(update, "🧠 <b>Analyzing your projects and recent work...</b>")

    # Gather context: recent results, pending tasks, conversation history
    results = get_overnight_results()
    results_summary = ""
    for brain in ("left", "right", "collab"):
        for item in results.get(brain, [])[:3]:
            results_summary += f"- [{brain}] {item['task']}: {item['preview'][:100]}\n"

    pending = []
    if LEDGER_DIR.exists():
        for f in sorted(LEDGER_DIR.glob("*.md"), key=os.path.getmtime, reverse=True)[:10]:
            entry = parse_ledger_entry(f)
            if entry and entry.get("status") != "completed":
                pending.append(f"- [{entry.get('brain', '?')}] {entry.get('task', '?')[:80]}")

    recent_conv = []
    for role, msg in list(conversation_history)[-15:]:
        if role != "system":
            recent_conv.append(f"{role}: {msg[:200]}")

    prompt = (
        "You are Wally, the manager agent of Josh's Device Link AI swarm. "
        "Your job is to LEAD, not follow. Based on everything you know about Josh's "
        "projects and recent work, suggest what he should focus on next.\n\n"
        "Josh's active projects:\n"
        "- AI Screening Assistant (recruiting tool for Naples/Xwell salons)\n"
        "- Device Link (the multi-Mac AI swarm you're running on)\n\n"
    )
    if results_summary:
        prompt += f"Recent completed work:\n{results_summary}\n"
    if pending:
        prompt += f"Pending tasks:\n" + "\n".join(pending[:5]) + "\n\n"
    if recent_conv:
        prompt += f"Recent conversation:\n" + "\n".join(recent_conv[-8:]) + "\n\n"

    prompt += (
        "Based on all this context, suggest 3 concrete things Josh should work on next. "
        "For each suggestion:\n"
        "1. What to do (specific and actionable)\n"
        "2. Which brain to use (left/right/both)\n"
        "3. Why now (what makes this timely)\n\n"
        "Also flag anything that looks stuck or forgotten.\n"
        "Be opinionated. Be specific. Don't hedge."
    )

    response = await ask_llm(prompt, timeout=60, retries=1)
    if response and not response.startswith("("):
        conversation_history.append(("assistant", f"[suggest]: {response[:300]}"))
        save_message("assistant", response, route="suggest")
        await edit_or_reply(placeholder, truncate(response, 4000))
    else:
        await edit_or_reply(placeholder, f"Couldn't generate suggestions: {response[:200]}")


# --- Trends Search: /trends ---
@authorized
async def cmd_trends(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search last 30 days across Reddit, X, YouTube for trending topics."""
    topic = " ".join(context.args) if context.args else ""
    if not topic:
        await update.message.reply_text("Usage: /trends <topic>\nExample: /trends AI recruiting tools")
        return

    await send_typing(update)
    placeholder = await reply_html(update, f"📡 <b>Scanning trends:</b> <code>{html_escape(topic[:60])}</code>")

    # Multi-platform search queries
    queries = [
        f"{topic} site:reddit.com 2026",
        f"{topic} site:x.com OR site:twitter.com",
        f"{topic} site:youtube.com 2026",
        f"{topic} latest trends 2026",
    ]

    all_results = []
    for q in queries:
        await send_typing(update)
        results = await web_search(q, max_results=4)
        all_results.extend(results)

    # Deduplicate
    seen_urls = set()
    unique = []
    for r in all_results:
        url = r.get("href", "")
        if url not in seen_urls:
            seen_urls.add(url)
            unique.append(r)

    if not unique:
        await edit_or_reply(placeholder, "No trending results found. Try different keywords.")
        return

    # Format for LLM
    formatted = []
    for i, r in enumerate(unique[:12], 1):
        formatted.append(f"{i}. {r.get('title', '')}\n   {r.get('href', '')}\n   {r.get('body', '')}")
    results_text = "\n\n".join(formatted)

    await send_typing(update)
    summary_prompt = (
        f"Josh is researching trending topics: {topic}\n\n"
        "These are search results from the LAST 30 DAYS across Reddit, X/Twitter, and YouTube.\n\n"
        f"Results:\n{results_text[:4000]}\n\n"
        "Analyze these results and give Josh a trends brief:\n"
        "1. 🔥 What's hot right now (top 3 trends with specific examples)\n"
        "2. 💡 Emerging patterns (what's gaining momentum)\n"
        "3. 🎯 Actionable for Josh (how these trends relate to his AI recruiting screener & Device Link)\n"
        "4. 📎 Best links to check out (top 3 URLs)\n\n"
        "Be specific. Name names. Reference actual content from the results."
    )
    summary = await ask_llm(summary_prompt, timeout=60, retries=1)
    if summary and not summary.startswith("("):
        conversation_history.append(("assistant", f"[trends: {topic}]\n{summary[:300]}"))
        save_message("assistant", summary, route="trends")
        await reply_html(update, truncate(summary, 4000),
                        reply_markup=build_quick_actions_keyboard(include_search=True))
    else:
        await update.message.reply_text("📋 Raw results:\n\n" + truncate(results_text, 3800))


# --- Proactive Overnight Work: /overnight ---
OVERNIGHT_FILE = Path.home() / ".device-link" / "overnight-queue.json"


@authorized
async def cmd_overnight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Queue tasks for overnight autonomous execution, or see what ran."""
    args = " ".join(context.args) if context.args else ""

    if not args or args.strip().lower() == "status":
        # Show overnight queue + last results
        queue = []
        if OVERNIGHT_FILE.exists():
            try:
                queue = json.loads(OVERNIGHT_FILE.read_text())
            except Exception:
                pass
        if not queue:
            await reply_html(update,
                "<b>🌙 Overnight Queue</b>\n\n"
                "No tasks queued. Add some:\n"
                "<code>/overnight research AI voice screening competitors</code>\n"
                "<code>/overnight draft onboarding email for new salon partners</code>\n\n"
                "Tasks run at 2 AM and results arrive with your 8 AM brief."
            )
        else:
            lines = ["<b>🌙 Overnight Queue</b>\n"]
            for i, task in enumerate(queue, 1):
                brain = task.get("brain", "auto")
                desc = task.get("task", "?")[:80]
                lines.append(f"{i}. [{brain}] {desc}")
            lines.append(f"\nThese will run at 2 AM. Use /overnight clear to reset.")
            await reply_html(update, "\n".join(lines))
        return

    if args.strip().lower() == "clear":
        OVERNIGHT_FILE.write_text("[]")
        await update.message.reply_text("🌙 Overnight queue cleared.")
        return

    # Add task to queue
    queue = []
    if OVERNIGHT_FILE.exists():
        try:
            queue = json.loads(OVERNIGHT_FILE.read_text())
        except Exception:
            pass

    # Auto-detect brain
    lower = args.lower()
    if any(kw in lower for kw in LEFT_KEYWORDS):
        brain = "left"
    elif any(kw in lower for kw in RIGHT_KEYWORDS):
        brain = "right"
    else:
        brain = "collab"

    queue.append({
        "task": args,
        "brain": brain,
        "queued_at": datetime.now().isoformat(),
    })
    OVERNIGHT_FILE.write_text(json.dumps(queue, indent=2))
    emoji = {"left": "🧠", "right": "🎨", "collab": "🤝"}[brain]
    await reply_html(update,
        f"🌙 <b>Queued for overnight:</b>\n"
        f"{emoji} [{brain}] {html_escape(args[:100])}\n\n"
        f"Queue size: {len(queue)} task(s). Will run at 2 AM."
    )


async def run_overnight_tasks(context: ContextTypes.DEFAULT_TYPE):
    """2 AM job: run all queued overnight tasks."""
    if not OVERNIGHT_FILE.exists():
        return
    try:
        queue = json.loads(OVERNIGHT_FILE.read_text())
    except Exception:
        return
    if not queue:
        return

    logger.info("Running %d overnight tasks", len(queue))
    await context.bot.send_message(
        chat_id=AUTHORIZED_CHAT_ID,
        text=f"🌙 Starting {len(queue)} overnight task(s)..."
    )

    for task_info in queue:
        task_text = task_info.get("task", "")
        brain = task_info.get("brain", "collab")
        if not task_text:
            continue
        # --- MC sync: create task + set agent busy ---
        mc_tid = mc_create_task(brain, task_text[:200], task_description="Overnight queue", priority="low")
        try:
            if brain == "collab":
                mc_update_agent("left", "busy", f"Overnight: {task_text[:80]}")
                mc_update_agent("right", "busy", f"Overnight: {task_text[:80]}")
                code, stdout, stderr = await dispatch_task("left", task_text)
                if code == 0:
                    code2, stdout2, stderr2 = await dispatch_task("right", task_text)
                mc_update_agent("left", "idle", f"Overnight done: {task_text[:60]}")
                mc_update_agent("right", "idle", f"Overnight done: {task_text[:60]}")
            else:
                mc_update_agent(brain, "busy", f"Overnight: {task_text[:80]}")
                code, stdout, stderr = await dispatch_task(brain, task_text)
                mc_update_agent(brain, "idle", f"Overnight done: {task_text[:60]}")
            status = "completed" if code == 0 else "failed"
            log_to_ledger(brain, task_text[:200], "overnight", status)
            mc_update_task(mc_tid, "done" if code == 0 else "failed",
                           result_preview=(stdout.strip()[:500] if code == 0 else stderr.strip()[:300]))
        except Exception as e:
            logger.error("Overnight task failed: %s — %s", task_text[:60], e)
            log_to_ledger(brain, task_text[:200], "overnight", "error", str(e))
            mc_update_task(mc_tid, "failed", outcome=str(e)[:300])
            # Reset agents to idle on error
            if brain == "collab":
                mc_update_agent("left", "idle", f"Overnight error: {task_text[:60]}")
                mc_update_agent("right", "idle", f"Overnight error: {task_text[:60]}")
            else:
                mc_update_agent(brain, "idle", f"Overnight error: {task_text[:60]}")

    # Clear the queue
    OVERNIGHT_FILE.write_text("[]")
    logger.info("Overnight tasks complete, queue cleared")


# --- Automatic Memory Flush ---
async def memory_flush(context: ContextTypes.DEFAULT_TYPE):
    """Periodic memory flush — save conversation context to persistent memory."""
    if not conversation_history:
        return
    try:
        # Build a context snapshot
        recent = list(conversation_history)[-20:]
        snapshot_lines = []
        for role, msg in recent:
            if role != "system":
                snapshot_lines.append(f"{role}: {msg[:300]}")
        if not snapshot_lines:
            return

        snapshot = "\n".join(snapshot_lines)
        # Save to a file for crash recovery
        flush_file = MEMORY_DIR / "last-session-context.md"
        flush_file.write_text(
            f"---\n"
            f"flushed: {datetime.now().isoformat()}\n"
            f"session: {SESSION_ID}\n"
            f"messages: {len(recent)}\n"
            f"---\n\n"
            f"# Session Context Snapshot\n\n"
            f"{snapshot}\n"
        )
        logger.info("Memory flush: saved %d messages to %s", len(recent), flush_file)
    except Exception as e:
        logger.error("Memory flush failed: %s", e)


# --- Ambient Work System — Agents never idle ---
AMBIENT_FILE = Path.home() / ".device-link" / "ambient-state.json"
AMBIENT_RESULTS_DIR = Path.home() / ".device-link" / "results" / "ambient"
AMBIENT_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Lock to prevent overlapping ambient dispatches
_ambient_running = False
# Track when user-requested tasks are active (ambient yields to direct work)
_direct_tasks_active = 0

# Task categories — rotated through so brains always have productive work
AMBIENT_TASKS = {
    "income": [
        {
            "brain": "left",
            "task": "Research current high-demand freelance skills on Upwork, Toptal, and Fiverr for 2026. "
                    "Identify 3 specific micro-SaaS or AI-agent niches that a solo developer with Claude/AI expertise "
                    "could build and monetize within 2 weeks. For each, estimate monthly revenue potential, "
                    "competition level, and a one-paragraph build plan. Output as actionable markdown.",
            "label": "Freelance opportunity scan",
        },
        {
            "brain": "right",
            "task": "Generate 3 creative AI-powered product ideas that could be launched as paid tools or services "
                    "within 1-2 weeks using existing Device Link infrastructure (3 Macs, Claude, Telegram bot). "
                    "For each idea: name it, describe the value prop, target audience, pricing model, and a quick "
                    "marketing hook. Think outside the box — what would people pay $20-50/mo for?",
            "label": "Product ideation",
        },
        {
            "brain": "left",
            "task": "Analyze the current AI agent marketplace (AgentHub, CrewAI marketplace, OpenAI GPT store, "
                    "Claude artifacts). Identify gaps where a multi-agent swarm like Device Link has a competitive "
                    "edge. Suggest 2 concrete agent-as-a-service offerings with pricing, technical requirements, "
                    "and a go-to-market strategy. Be specific and actionable.",
            "label": "Agent marketplace analysis",
        },
        {
            "brain": "right",
            "task": "Draft a compelling landing page copy (headline, subheadline, 3 benefit bullets, CTA) for "
                    "an AI automation service targeting small business owners. The service uses a multi-agent AI swarm "
                    "to handle research, content creation, and technical tasks 24/7. Make it punchy, modern, and "
                    "conversion-focused. Include pricing tier suggestions.",
            "label": "Landing page copy draft",
        },
        {
            "brain": "left",
            "task": "Research trending GitHub repos, ProductHunt launches, and HackerNews front-page projects from "
                    "the past 7 days in the AI/automation space. Identify patterns and underserved niches. "
                    "Suggest 2 open-source tools or libraries that could be built to gain traction and later "
                    "monetized via premium features. Include repo naming, README outline, and launch strategy.",
            "label": "Open source opportunity scan",
        },
    ],
    "project": [
        {
            "brain": "left",
            "task": "Review the AI Screening Assistant project for Naples/Xwell Spa. Analyze the current technical "
                    "implementation plan and identify: 1) The single highest-risk technical component, 2) A concrete "
                    "next step that could be built today, 3) Any missing security or compliance considerations for "
                    "handling candidate data (CCPA, etc). Output actionable recommendations.",
            "label": "AI Screening Assistant review",
        },
        {
            "brain": "right",
            "task": "For the AI Screening Assistant project: design the candidate experience flow from receiving "
                    "the screening call to getting hired. Map out the emotional journey, identify friction points, "
                    "and suggest 3 UX improvements that would make candidates feel valued (not interrogated by AI). "
                    "Include sample conversation scripts for the voice AI.",
            "label": "Screening UX design",
        },
        {
            "brain": "left",
            "task": "Audit the Device Link codebase itself. Review telegram-bridge.py for: 1) Error handling gaps "
                    "that could cause silent failures, 2) Performance bottlenecks in the message handling pipeline, "
                    "3) Security concerns (token exposure, injection risks). Suggest the top 3 improvements with "
                    "specific code-level recommendations.",
            "label": "Device Link self-audit",
        },
    ],
    "growth": [
        {
            "brain": "right",
            "task": "Write a Twitter/X thread (8-10 tweets) about building a personal AI agent swarm with 3 Mac laptops. "
                    "Cover: the setup, what it does, surprising capabilities, and lessons learned. Make it authentic, "
                    "technically interesting but accessible. Include hook tweet and a CTA. Style: builder sharing "
                    "their work, not salesy.",
            "label": "Twitter thread draft",
        },
        {
            "brain": "left",
            "task": "Research SEO keywords and content opportunities around 'AI agent swarm', 'multi-agent system', "
                    "'personal AI assistant setup', and 'Claude Code automation'. Identify 5 long-tail keywords with "
                    "search volume, suggest blog post titles for each, and outline the highest-opportunity post in "
                    "detail (H2 structure, word count target, key points to cover).",
            "label": "SEO content research",
        },
        {
            "brain": "right",
            "task": "Design a short-form video script (60-90 seconds) showing the Device Link AI swarm in action. "
                    "The hook should grab attention in 3 seconds. Show: sending a task via Telegram, both brains "
                    "working simultaneously, results coming back. End with a memorable takeaway. Write the full "
                    "script with visual directions and voiceover text.",
            "label": "Video script draft",
        },
    ],
    "research": [
        {
            "brain": "left",
            "task": "Research the latest developments in AI agent frameworks (CrewAI, AutoGen, LangGraph, Claude Agent SDK, "
                    "OpenAI Swarm) from the past 30 days. Compare their multi-agent orchestration approaches with "
                    "Device Link's bash-based trigger system. Identify 2-3 features or patterns worth adopting. "
                    "Be specific about implementation difficulty and expected benefits.",
            "label": "AI framework landscape scan",
        },
        {
            "brain": "right",
            "task": "Explore unconventional uses of a 3-machine AI swarm that most people wouldn't think of. "
                    "Consider: automated negotiation, real-time market making simulation, creative writing partnerships, "
                    "music composition, game AI testing, scientific hypothesis generation. Pick the 3 most promising "
                    "and write a one-page concept for each.",
            "label": "Creative swarm applications",
        },
        {
            "brain": "left",
            "task": "Analyze the economics of running AI agents 24/7. Compare: Claude API costs vs local Ollama models "
                    "vs hybrid approaches. Calculate break-even points for different workloads. Suggest an optimal "
                    "cost-reduction strategy for Device Link that maintains quality for complex tasks while using "
                    "local models for routine work. Include specific model recommendations.",
            "label": "Cost optimization analysis",
        },
    ],
}

# Flatten all tasks with category tags
_ALL_AMBIENT = []
for category, tasks in AMBIENT_TASKS.items():
    for t in tasks:
        _ALL_AMBIENT.append({**t, "category": category})


def _load_ambient_state():
    """Load ambient state (last run index, history, enabled flag)."""
    if AMBIENT_FILE.exists():
        try:
            return json.loads(AMBIENT_FILE.read_text())
        except Exception:
            pass
    return {"enabled": True, "index": 0, "history": [], "paused_until": None}


def _save_ambient_state(state):
    """Persist ambient state."""
    AMBIENT_FILE.write_text(json.dumps(state, indent=2, default=str))


async def run_ambient_loop(context: ContextTypes.DEFAULT_TYPE):
    """Periodic job: if brains are idle, dispatch productive ambient work."""
    global _ambient_running
    if _ambient_running:
        logger.info("Ambient: skipping — previous task still running")
        return

    if _direct_tasks_active > 0:
        logger.info("Ambient: skipping — %d direct task(s) active", _direct_tasks_active)
        return

    state = _load_ambient_state()
    if not state.get("enabled", True):
        return

    # Check if paused (e.g. user said "stop ambient for 2 hours")
    paused_until = state.get("paused_until")
    if paused_until:
        try:
            if datetime.fromisoformat(paused_until) > datetime.now():
                return
            else:
                state["paused_until"] = None
                _save_ambient_state(state)
        except Exception:
            state["paused_until"] = None
            _save_ambient_state(state)

    # Pick next task (round-robin through all categories)
    if not _ALL_AMBIENT:
        return
    idx = state.get("index", 0) % len(_ALL_AMBIENT)
    task_info = _ALL_AMBIENT[idx]

    brain = task_info["brain"]
    task_text = task_info["task"]
    label = task_info["label"]
    category = task_info["category"]

    _ambient_running = True
    logger.info("Ambient: dispatching [%s/%s] %s to %s brain", category, label, task_text[:60], brain)

    # --- MC sync ---
    mc_update_agent(brain, "busy", f"Ambient: {label[:80]}")
    mc_task_id = mc_create_task(brain, f"[Ambient] {label}"[:200],
                                 task_description=task_text[:500], priority="low")

    try:
        code, stdout, stderr = await dispatch_task(brain, task_text)
        now_str = datetime.now().strftime("%Y%m%d-%H%M%S")

        if code == 0 and stdout.strip():
            # Save result
            result_file = AMBIENT_RESULTS_DIR / f"{category}-{brain}-{now_str}.md"
            result_file.write_text(
                f"---\n"
                f"category: {category}\n"
                f"label: {label}\n"
                f"brain: {brain}\n"
                f"timestamp: {datetime.now().isoformat()}\n"
                f"---\n\n"
                f"# {label}\n\n"
                f"{stdout.strip()}\n"
            )
            log_to_ledger(brain, f"[ambient] {label}"[:200], "ambient", "completed", stdout.strip()[:300])
            mc_update_task(mc_task_id, "done", result_preview=stdout.strip()[:500])
            mc_update_agent(brain, "idle", f"Ambient done: {label[:60]}")

            # Notify user with a brief summary (don't spam — keep it short)
            preview = stdout.strip()[:300]
            await context.bot.send_message(
                chat_id=AUTHORIZED_CHAT_ID,
                text=f"🔄 <b>Ambient [{category}]:</b> {label}\n\n{preview[:200]}...\n\n"
                     f"<i>Full result saved. Use /ambient results to see all.</i>",
                parse_mode="HTML",
            )
        else:
            err = stderr.strip()[:200] if stderr else "(no output)"
            logger.warning("Ambient task failed: %s — %s", label, err)
            mc_update_task(mc_task_id, "failed", outcome=err)
            mc_update_agent(brain, "idle", f"Ambient failed: {label[:60]}")

    except asyncio.TimeoutError:
        logger.warning("Ambient task timed out: %s", label)
        mc_update_task(mc_task_id, "failed", outcome="timeout")
        mc_update_agent(brain, "idle", f"Ambient timeout: {label[:60]}")
    except Exception as e:
        logger.error("Ambient error: %s — %s", label, e)
        mc_update_task(mc_task_id, "failed", outcome=str(e)[:300])
        mc_update_agent(brain, "idle", f"Ambient error: {label[:60]}")
    finally:
        _ambient_running = False
        # Advance index
        state = _load_ambient_state()
        state["index"] = (idx + 1) % len(_ALL_AMBIENT)
        state["history"].append({
            "label": label,
            "category": category,
            "brain": brain,
            "timestamp": datetime.now().isoformat(),
        })
        # Keep only last 50 history entries
        state["history"] = state["history"][-50:]
        _save_ambient_state(state)


# --- /ambient command ---
@authorized
async def cmd_ambient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Control the ambient work system. Usage: /ambient [on|off|status|results|pause <hours>]"""
    args = " ".join(context.args).strip().lower() if context.args else "status"
    state = _load_ambient_state()

    if args == "on":
        state["enabled"] = True
        state["paused_until"] = None
        _save_ambient_state(state)
        await reply_html(update,
            "🔄 <b>Ambient work: ENABLED</b>\n"
            "Brains will automatically work on productive tasks when idle."
        )

    elif args == "off":
        state["enabled"] = False
        _save_ambient_state(state)
        await reply_html(update,
            "⏸ <b>Ambient work: DISABLED</b>\n"
            "Brains will idle when not given direct tasks."
        )

    elif args.startswith("pause"):
        hours = 2  # default
        parts = args.split()
        if len(parts) > 1:
            try:
                hours = float(parts[1])
            except ValueError:
                pass
        from datetime import timedelta
        resume_at = datetime.now() + timedelta(hours=hours)
        state["paused_until"] = resume_at.isoformat()
        _save_ambient_state(state)
        await reply_html(update,
            f"⏸ <b>Ambient paused for {hours:.1f}h</b>\n"
            f"Resumes at {resume_at.strftime('%H:%M')}"
        )

    elif args == "results":
        # Show recent ambient results
        result_files = sorted(AMBIENT_RESULTS_DIR.glob("*.md"), key=os.path.getmtime, reverse=True)[:10]
        if not result_files:
            await reply_html(update, "No ambient results yet. Brains are just getting started!")
            return
        lines = ["<b>🔄 Recent Ambient Work:</b>\n"]
        for f in result_files:
            name = f.stem
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%m/%d %H:%M")
            # Parse label from frontmatter
            try:
                content = f.read_text()
                label_line = [l for l in content.split("\n") if l.startswith("label:")]
                label = label_line[0].split(":", 1)[1].strip() if label_line else name
            except Exception:
                label = name
            lines.append(f"• <b>{mtime}</b> — {label}")
        lines.append(f"\n<i>{len(result_files)} results shown. Files in ~/results/ambient/</i>")
        await reply_html(update, "\n".join(lines))

    elif args.startswith("show"):
        # Show the last ambient result in full
        result_files = sorted(AMBIENT_RESULTS_DIR.glob("*.md"), key=os.path.getmtime, reverse=True)
        if not result_files:
            await reply_html(update, "No ambient results yet.")
            return
        content = result_files[0].read_text()
        # Strip frontmatter
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                content = content[end + 3:].strip()
        chunks = [content[i:i+3500] for i in range(0, min(len(content), 7000), 3500)]
        for chunk in chunks:
            await update.message.reply_text(chunk)

    elif args == "next":
        # Show what's coming next
        idx = state.get("index", 0) % len(_ALL_AMBIENT)
        upcoming = []
        for i in range(5):
            t = _ALL_AMBIENT[(idx + i) % len(_ALL_AMBIENT)]
            upcoming.append(f"{i+1}. [{t['category']}] {t['label']} → {t['brain']}")
        await reply_html(update,
            "<b>🔄 Next 5 Ambient Tasks:</b>\n\n" + "\n".join(upcoming)
        )

    else:  # status
        enabled = "✅ ON" if state.get("enabled", True) else "❌ OFF"
        paused = ""
        if state.get("paused_until"):
            try:
                p = datetime.fromisoformat(state["paused_until"])
                if p > datetime.now():
                    paused = f"\n⏸ Paused until {p.strftime('%H:%M')}"
            except Exception:
                pass
        idx = state.get("index", 0) % len(_ALL_AMBIENT) if _ALL_AMBIENT else 0
        next_task = _ALL_AMBIENT[idx] if _ALL_AMBIENT else {"label": "none", "category": "?"}
        history_count = len(state.get("history", []))
        result_count = len(list(AMBIENT_RESULTS_DIR.glob("*.md")))
        running = "🔴 RUNNING" if _ambient_running else "⚪ idle"

        await reply_html(update,
            f"<b>🔄 Ambient Work System</b>\n\n"
            f"Status: {enabled}{paused}\n"
            f"Engine: {running}\n"
            f"Total tasks in rotation: {len(_ALL_AMBIENT)}\n"
            f"Completed: {history_count}\n"
            f"Results saved: {result_count}\n"
            f"Next up: [{next_task['category']}] {next_task['label']}\n\n"
            f"<b>Commands:</b>\n"
            f"/ambient on — enable\n"
            f"/ambient off — disable\n"
            f"/ambient pause 2 — pause for 2 hours\n"
            f"/ambient results — see recent output\n"
            f"/ambient show — read latest result\n"
            f"/ambient next — see upcoming queue"
        )


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
    app.add_handler(CommandHandler("search", cmd_search))

    # Brain skill commands
    for skill_name in BRAIN_SKILLS:
        app.add_handler(CommandHandler(skill_name, handle_skill_command))

    # Second brain commands
    app.add_handler(CommandHandler("inbox", cmd_inbox))
    app.add_handler(CommandHandler("connections", cmd_connections))
    app.add_handler(CommandHandler("journal", cmd_journal))
    app.add_handler(CommandHandler("digest", cmd_digest))
    app.add_handler(CommandHandler("note", cmd_note))

    # Memory, mailbox, skills commands
    app.add_handler(CommandHandler("remember", cmd_remember))
    app.add_handler(CommandHandler("mail", cmd_mail))
    app.add_handler(CommandHandler("newskill", cmd_newskill))
    app.add_handler(CommandHandler("skills", cmd_skills))

    # Proactive commands
    app.add_handler(CommandHandler("suggest", cmd_suggest))
    app.add_handler(CommandHandler("trends", cmd_trends))
    app.add_handler(CommandHandler("overnight", cmd_overnight))
    app.add_handler(CommandHandler("predict", cmd_predict))
    app.add_handler(CommandHandler("signal", cmd_signal))
    app.add_handler(CommandHandler("ambient", cmd_ambient))

    # Dynamic custom skill commands
    for skill_name in CUSTOM_SKILLS:
        if skill_name not in BRAIN_SKILLS:  # don't shadow built-in skills
            app.add_handler(CommandHandler(skill_name, handle_custom_skill))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Global error handler — stops "No error handlers registered" spam
    app.add_error_handler(error_handler)

    if app.job_queue:
        app.job_queue.run_daily(scheduled_brief, time=time(hour=8, minute=0))
        app.job_queue.run_daily(run_overnight_tasks, time=time(hour=2, minute=0))
        app.job_queue.run_repeating(memory_flush, interval=1800, first=300)  # every 30 min, first at 5 min
        app.job_queue.run_repeating(run_ambient_loop, interval=2700, first=120)  # every 45 min, first at 2 min

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
