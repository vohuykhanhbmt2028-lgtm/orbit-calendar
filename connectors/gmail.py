"""Gmail connector — reads recent emails via IMAP and extracts
calendar invites and commitment mentions.

Requires:
  - GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env
  - 2-Step Verification enabled on the Google account
  - App Password generated at myaccount.google.com/apppasswords
"""

import os
import re
import email
import imaplib
from datetime import datetime, timedelta
from email.header import decode_header

from icalendar import Calendar as ICalendar


# Keywords that suggest an email contains a commitment worth flagging
MENTION_KEYWORDS = [
    "meeting", "invite", "invitation", "deadline", "due",
    "rsvp", "schedule", "appointment", "call at", "session at",
    "interview", "webinar", "office hours",
]

# Phrases we don't want to flag (marketing, notifications, social)
MENTION_EXCLUDE = [
    # Marketing / promo
    "unsubscribe", "newsletter", "sale", "offer ends", "deal ends",
    "limited time", "promo", "sale ends", "flash sale",
    # Account / security
    "verify your email", "confirm your email", "password reset",
    "security alert", "sign-in attempt", "new login", "2fa",
    # Social / networking noise
    "new invitations", "new invitation", "connect", "followed you",
    "is following", "wants to connect", "new message on",
    "you have", "notification", "digest", "weekly roundup",
    # Promotions
    "invited to try", "invited to join", "invited to upgrade",
    "invited to purchase", "invited to view our",
]

# Sender domains/prefixes we ignore — usually automated
NOTIFICATION_SENDER_MARKERS = [
    "notification", "notifications", "no-reply", "noreply",
    "donotreply", "donot-reply", "linkedin", "facebook", "twitter",
    "instagram", "medium", "substack", "meetup", "pinterest",
    "quora", "reddit", "quora", "do_not_reply",
]


class GmailConnector:
    IMAP_HOST = "imap.gmail.com"

    def __init__(self):
        self.address = os.getenv("GMAIL_ADDRESS", "").strip()
        self.password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
        if not self.address or not self.password:
            raise RuntimeError(
                "GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set in .env."
            )

    # ------------------------------------------------------------------
    def fetch_recent(self, days_back=14):
        """Fetch emails from the last N days.

        Returns:
            {
              'invites':  [ {summary, start, end, location, uid}, ... ],
              'mentions': [ {subject, sender, date, uid}, ... ],
            }
        """
        since = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")

        mail = imaplib.IMAP4_SSL(self.IMAP_HOST)
        try:
            mail.login(self.address, self.password)
        except imaplib.IMAP4.error as e:
            raise RuntimeError(f"Gmail login failed: {e}")

        invites = []
        mentions = []

        try:
            mail.select("INBOX", readonly=True)
            status, data = mail.search(None, f'(SINCE {since})')
            if status != "OK":
                return {"invites": [], "mentions": []}

            uids = data[0].split()
            for uid_bytes in uids:
                try:
                    status, msg_data = mail.fetch(uid_bytes, "(RFC822)")
                    if status != "OK" or not msg_data:
                        continue
                    raw = msg_data[0][1]
                    if not isinstance(raw, bytes):
                        continue

                    msg = email.message_from_bytes(raw)
                    self._process_message(msg, uid_bytes.decode(),
                                          invites, mentions)
                except Exception:
                    continue
        finally:
            try:
                mail.close()
            except Exception:
                pass
            try:
                mail.logout()
            except Exception:
                pass

        return {"invites": invites, "mentions": mentions}

    # ------------------------------------------------------------------
    def _process_message(self, msg, uid, invites, mentions):
        subject = _decode_header(msg.get("Subject", ""))
        sender = _decode_header(msg.get("From", ""))
        date_hdr = msg.get("Date", "")

        has_ics = False

        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type in ("text/calendar", "application/ics"):
                has_ics = True
                payload = part.get_payload(decode=True)
                if payload:
                    self._parse_ics(payload, invites)

        if not has_ics:
            subj_l = subject.lower()
            from_l = sender.lower()

            is_match = any(k in subj_l for k in MENTION_KEYWORDS)
            is_excluded = any(k in subj_l for k in MENTION_EXCLUDE)
            is_auto_sender = any(s in from_l
                                 for s in NOTIFICATION_SENDER_MARKERS)

            if is_match and not is_excluded and not is_auto_sender:
                mentions.append({
                    "uid": uid,
                    "subject": subject[:120],
                    "from": sender[:80],
                    "date": _normalize_date(date_hdr),
                })

    # ------------------------------------------------------------------
    def _parse_ics(self, payload, invites):
        try:
            cal = ICalendar.from_ical(payload)
        except Exception:
            return

        for component in cal.walk():
            if component.name != "VEVENT":
                continue
            try:
                dtstart = component.get("dtstart")
                dtend = component.get("dtend")
                if dtstart is None:
                    continue

                start = dtstart.dt
                end = dtend.dt if dtend is not None else None

                # Skip all-day events (date, not datetime)
                if not isinstance(start, datetime):
                    continue

                summary = str(component.get("summary", "Untitled event"))
                location = str(component.get("location", "") or "")
                uid = str(component.get("uid", "") or "")

                invites.append({
                    "uid": uid,
                    "summary": summary,
                    "start": start.isoformat(),
                    "end": end.isoformat() if end else None,
                    "location": location,
                })
            except Exception:
                continue


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _decode_header(value):
    if not value:
        return ""
    try:
        parts = decode_header(value)
        decoded = []
        for text, charset in parts:
            if isinstance(text, bytes):
                decoded.append(text.decode(charset or "utf-8", errors="replace"))
            else:
                decoded.append(text)
        return "".join(decoded).strip()
    except Exception:
        return str(value)


def _normalize_date(value):
    if not value:
        return ""
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(value)
        return dt.isoformat()
    except Exception:
        return value


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    print("Connecting to Gmail...")
    conn = GmailConnector()
    result = conn.fetch_recent(days_back=14)

    invites = result["invites"]
    mentions = result["mentions"]

    print(f"\nCalendar invites ({len(invites)}):")
    for inv in invites[:10]:
        print(f"  {inv['start'][:16]}  {inv['summary'][:60]}")

    print(f"\nKeyword mentions ({len(mentions)}):")
    for m in mentions[:10]:
        print(f"  {m['date'][:16]}  {m['subject'][:60]}")
        print(f"       from: {m['from']}")

    if len(invites) > 10:
        print(f"  ... and {len(invites) - 10} more invites")
    if len(mentions) > 10:
        print(f"  ... and {len(mentions) - 10} more mentions")