#!/usr/bin/env python3
"""
upload_voice_corpus.py

Scans a local folder of published LinkedIn PDFs, extracts text,
uploads files to Supabase Storage, and records metadata in Neon DB.

Run once (batch):
    python upload_voice_corpus.py

Watch mode (continuous):
    python upload_voice_corpus.py --watch

Usage with custom folder:
    python upload_voice_corpus.py --folder "C:/path/to/folder" --channel personal_career
"""

import argparse
import hashlib
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from supabase import create_client, Client

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
# Use service_role key for uploads (bypasses RLS). Get it from:
# Supabase Dashboard → Project Settings → API → service_role (secret)
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

BUCKET_NAME = "post-assets"
DEFAULT_FOLDER = r"C:\Users\USER\OneDrive\LinkedIn_PersonalBrand\LinkedInAIPosts\PublishedPost _MachineLearnign"
DEFAULT_CHANNEL = "personal_career"
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_text_from_pdf(path: Path) -> str:
    """Extract text from PDF using pdfplumber."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t.strip())
        return "\n\n".join(text_parts)
    except ImportError:
        print("  [WARN] pdfplumber not installed. Run: pip install pdfplumber")
        return ""
    except Exception as e:
        print(f"  [WARN] PDF text extraction failed: {e}")
        return ""


def extract_text_from_docx(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        print("  [WARN] python-docx not installed. Run: pip install python-docx")
        return ""
    except Exception as e:
        print(f"  [WARN] DOCX text extraction failed: {e}")
        return ""


def extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    elif ext == ".docx":
        return extract_text_from_docx(path)
    elif ext in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    return ""


def storage_path(file_name: str, channel: str) -> str:
    """Build the Supabase Storage path: final/{channel}/YYYY/MM/filename"""
    now = datetime.now(timezone.utc)
    return f"final/{channel}/{now.year}/{now.month:02d}/{file_name}"


# ──────────────────────────────────────────────
# Core logic
# ──────────────────────────────────────────────

def get_db_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def already_uploaded(conn, sha256: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM post_assets WHERE file_sha256 = %s", (sha256,))
        return cur.fetchone() is not None


def upload_file(supabase: Client, local_path: Path, dest_path: str) -> str:
    """Upload file to Supabase Storage, return public URL."""
    with open(local_path, "rb") as f:
        data = f.read()

    # Remove existing file if present (upsert workaround)
    try:
        supabase.storage.from_(BUCKET_NAME).remove([dest_path])
    except Exception:
        pass

    content_type = "application/pdf" if local_path.suffix.lower() == ".pdf" else "text/plain"
    supabase.storage.from_(BUCKET_NAME).upload(
        dest_path,
        data,
        {"content-type": content_type, "upsert": "true"}
    )

    # Build public URL
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{dest_path}"
    return public_url


def insert_neon_row(conn, *, channel: str, file_name: str, file_url: str,
                    file_sha256: str, extracted_text: str, pillar: str = None,
                    topic: str = None, format: str = "Carousel PDF"):
    has_text = bool(extracted_text and extracted_text.strip())
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO post_assets (
                channel, pillar, format, topic, version_label, status,
                storage_provider, file_url, file_name, file_sha256,
                extracted_text, text_extraction_status, voice_ready, source_origin
            ) VALUES (
                %(channel)s, %(pillar)s, %(format)s, %(topic)s, 'v1', 'final',
                'supabase_storage', %(file_url)s, %(file_name)s, %(file_sha256)s,
                %(extracted_text)s, %(text_status)s, %(voice_ready)s, 'local_edit_upload'
            )
            ON CONFLICT (file_sha256) DO NOTHING
            """,
            {
                "channel": channel,
                "pillar": pillar,
                "format": format,
                "topic": topic,
                "file_url": file_url,
                "file_name": file_name,
                "file_sha256": file_sha256,
                "extracted_text": extracted_text if has_text else None,
                "text_status": "done" if has_text else "failed",
                "voice_ready": has_text,
            }
        )
    conn.commit()


