import argparse
import json
import os
import re
import smtplib
import sys
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests
from dotenv import load_dotenv


URL_RE = re.compile(r"https?://[^\s<>)\]]+")
AUDIO_EXTENSIONS = (".mp3", ".wav")


@dataclass(frozen=True)
class EmailConfig:
    host: str
    port: int
    user: str
    password: str
    from_addr: str
    to_addr: str
    use_tls: bool


def _load_email_config_from_env() -> EmailConfig:
    load_dotenv()

    host = (os.getenv("SMTP_HOST") or "").strip()
    port_raw = (os.getenv("SMTP_PORT") or "").strip()
    user = (os.getenv("SMTP_USER") or "").strip()
    password = (os.getenv("SMTP_PASSWORD") or "").strip()
    from_addr = (os.getenv("EMAIL_FROM") or "").strip() or user
    to_addr = (os.getenv("EMAIL_TO") or "").strip()
    use_tls_raw = (os.getenv("SMTP_TLS") or "1").strip().lower()

    if not host:
        raise ValueError("Missing SMTP_HOST in .env")
    if not port_raw:
        raise ValueError("Missing SMTP_PORT in .env")
    if not user:
        raise ValueError("Missing SMTP_USER in .env")
    if not password:
        raise ValueError("Missing SMTP_PASSWORD in .env")
    if not to_addr:
        raise ValueError("Missing EMAIL_TO in .env")

    try:
        port = int(port_raw)
    except ValueError as e:
        raise ValueError("SMTP_PORT must be an integer") from e

    use_tls = use_tls_raw not in {"0", "false", "no"}

    return EmailConfig(
        host=host,
        port=port,
        user=user,
        password=password,
        from_addr=from_addr,
        to_addr=to_addr,
        use_tls=use_tls,
    )


def _send_email(cfg: EmailConfig, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg.from_addr
    msg["To"] = cfg.to_addr
    msg.set_content(body)

    with smtplib.SMTP(cfg.host, cfg.port, timeout=20) as server:
        if cfg.use_tls:
            server.starttls()
        server.login(cfg.user, cfg.password)
        server.send_message(msg)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_state(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except Exception:
        return {}
    return {}


def _save_state(path: Path, state: Dict[str, str]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _is_checklist_complete(checklist: dict) -> bool:
    items = checklist.get("checkItems") or []
    if not items:
        return False
    for it in items:
        if (it.get("state") or "").lower() != "complete":
            return False
    return True


def _card_is_complete(card: dict) -> bool:
    checklists = card.get("checklists") or []
    if not checklists:
        return False
    return any(_is_checklist_complete(cl) for cl in checklists)


def _extract_links_from_comments(card: dict) -> List[str]:
    links: List[str] = []
    for act in card.get("actions") or []:
        if act.get("type") != "commentCard":
            continue
        text = ((act.get("data") or {}).get("text") or "").strip()
        if not text:
            continue
        links.extend(URL_RE.findall(text))
    return links


def _extract_links_from_attachments(card: dict) -> List[str]:
    links: List[str] = []
    for att in card.get("attachments") or []:
        url = (att.get("url") or "").strip()
        if url:
            links.append(url)
    return links


def _normalize_links(links: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for l in links:
        l2 = (l or "").strip().rstrip(".,)")
        if not l2 or l2 in seen:
            continue
        seen.add(l2)
        out.append(l2)
    return out


def _audio_links(links: Iterable[str]) -> List[str]:
    out = []
    for l in links:
        ll = l.lower()
        if any(ll.endswith(ext) for ext in AUDIO_EXTENSIONS):
            out.append(l)
    return out


def _download_audio(links: Iterable[str], out_dir: Path) -> List[Tuple[str, str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: List[Tuple[str, str]] = []

    for url in links:
        filename = url.split("?")[0].split("/")[-1]
        if not filename:
            results.append((url, "skip: no filename"))
            continue
        target = out_dir / filename
        if target.exists():
            results.append((url, f"skip: exists ({target.name})"))
            continue

        try:
            r = requests.get(url, timeout=(10, 30), stream=True)
            r.raise_for_status()
            with open(target, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 128):
                    if chunk:
                        f.write(chunk)
            results.append((url, f"ok: saved to {target}"))
        except Exception as e:
            results.append((url, f"error: {e}"))

    return results


def _iter_cards_in_list(data: dict, list_name: str) -> Iterable[dict]:
    cards = (data.get("cards_by_list") or {}).get(list_name) or []
    for c in cards:
        if isinstance(c, dict):
            yield c


def _format_email_body(card: dict, links: List[str], audio_links: List[str], download_results: Optional[List[Tuple[str, str]]]) -> str:
    name = card.get("name") or "(unnamed)"
    url = card.get("shortUrl") or card.get("url") or ""
    due = card.get("due") or ""

    lines: List[str] = []
    lines.append("Checklist completed in Trello")
    lines.append("")
    lines.append(f"Project: {name}")
    if url:
        lines.append(f"Trello: {url}")
    if due:
        lines.append(f"Due: {due}")
    lines.append("")

    if links:
        lines.append("Links found in comments/attachments:")
        for l in links:
            lines.append(f"- {l}")
        lines.append("")

    if audio_links:
        lines.append("Direct audio links (mp3/wav):")
        for l in audio_links:
            lines.append(f"- {l}")
        lines.append("")

    if download_results is not None:
        lines.append("Download results:")
        for url2, status in download_results:
            lines.append(f"- {url2} -> {status}")
        lines.append("")

    lines.append("Note: Dropbox/Google Drive/Mega links may require manual download depending on share settings.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Notify via email when a Trello card checklist becomes complete.")
    parser.add_argument("--json", dest="json_path", default="trello_cards_detailed.json", help="Path to trello_cards_detailed.json")
    parser.add_argument("--state", dest="state_path", default="checklist_notify_state.json", help="State file to avoid duplicate notifications")
    parser.add_argument("--download", action="store_true", help="Attempt to download direct .mp3/.wav links")
    parser.add_argument("--download-dir", dest="download_dir", default="downloads/audio", help="Where to save downloaded audio")
    parser.add_argument("--list", dest="list_name", default="Skripte zur Aufnahme", help="Only process cards from this Trello list")
    args = parser.parse_args()

    json_path = Path(args.json_path)
    state_path = Path(args.state_path)

    if not json_path.exists():
        print(f"ERROR: JSON file not found: {json_path}", file=sys.stderr)
        return 1

    data = _read_json(json_path)
    state = _load_state(state_path)

    completed_cards: List[dict] = []
    for card in _iter_cards_in_list(data, args.list_name):
        card_id = str(card.get("id") or "")
        if not card_id:
            continue
        if not _card_is_complete(card):
            continue

        if state.get(card_id) == "notified":
            continue

        completed_cards.append(card)
        state[card_id] = "notified"

    if not completed_cards:
        return 0

    cfg = _load_email_config_from_env()

    for card in completed_cards:
        links = _normalize_links(_extract_links_from_comments(card) + _extract_links_from_attachments(card))
        audio = _audio_links(links)

        download_results = None
        if args.download and audio:
            download_results = _download_audio(audio, Path(args.download_dir))

        subject = f"Trello checklist complete: {card.get('name','(unnamed)')}"
        body = _format_email_body(card, links, audio, download_results)
        _send_email(cfg, subject=subject, body=body)

    _save_state(state_path, state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
