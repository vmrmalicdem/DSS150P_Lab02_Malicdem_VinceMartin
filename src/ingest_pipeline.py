"""Week 3 starter: rerunnable ingestion to a raw area.
Students implement file ingestion + paginated REST API ingestion + watermark + duplicate prevention.
"""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, shutil, csv, uuid
import requests

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; RAW=ROOT/'raw'; STATE=ROOT/'state'
TEMPLATES=ROOT/'templates'
API_URL='http://127.0.0.1:8000/api/events'
RUN_LOG_PATH = ROOT/'outputs'/'pipeline_run_log.csv'
RUN_LOG_HEADER = [
    'run_id', 'started_at', 'finished_at', 'status', 'source',
    'records_read', 'records_written', 'duplicates_removed',
    'watermark_before', 'watermark_after', 'error_message',
]

def utc_now(): return datetime.now(timezone.utc).isoformat()

def sha256_file(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def load_watermark():
    p=STATE/'api_watermark.json'
    if not p.exists(): return None
    return json.loads(p.read_text())['updated_at']

def save_watermark(value):
    STATE.mkdir(exist_ok=True)
    (STATE/'api_watermark.json').write_text(json.dumps({'updated_at':value},indent=2))


def append_run_log(entry):
    """Append one row to the run log, writing the header first if the file is new."""
    RUN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = RUN_LOG_PATH.exists()
    with RUN_LOG_PATH.open('a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=RUN_LOG_HEADER)
        if not file_exists:
            writer.writeheader()
        writer.writerow(entry)


def ingest_files():
    # Copy CSV/JSON/Parquet to raw/files/ without creating duplicates on rerun.
    # Add manifest entries with source_file, ingested_at, sha256, bytes.
    run_id = str(uuid.uuid4())
    started_at = utc_now()
    records_read = 0
    records_written = 0
    duplicates_removed = 0  # not applicable to files; kept at 0 for log consistency
    status = 'success'
    error_message = ''

    try:
        files_raw = RAW/'files'
        files_raw.mkdir(parents=True, exist_ok=True)
        STATE.mkdir(exist_ok=True)

        manifest_path = STATE/'files_manifest.json'
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
        by_name = {m['source_file']: m for m in manifest}

        targets = ['customers.csv', 'orders.json', 'products.parquet']
        for name in targets:
            src = DATA/name
            if not src.exists():
                print(f"[files] WARNING: {name} not found in {DATA}, skipping")
                continue

            records_read += 1
            digest = sha256_file(src)
            prior = by_name.get(src.name)

            if prior and prior['sha256'] == digest:
                print(f"[files] SKIP {src.name} - unchanged (sha256 matches last ingest)")
                continue

            dest = files_raw/src.name
            shutil.copy2(src, dest)

            entry = {
                'source_file': src.name,
                'ingested_at': utc_now(),
                'sha256': digest,
                'bytes': src.stat().st_size,
            }
            manifest.append(entry)
            by_name[src.name] = entry
            records_written += 1
            print(f"[files] INGESTED {src.name} -> {dest} ({entry['bytes']} bytes)")

        manifest_path.write_text(json.dumps(manifest, indent=2))
        print(f"[files] manifest written: {manifest_path} ({len(manifest)} total entries)")

    except Exception as e:
        status = 'failed'
        error_message = str(e)
        print(f"[files] ERROR: {error_message}")

    finally:
        append_run_log({
            'run_id': run_id,
            'started_at': started_at,
            'finished_at': utc_now(),
            'status': status,
            'source': 'files',
            'records_read': records_read,
            'records_written': records_written,
            'duplicates_removed': duplicates_removed,
            'watermark_before': '',
            'watermark_after': '',
            'error_message': error_message,
        })

    if status == 'failed':
        raise SystemExit(f"[files] ingestion failed: {error_message}")


def fetch_api_page(page, per_page=20, updated_after=None):
    params={'page':page,'per_page':per_page}
    if updated_after: params['updated_after']=updated_after
    try:
        r = requests.get(API_URL, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Could not connect to API at {API_URL}. "
            f"Is local_api_server.py running?"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(f"API request to {API_URL} timed out after 30s.")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"API returned an HTTP error: {e}")


def ingest_api():
    # 1) read watermark
    # 2) follow pagination until has_more=False
    # 3) append ingestion metadata (_ingested_at, _source)
    # 4) deduplicate by event_id keeping greatest updated_at
    # 5) write raw/api/events.jsonl atomically
    # 6) update watermark only after successful write
    run_id = str(uuid.uuid4())
    started_at = utc_now()
    watermark_before = load_watermark()
    watermark_after = watermark_before
    records_read = 0
    records_written = 0
    duplicates_removed = 0
    status = 'success'
    error_message = ''

    try:
        print(f"[api] starting from watermark: {watermark_before}")

        fetched = []
        page = 1
        while True:
            data = fetch_api_page(page, per_page=20, updated_after=watermark_before)
            items = data.get('items', [])
            fetched.extend(items)
            print(f"[api] page {page}: {len(items)} items, has_more={data.get('has_more')}")
            if not data.get('has_more'):
                break
            page += 1

        records_read = len(fetched)
        print(f"[api] fetched {records_read} new/updated records total")

        ingested_at = utc_now()
        for e in fetched:
            e['_ingested_at'] = ingested_at
            e['_source'] = 'api'

        raw_api_dir = RAW/'api'
        raw_api_dir.mkdir(parents=True, exist_ok=True)
        events_path = raw_api_dir/'events.jsonl'

        existing = []
        if events_path.exists():
            with events_path.open() as f:
                for line in f:
                    line = line.strip()
                    if line:
                        existing.append(json.loads(line))

        combined = existing + fetched

        # Deduplicate by event_id, keeping whichever record has the greatest updated_at.
        dedup = {}
        for e in combined:
            eid = e['event_id']
            if eid not in dedup or e['updated_at'] > dedup[eid]['updated_at']:
                dedup[eid] = e

        duplicates_removed = len(combined) - len(dedup)
        final_records = sorted(dedup.values(), key=lambda r: r['event_id'])
        records_written = len(final_records)

        # Atomic write: write to a temp file, then rename over the target.
        # If the process dies mid-write, events.jsonl is untouched (still the old version).
        tmp_path = events_path.with_suffix('.jsonl.tmp')
        with tmp_path.open('w') as f:
            for r in final_records:
                f.write(json.dumps(r) + '\n')
        tmp_path.replace(events_path)

        print(f"[api] wrote {records_written} deduplicated records to {events_path}")
        print(f"[api] {duplicates_removed} duplicate record(s) removed during dedup")

        # Only advance the watermark after the write above has succeeded.
        if fetched:
            max_updated = max(e['updated_at'] for e in fetched)
            if watermark_before is None or max_updated > watermark_before:
                save_watermark(max_updated)
                watermark_after = max_updated
                print(f"[api] watermark advanced to {max_updated}")
            else:
                print(f"[api] watermark unchanged ({watermark_before})")
        else:
            print("[api] no new records fetched; watermark unchanged")

    except Exception as e:
        status = 'failed'
        error_message = str(e)
        print(f"[api] ERROR: {error_message}")

    finally:
        append_run_log({
            'run_id': run_id,
            'started_at': started_at,
            'finished_at': utc_now(),
            'status': status,
            'source': 'api',
            'records_read': records_read,
            'records_written': records_written,
            'duplicates_removed': duplicates_removed,
            'watermark_before': watermark_before if watermark_before else '',
            'watermark_after': watermark_after if watermark_after else '',
            'error_message': error_message,
        })

    if status == 'failed':
        raise SystemExit(f"[api] ingestion failed: {error_message}")


if __name__=='__main__':
    RAW.mkdir(exist_ok=True); STATE.mkdir(exist_ok=True)
    ingest_files(); ingest_api()