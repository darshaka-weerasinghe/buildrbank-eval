"""Send one message to the agent, and name the session it belongs to.

    python scripts/say.py "What is the fee for a wire transfer?" --session kasun-01

The session name is yours to choose. It does two jobs at once: it is the
thread the agent remembers between messages, and it is the name Langfuse
files the trace under. Send the same --session twice and you get a
two-message conversation, in the agent's memory and in Langfuse Sessions.

This exists so that you do not need curl, a JSON body, or a running server
to put one real turn through the agent. It works the same on Windows.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Make this runnable as `python scripts/say.py` from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import settings     # noqa: E402

parser = argparse.ArgumentParser(description="Send one message to the agent.")
parser.add_argument("message", help="what to say to the agent")
parser.add_argument("--session", required=True,
                    help="a name you choose, e.g. yourname-01. Use the same "
                         "one again to continue the conversation.")
parser.add_argument("--email", default=None,
                    help="sign in as a seeded customer, e.g. isuru@example.com")
args = parser.parse_args()

settings.configure()

# Only now is it safe to import the agent - it reads settings on import.
from buildrbank.app import build_app     # noqa: E402

agent = build_app()
try:
    out = agent.turn(user_id=args.session, thread_id=args.session,
                     text=args.message, email=args.email)
finally:
    # Recordings are uploaded in the background. Without this the process
    # can exit before the trace leaves your laptop.
    agent.close()

print()
print(f"  you      {args.message}")
print(f"  agent    {out.reply}")
print()
print(f"  route    {out.route}")
print(f"  session  {args.session}")
print()
host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
print(f"  Find it: {host}  ->  Sessions  ->  {args.session}")
