#!/usr/bin/env python3
"""
Device-Link Telegram Bridge
Connects Telegram to the device-link agent swarm.

Setup:
  1. Message @BotFather on Telegram, /newbot, get your token
  2. Message your bot, then get your chat ID:
     curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates" | python3 -c "import json,sys; print(json.load(sys.stdin)['result'][0]['message']['chat']['id'])"
  3. Set environment variables:
     export TELEGRAM_BOT_TOKEN="your-token"
     export TELEGRAM_CHAT_ID="your-chat-id"
  4. pip3 install python-telegram-bot[job-queue]
  5. python3 telegram-bridge.py

Commands:
  left: <task>   — dispatch to left brain
  right: <task>  — dispatch to right brain
  both: <task>   — dispatch to both brains
  /status        — swarm health check
  /brief         — daily briefing on demand
  /results       — show recent results
  /help          — show commands
"""

import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime, time
from functools import wraps

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
TRIGGER_SCRIPT = os.environ.get(
    "DEVICE_LINK_TRIGGER",
    str(Path(__file__).resolve().parent.parent / "trigger" / "trigger.sh"),
)

# Tailscale hostnames — update these or set via env
LEFT_HOST = os.environ.get("DEVICE_LINK_LEFT_HOST", "helper-left")
RIGHT_HOST = os.environ.get("DEVICE_LINK_RIGHT_HOST", "helper-right")
SSH_USER = os.environ.get("DEVICE_LINK_USER", os.environ.get("USER", ""))

BRAINS = {
    "left": LEFT_HOST,
    "right": RIGHT_HOST,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
)
logger = logging.getLogger("device-link")


# --- Auth guard ---
def authorized(func):
    """Only respond to the authorized user."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != AUTHORIZED_CHAT_ID:
            await update.message.reply_text("Unauthorized.")
            return
        return await func(update, context)
    return wrapper


# --- Helpers ---
async def ssh_check(host: str) -> str:
    """Check if a host is reachable via SSH."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "ConnectTimeout=3", f"{SSH_USER}@{host}", "echo", "ok",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=5)
        return "online" if proc.returncode == 0 else "unreachable"
    except (asyncio.TimeoutError, Exception):
        return "offline"


