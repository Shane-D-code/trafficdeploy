import sqlite3
import os
import json
from datetime import datetime
from pathlib import Path
import numpy as np
import cv2


DB_PATH = Path('traffic_violations.db')
EVIDENCE_DIR = Path('evidence')
DATE_FMT = '%Y-%m-%d'
TIMESTAMP_FMT = '%d %b %Y, %H:%M'


def init_db(db_path=None):
    if db_path is None:
        db_path = str(DB_PATH)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS violations (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            evidence_id    TEXT    UNIQUE,
            timestamp      TEXT    NOT NULL,
            violation_type TEXT    NOT NULL,
            license_plate  TEXT,
            plate_number   TEXT,
            confidence     REAL    NOT NULL,
            image_path     TEXT,
            evidence_path  TEXT,
            location       TEXT
        )
    """)
    conn.commit()
    return conn


def insert_violation(v_type, confidence, plate_number=None, evidence_path=None, image_path=None, location=None, db_path=None):
    conn = init_db(db_path)
    now = datetime.utcnow().isoformat()
    evidence_id = f"EV{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    cur = conn.execute(
        """INSERT INTO violations (evidence_id, timestamp, violation_type, license_plate,
                                   plate_number, confidence, image_path, evidence_path, location)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (evidence_id, now, v_type, plate_number, plate_number, confidence, image_path, evidence_path, location),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id, evidence_id


def save_violation(v_type, plate, confidence, image_path, db_path=None, location=None):
    conn = init_db(db_path)
    now = datetime.utcnow().isoformat()
    evidence_id = f"EV{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    cur = conn.execute(
        """INSERT INTO violations (evidence_id, timestamp, violation_type, license_plate,
                                   plate_number, confidence, image_path, evidence_path, location)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (evidence_id, now, v_type, plate, plate, confidence, image_path, image_path, location),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def get_all_violations(db_path=None):
    conn = init_db(db_path)
    rows = conn.execute(
        "SELECT * FROM violations ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_violations_by_type(v_type, db_path=None):
    conn = init_db(db_path)
    rows = conn.execute(
        "SELECT * FROM violations WHERE violation_type = ? ORDER BY id DESC",
        (v_type,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_violations_by_plate(plate_query, db_path=None):
    conn = init_db(db_path)
    rows = conn.execute(
        "SELECT * FROM violations WHERE plate_number LIKE ? ORDER BY id DESC",
        (f'%{plate_query}%',),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats(db_path=None):
    conn = init_db(db_path)
    total = conn.execute("SELECT COUNT(*) AS cnt FROM violations").fetchone()['cnt']
    by_type_rows = conn.execute(
        "SELECT violation_type, COUNT(*) AS cnt FROM violations GROUP BY violation_type"
    ).fetchall()
    by_type = {r['violation_type']: r['cnt'] for r in by_type_rows}
    by_date_rows = conn.execute(
        "SELECT SUBSTR(timestamp, 1, 10) AS d, COUNT(*) AS cnt "
        "FROM violations GROUP BY d ORDER BY d"
    ).fetchall()
    by_date = {r['d']: r['cnt'] for r in by_date_rows}
    total_vehicles = conn.execute(
        "SELECT COUNT(DISTINCT plate_number) AS cnt FROM violations WHERE plate_number IS NOT NULL"
    ).fetchone()['cnt']
    conn.close()
    return {
        'total': total,
        'by_type': by_type,
        'by_date': by_date,
        'total_vehicles': total_vehicles,
    }


def delete_violation(violation_id, db_path=None):
    conn = init_db(db_path)
    conn.execute("DELETE FROM violations WHERE id = ?", (violation_id,))
    conn.commit()
    conn.close()


def ensure_dirs():
    today = datetime.now().strftime(DATE_FMT)
    dirs = [EVIDENCE_DIR, EVIDENCE_DIR / today, Path('datasets'), Path('reports')]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def save_evidence(image, violation_type):
    try:
        ensure_dirs()
        now = datetime.now()
        date_str = now.strftime(DATE_FMT)
        ts_str   = now.strftime('%H%M%S')
        safe_type = violation_type.replace(' ', '_')
        filename  = f'{ts_str}_{safe_type}.jpg'
        rel_path  = EVIDENCE_DIR / date_str / filename
        rel_path  = rel_path.resolve()
        cv2.imwrite(str(rel_path), image)
        return str(rel_path)
    except Exception:
        return None


def format_timestamp(dt):
    return dt.strftime(TIMESTAMP_FMT)


def confidence_color(conf):
    if conf > 0.85:
        return '#22c55e'
    if conf > 0.65:
        return '#f59e0b'
    return '#ef4444'


if __name__ == '__main__':
    print("=== Initialising database ===")
    init_db()
    print("=== Inserting 3 violations ===")
    save_violation(v_type='NO HELMET', plate='KA01AB1234', confidence=0.92, image_path='evidence/2025-06-19/143022_NO_HELMET.jpg', location='MG Road, Bangalore')
    save_violation(v_type='NO SEATBELT', plate='DL10C5678', confidence=0.74, image_path='evidence/2025-06-19/143105_NO_SEATBELT.jpg', location='Indiranagar, Bangalore')
    save_violation(v_type='TRIPLE RIDING', plate='MH12DE3456', confidence=0.88, image_path='evidence/2025-06-19/143210_TRIPLE_RIDING.jpg')
    print("\n=== All violations ===")
    print(json.dumps(get_all_violations(), indent=2))
    print("\n=== Search by plate 'KA' ===")
    print(json.dumps(search_violations_by_plate('KA'), indent=2))
    print("\n=== Stats ===")
    print(json.dumps(get_stats(), indent=2))
    import shutil as _shutil
    if EVIDENCE_DIR.exists():
        _shutil.rmtree(str(EVIDENCE_DIR))
    if Path('reports').exists():
        _shutil.rmtree(str(Path('reports')))
    print("\nAll utils tests passed.")