def process_file(path: Path, channel: str, supabase: Client, conn) -> bool:
    """Process a single file: extract → upload → record. Returns True if processed."""
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return False

    print(f"\n>> Processing: {path.name}")

    sha256 = sha256_of_file(path)
    if already_uploaded(conn, sha256):
        print(f"  [SKIP] Already in Neon (sha256 match)")
        return False

    # Extract text
    print("  Extracting text...")
    text = extract_text(path)
    word_count = len(text.split()) if text else 0
    print(f"  Extracted {word_count} words")

    # Upload to Supabase Storage
    dest = storage_path(path.name, channel)
    print(f"  Uploading to: {BUCKET_NAME}/{dest}")
    try:
        public_url = upload_file(supabase, path, dest)
        print(f"  URL: {public_url}")
    except Exception as e:
        print(f"  [ERROR] Upload failed: {e}")
        return False

    # Insert Neon row
    print("  Inserting Neon row...")
    try:
        insert_neon_row(
            conn,
            channel=channel,
            file_name=path.name,
            file_url=public_url,
            file_sha256=sha256,
            extracted_text=text,
        )
        print(f"  [OK] voice_ready={'true' if text else 'false'}")
    except Exception as e:
        print(f"  [ERROR] Neon insert failed: {e}")
        conn.rollback()
        return False

    return True


def batch_scan(folder: Path, channel: str, supabase: Client):
    """Scan folder once and process all supported files."""
    conn = get_db_conn()
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    if not files:
        print(f"No supported files found in: {folder}")
        conn.close()
        return

    print(f"Found {len(files)} file(s) to check in: {folder}")
    processed = 0
    for path in sorted(files):
        if process_file(path, channel, supabase, conn):
            processed += 1

    conn.close()
    print(f"\n[DONE] {processed}/{len(files)} file(s) uploaded & recorded.")


def watch_mode(folder: Path, channel: str, supabase: Client):
    """Watch folder for new/changed files and process them."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print("[ERROR] watchdog not installed. Run: pip install watchdog")
        sys.exit(1)

    class Handler(FileSystemEventHandler):
        def __init__(self):
            self.conn = get_db_conn()

        def _handle(self, path_str: str):
            path = Path(path_str)
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                # Brief delay to ensure file write is complete
                time.sleep(1)
                process_file(path, channel, supabase, self.conn)

        def on_created(self, event):
            if not event.is_directory:
                self._handle(event.src_path)

        def on_modified(self, event):
            if not event.is_directory:
                self._handle(event.src_path)

    print(f"Watching: {folder}")
    print("Drop PDF/TXT/MD/DOCX files into the folder to auto-upload. Ctrl+C to stop.\n")

    # Run initial batch scan
    conn = get_db_conn()
    batch_scan(folder, channel, supabase)
    conn.close()

    handler = Handler()
    observer = Observer()
    observer.schedule(handler, str(folder), recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    handler.conn.close()
    print("\nStopped watching.")


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Upload published LinkedIn posts to cloud voice corpus")
    parser.add_argument("--folder", default=DEFAULT_FOLDER, help="Local folder to scan")
    parser.add_argument("--channel", default=DEFAULT_CHANNEL, help="Channel name (e.g. personal_career)")
    parser.add_argument("--watch", action="store_true", help="Enable watch mode (continuous)")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists():
        print(f"[ERROR] Folder not found: {folder}")
        sys.exit(1)

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[ERROR] SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        print("  Get service_role key from: Supabase > Project Settings > API")
        sys.exit(1)

    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL not set in .env")
        sys.exit(1)

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    if args.watch:
        watch_mode(folder, args.channel, supabase)
    else:
        batch_scan(folder, args.channel, supabase)


if __name__ == "__main__":
    main()