async def dispatch_task(brain: str, task: str) -> tuple:
    """Send a task to a brain via the trigger script."""
    proc = await asyncio.create_subprocess_exec(
        "bash", TRIGGER_SCRIPT, brain, task,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
    return proc.returncode, stdout.decode(), stderr.decode()


def get_recent_results(count: int = 5) -> list:
    """Get the most recent result files."""
    if not RESULTS_DIR.exists():
        return []
    files = sorted(RESULTS_DIR.glob("*.md"), key=os.path.getmtime, reverse=True)
    return files[:count]


def truncate(text: str, max_len: int = 3000) -> str:
    """Truncate text to fit Telegram's message limit."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\n...(truncated)"


# --- Command handlers ---
@authorized
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check swarm health."""
    await update.message.reply_text("Checking swarm status...")

    checks = await asyncio.gather(
        ssh_check(LEFT_HOST),
        ssh_check(RIGHT_HOST),
    )

    recent = get_recent_results(3)
    result_lines = []
    for f in recent:
        name = f.stem
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%H:%M")
        result_lines.append(f"  {name} ({mtime})")

    msg = (
        f"Swarm Status\n"
        f"{'=' * 20}\n"
        f"Left brain:  {checks[0]}\n"
        f"Right brain: {checks[1]}\n"
        f"\nRecent results ({len(recent)}):\n"
        + ("\n".join(result_lines) if result_lines else "  (none)")
    )
    await update.message.reply_text(msg)


@authorized
async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send daily briefing on demand."""
    brief = build_daily_brief()
    await update.message.reply_text(brief)


@authorized
async def cmd_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent results."""
    results = get_recent_results(5)
    if not results:
        await update.message.reply_text("No results yet.")
        return

    for f in results:
        content = f.read_text()
        header = f"--- {f.stem} ---\n"
        await update.message.reply_text(truncate(header + content, 3000))


@authorized
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available commands."""
    await update.message.reply_text(
        "Device Link Commands\n"
        "====================\n"
        "left: <task>   - send to left brain\n"
        "right: <task>  - send to right brain\n"
        "both: <task>   - send to both brains\n"
        "/status        - swarm health\n"
        "/brief         - daily briefing\n"
        "/results       - recent results\n"
        "/help          - this message"
    )


@authorized
async def handle_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parse 'left: <task>' or 'right: <task>' and dispatch."""
    text = update.message.text.strip()

    # Parse target:task format
    if ":" not in text:
        await update.message.reply_text(
            "Format: left: <task> or right: <task>\n"
            "Type /help for all commands."
        )
        return

    target, task = text.split(":", 1)
    target = target.strip().lower()
    task = task.strip()

    if not task:
        await update.message.reply_text("No task specified.")
        return

    if target == "both":
        await update.message.reply_text(f"Dispatching to both brains: {task}")
        asyncio.create_task(run_and_notify(update, "left", task))
        asyncio.create_task(run_and_notify(update, "right", task))
        return

    if target not in BRAINS:
        await update.message.reply_text(
            f"Unknown brain: {target}\nAvailable: left, right, both"
        )
        return

    await update.message.reply_text(f"Dispatching to {target}: {task}")
    asyncio.create_task(run_and_notify(update, target, task))


async def run_and_notify(update: Update, brain: str, task: str):
    """Run a task and send the result back to Telegram."""
    try:
        code, stdout, stderr = await dispatch_task(brain, task)
        if code == 0:
            result = truncate(stdout.strip(), 3000) if stdout.strip() else "(no output)"
            await update.message.reply_text(f"{brain} completed:\n{result}")
        else:
            err = truncate(stderr.strip() or stdout.strip(), 2000)
            await update.message.reply_text(f"{brain} failed (exit {code}):\n{err}")
    except asyncio.TimeoutError:
        await update.message.reply_text(f"{brain} timed out (10 min): {task}")
    except Exception as e:
        await update.message.reply_text(f"{brain} error: {e}")


# --- Daily brief ---
def build_daily_brief() -> str:
    """Assemble a morning briefing from recent results."""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"Daily Brief - {today}", "=" * 30, ""]

    results = get_recent_results(10)
    today_results = []
    for r in results:
        mtime = datetime.fromtimestamp(r.stat().st_mtime)
        if mtime.strftime("%Y-%m-%d") == today:
            today_results.append((r, mtime))

    if today_results:
        lines.append(f"Tasks today: {len(today_results)}")
        for r, mtime in today_results:
            lines.append(f"  {r.stem} ({mtime.strftime('%H:%M')})")
    else:
        lines.append("No tasks completed today yet.")

    lines.extend([
        "",
        "Quick commands:",
        "  left: <task>",
        "  right: <task>",
        "  /status",
    ])

    return "\n".join(lines)


async def scheduled_brief(context: ContextTypes.DEFAULT_TYPE):
    """Send the daily brief at the scheduled time."""
    brief = build_daily_brief()
    await context.bot.send_message(
        chat_id=AUTHORIZED_CHAT_ID,
        text=brief,
    )


# --- File watcher for push notifications ---
async def watch_results(app: Application):
    """Watch results directory for new files and push notifications."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    seen = set(f.name for f in RESULTS_DIR.glob("*.md"))

    while True:
        await asyncio.sleep(10)
        try:
            current = set(f.name for f in RESULTS_DIR.glob("*.md"))
            new_files = current - seen
            seen = current

            for fname in new_files:
                fpath = RESULTS_DIR / fname
                content = fpath.read_text()
                preview = content[:500] + ("..." if len(content) > 500 else "")
                msg = f"New result: {fname}\n{preview}"
                await app.bot.send_message(
                    chat_id=AUTHORIZED_CHAT_ID,
                    text=msg,
                )
        except Exception as e:
            logger.error(f"Watch error: {e}")


# --- Main ---
def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    async def post_init(application: Application) -> None:
        """Start file watcher after app initializes."""
        asyncio.create_task(watch_results(application))

    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    # Command handlers
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("brief", cmd_brief))
    app.add_handler(CommandHandler("results", cmd_results))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("start", cmd_help))

    # Free-text message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_task))

    # Schedule daily brief at 8:00 AM
    if app.job_queue:
        app.job_queue.run_daily(
            scheduled_brief,
            time=time(hour=8, minute=0),
        )

    logger.info("Device-Link Telegram bridge starting...")
    logger.info(f"Authorized chat ID: {AUTHORIZED_CHAT_ID}")
    logger.info(f"Left brain: {LEFT_HOST}, Right brain: {RIGHT_HOST}")

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
