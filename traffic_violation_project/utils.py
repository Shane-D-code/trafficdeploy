"""
utils.py — Utility Functions for Traffic Violation Detection System

SQLite database operations, file management, formatting helpers.
"""

import atexit
import json
import logging
import os
import shutil
import sqlite3
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================
# DATABASE FUNCTIONS
# ============================================

def init_db(db_path: str = 'traffic_violations.db') -> sqlite3.Connection:
    try:
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_id TEXT UNIQUE,
                timestamp TEXT NOT NULL,
                violation_type TEXT NOT NULL,
                plate_text TEXT,
                confidence REAL NOT NULL,
                detection_confidence REAL,
                ocr_confidence REAL,
                plate_valid INTEGER DEFAULT 0,
                bbox TEXT,
                image_path TEXT,
                evidence_path TEXT,
                location TEXT,
                metadata TEXT,
                job_id TEXT
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_violation_type ON violations(violation_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_plate_text ON violations(plate_text)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON violations(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_evidence_id ON violations(evidence_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_id ON violations(job_id)')

        conn.commit()
        logger.info(f"Database initialized: {db_path}")
        return conn

    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        raise


def save_violation(
    v_type: str = None,
    plate: str = None,
    confidence: float = 0.0,
    image_path: str = None,
    db_path: str = None,
    location: str = None,
    violation_type: str = None,
    license_plate: str = None,
    evidence_path: str = None,
    detection_confidence: float = None,
    ocr_confidence: float = None,
    plate_valid: bool = False,
    bbox: List[int] = None,
    metadata: Dict = None,
    job_id: str = None,
) -> int:
    if violation_type is not None:
        v_type = violation_type
    if license_plate is not None:
        plate = license_plate

    if not v_type:
        raise ValueError("violation_type is required")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0.0 and 1.0")

    evidence_id = f"EV_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now().isoformat()
    bbox_json = json.dumps(bbox) if bbox else None
    metadata_json = json.dumps(metadata) if metadata else None
    plate_valid_int = 1 if plate_valid else 0

    if db_path is None:
        db_path = 'traffic_violations.db'

    try:
        conn = init_db(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO violations (
                evidence_id, timestamp, violation_type, plate_text,
                confidence, detection_confidence, ocr_confidence,
                plate_valid, bbox, image_path, evidence_path,
                location, metadata, job_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            evidence_id, timestamp, v_type, plate,
            confidence, detection_confidence, ocr_confidence,
            plate_valid_int, bbox_json, image_path, evidence_path or image_path,
            location, metadata_json, job_id
        ))

        conn.commit()
        violation_id = cursor.lastrowid
        conn.close()

        logger.info(f"Violation saved (ID: {violation_id}, Type: {v_type})")
        return violation_id

    except sqlite3.IntegrityError as e:
        logger.error(f"Integrity error: {e}")
        return save_violation(
            v_type=v_type, plate=plate, confidence=confidence,
            image_path=image_path, db_path=db_path, location=location,
            evidence_path=evidence_path, detection_confidence=detection_confidence,
            ocr_confidence=ocr_confidence, plate_valid=plate_valid,
            bbox=bbox, metadata=metadata, job_id=job_id
        )
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise


def insert_violation(
    v_type, confidence, plate_text=None,
    evidence_path=None, image_path=None, location=None, db_path=None,
):
    return save_violation(
        v_type=v_type, plate=plate_text, confidence=confidence,
        image_path=image_path, db_path=db_path, location=location,
        evidence_path=evidence_path,
    ), f"EV{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def _row_to_dict(row) -> Dict:
    v = dict(row)
    if v.get('bbox'):
        try:
            v['bbox'] = json.loads(v['bbox'])
        except Exception:
            v['bbox'] = None
    if v.get('metadata'):
        try:
            v['metadata'] = json.loads(v['metadata'])
        except Exception:
            v['metadata'] = None
    return v


def _query_violations(query: str, params: list, db_path: str) -> List[Dict[str, Any]]:
    try:
        conn = init_db(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [_row_to_dict(r) for r in rows]
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return []


def get_all_violations(limit: int = None, offset: int = 0, db_path: str = 'traffic_violations.db') -> List[Dict[str, Any]]:
    query = '''
        SELECT id, evidence_id, timestamp, violation_type,
               plate_text, confidence, detection_confidence,
               ocr_confidence, plate_valid, bbox, image_path,
               evidence_path, location, metadata, job_id
        FROM violations ORDER BY timestamp DESC
    '''
    params = []
    if limit is not None:
        query += ' LIMIT ? OFFSET ?'
        params = [limit, offset]
    return _query_violations(query, params, db_path)


def get_violations_by_type(violation_type: str, limit: int = None, db_path: str = 'traffic_violations.db') -> List[Dict[str, Any]]:
    query = '''
        SELECT id, evidence_id, timestamp, violation_type,
               plate_text, confidence, detection_confidence,
               ocr_confidence, plate_valid, bbox, image_path,
               evidence_path, location, metadata, job_id
        FROM violations WHERE violation_type = ?
        ORDER BY timestamp DESC
    '''
    params = [violation_type]
    if limit is not None:
        query += ' LIMIT ?'
        params.append(limit)
    return _query_violations(query, params, db_path)


def search_violations_by_plate(plate_query: str, db_path: str = 'traffic_violations.db') -> List[Dict[str, Any]]:
    return _query_violations('''
        SELECT id, evidence_id, timestamp, violation_type,
               plate_text, confidence, detection_confidence,
               ocr_confidence, plate_valid, bbox, image_path,
               evidence_path, location, metadata, job_id
        FROM violations WHERE plate_text LIKE ?
        ORDER BY timestamp DESC
    ''', [f'%{plate_query}%'], db_path)


def delete_violation(violation_id: int, db_path: str = 'traffic_violations.db') -> None:
    try:
        conn = init_db(db_path)
        conn.execute("DELETE FROM violations WHERE id = ?", (violation_id,))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Delete error: {e}")


def get_stats(db_path: str = 'traffic_violations.db') -> Dict[str, Any]:
    try:
        conn = init_db(db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM violations')
        total = cursor.fetchone()[0]

        cursor.execute('SELECT violation_type, COUNT(*) FROM violations GROUP BY violation_type ORDER BY COUNT(*) DESC')
        by_type = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute('''
            SELECT DATE(timestamp) as d, COUNT(*) as cnt
            FROM violations
            WHERE timestamp >= DATE('now', '-30 days')
            GROUP BY d ORDER BY d DESC
        ''')
        by_date = [{'date': row[0], 'count': row[1]} for row in cursor.fetchall()]

        cursor.execute('SELECT COUNT(DISTINCT plate_text) FROM violations WHERE plate_text IS NOT NULL AND plate_text != \'\'')
        unique_plates = cursor.fetchone()[0] or 0

        cursor.execute('SELECT AVG(confidence) FROM violations')
        avg_confidence = cursor.fetchone()[0] or 0.0

        cursor.execute("SELECT COUNT(*) FROM violations WHERE violation_type = 'NO_HELMET'")
        no_helmet = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM violations WHERE violation_type = 'NO_SEATBELT'")
        no_seatbelt = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM violations WHERE violation_type IN ('NO_HELMET', 'HELMET')")
        total_helmet = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM violations WHERE violation_type IN ('NO_SEATBELT', 'SEATBELT')")
        total_seatbelt = cursor.fetchone()[0] or 0

        helmet_compliance = 1.0 - (no_helmet / total_helmet) if total_helmet > 0 else 0.0
        seatbelt_compliance = 1.0 - (no_seatbelt / total_seatbelt) if total_seatbelt > 0 else 0.0

        cursor.execute('''
            SELECT timestamp, violation_type, plate_text, confidence
            FROM violations ORDER BY timestamp DESC LIMIT 10
        ''')
        recent = [
            {'timestamp': row[0], 'type': row[1], 'plate': row[2] or 'N/A', 'confidence': row[3]}
            for row in cursor.fetchall()
        ]

        conn.close()

        return {
            'total': total,
            'by_type': by_type,
            'by_date': by_date,
            'unique_plates': unique_plates,
            'avg_confidence': round(avg_confidence, 3),
            'compliance': {
                'helmet': round(helmet_compliance, 3),
                'seatbelt': round(seatbelt_compliance, 3),
                'overall': round((helmet_compliance + seatbelt_compliance) / 2, 3),
            },
            'recent': recent,
        }
    except sqlite3.Error as e:
        logger.error(f"Stats error: {e}")
        return {'total': 0, 'by_type': {}, 'by_date': [], 'unique_plates': 0,
                'avg_confidence': 0.0, 'compliance': {'helmet': 0.0, 'seatbelt': 0.0, 'overall': 0.0}, 'recent': []}


# ============================================
# FILE HELPERS
# ============================================

def ensure_dirs(base_dir: str = '') -> Dict[str, str]:
    dirs = {
        'evidence': os.path.join(base_dir, 'evidence'),
        'reports': os.path.join(base_dir, 'reports'),
        'data': os.path.join(base_dir, 'data'),
        'uploads': os.path.join(base_dir, 'uploads'),
        'logs': os.path.join(base_dir, 'logs'),
    }
    for name, path in dirs.items():
        os.makedirs(path, exist_ok=True)

    today = datetime.now().strftime('%Y-%m-%d')
    daily_evidence = os.path.join(dirs['evidence'], today)
    os.makedirs(daily_evidence, exist_ok=True)
    dirs['daily_evidence'] = daily_evidence

    return dirs


def save_evidence(
    image,
    violation_type: str,
    base_dir: str = '',
    timestamp: datetime = None,
) -> Optional[str]:
    try:
        dirs = ensure_dirs(base_dir)
        if timestamp is None:
            timestamp = datetime.now()
        time_str = timestamp.strftime('%H%M%S')
        date_str = timestamp.strftime('%Y-%m-%d')
        safe_type = violation_type.replace(' ', '_').upper()
        filename = f"{time_str}_{safe_type}.jpg"

        daily_dir = os.path.join(dirs['evidence'], date_str)
        os.makedirs(daily_dir, exist_ok=True)
        evidence_path = os.path.join(daily_dir, filename)

        if isinstance(image, str):
            shutil.copy2(image, evidence_path)
        else:
            cv2.imwrite(evidence_path, image)

        return evidence_path
    except Exception as e:
        logger.error(f"Failed to save evidence: {e}")
        return None


def cleanup_temp_files(temp_dir: str = 'uploads', max_age_hours: int = 24) -> int:
    removed_count = 0
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600

    try:
        if not os.path.exists(temp_dir):
            return 0
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    if current_time - os.path.getmtime(file_path) > max_age_seconds:
                        os.remove(file_path)
                        removed_count += 1
                except Exception:
                    pass
        return removed_count
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return 0


# ============================================
# FORMATTING HELPERS
# ============================================

def format_timestamp(dt) -> str:
    if dt is None:
        return 'N/A'
    try:
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        elif isinstance(dt, (int, float)):
            dt = datetime.fromtimestamp(dt)
        return dt.strftime('%d %b %Y, %H:%M:%S')
    except Exception:
        return str(dt)


def confidence_color(confidence: float) -> str:
    if confidence > 0.85:
        return '#22c55e'
    elif confidence > 0.65:
        return '#f59e0b'
    else:
        return '#ef4444'


def confidence_badge(confidence: float) -> Tuple[str, str]:
    if confidence > 0.85:
        return 'High', '#22c55e'
    elif confidence > 0.65:
        return 'Medium', '#f59e0b'
    else:
        return 'Low', '#ef4444'


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


# ============================================
# DATABASE MIGRATION HELPERS
# ============================================

def migrate_database(db_path: str = 'traffic_violations.db') -> bool:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='violations'")
        result = cursor.fetchone()

        if result:
            cursor.execute("PRAGMA table_info(violations)")
            columns = [row[1] for row in cursor.fetchall()]

            new_cols = {
                'detection_confidence': 'REAL',
                'ocr_confidence': 'REAL',
                'plate_valid': 'INTEGER DEFAULT 0',
                'bbox': 'TEXT',
                'metadata': 'TEXT',
                'job_id': 'TEXT',
            }
            for col, col_type in new_cols.items():
                if col not in columns:
                    cursor.execute(f"ALTER TABLE violations ADD COLUMN {col} {col_type}")
                    logger.info(f"Added column: {col}")

            conn.commit()
            conn.close()
            return True
        else:
            init_db(db_path)
            return True
    except sqlite3.Error as e:
        logger.error(f"Migration failed: {e}")
        return False


# ============================================
# TEMP FILE MANAGER
# ============================================

class TempFileManager:
    def __init__(self, max_age_hours=24, cleanup_on_exit=True):
        self.temp_dir = tempfile.mkdtemp(prefix='gridlock_temp_')
        self.max_age_hours = max_age_hours
        self.files = []
        if cleanup_on_exit:
            atexit.register(self.cleanup)

    def create(self, suffix=".jpg"):
        fd, path = tempfile.mkstemp(suffix=suffix, prefix='gridlock_', dir=self.temp_dir)
        os.close(fd)
        self.files.append(path)
        return path

    def create_temp_dir(self, prefix='gridlock_dir_'):
        path = tempfile.mkdtemp(prefix=prefix, dir=self.temp_dir)
        self.files.append(path)
        return path

    def cleanup_file(self, path):
        try:
            if os.path.exists(path):
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                if path in self.files:
                    self.files.remove(path)
                return True
        except Exception:
            pass
        return False

    def cleanup(self):
        for path in self.files[:]:
            self.cleanup_file(path)
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception:
            pass
        self.files.clear()


temp_manager = TempFileManager()


# ============================================
# TEST BLOCK
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING UTILS.PY")
    print("=" * 60)

    db_path = 'test_violations.db'

    print("\n1. Testing Database Initialization...")
    conn = init_db(db_path)
    conn.close()
    print(f"   Database initialized: {db_path}")

    print("\n2. Testing Directory Creation...")
    dirs = ensure_dirs()
    for name, path in dirs.items():
        print(f"   {name}: {path}")

    print("\n3. Testing Formatting Helpers...")
    now = datetime.now()
    print(f"   format_timestamp: {format_timestamp(now)}")
    print(f"   confidence_color(0.92): {confidence_color(0.92)}")
    print(f"   confidence_color(0.75): {confidence_color(0.75)}")
    print(f"   confidence_color(0.50): {confidence_color(0.50)}")
    print(f"   format_duration(3665): {format_duration(3665)}")
    print(f"   format_file_size(1234567): {format_file_size(1234567)}")

    print("\n4. Testing Violation Saving...")
    test_violations = [
        {'v_type': 'NO_HELMET', 'plate': 'KA01AB1234', 'confidence': 0.92,
         'image_path': '/path/to/image1.jpg', 'location': 'MG Road, Bangalore'},
        {'v_type': 'NO_SEATBELT', 'plate': 'MH12CD5678', 'confidence': 0.78,
         'image_path': '/path/to/image2.jpg', 'location': 'Brigade Road, Bangalore'},
        {'v_type': 'TRIPLE_RIDING', 'plate': None, 'confidence': 0.85,
         'image_path': '/path/to/image3.jpg', 'location': 'Church Street, Bangalore'},
    ]

    saved_ids = []
    for v in test_violations:
        violation_id = save_violation(
            v_type=v['v_type'], plate=v['plate'], confidence=v['confidence'],
            image_path=v['image_path'], location=v['location'], db_path=db_path
        )
        saved_ids.append(violation_id)
        print(f"   Saved violation {violation_id}: {v['v_type']} ({v['plate']})")

    print("\n5. Testing Violation Retrieval...")
    all_violations = get_all_violations(db_path=db_path)
    print(f"   Total violations: {len(all_violations)}")
    for v in all_violations:
        print(f"      - {v['id']}: {v['violation_type']} | {v.get('plate_text', 'N/A')} | {v['confidence']:.2f}")

    print("\n6. Testing Type Filtering...")
    helmet_violations = get_violations_by_type('NO_HELMET', db_path=db_path)
    print(f"   Found {len(helmet_violations)} NO_HELMET violations")

    print("\n7. Testing Plate Search...")
    plate_results = search_violations_by_plate('KA01', db_path=db_path)
    print(f"   Found {len(plate_results)} violations with 'KA01'")

    print("\n8. Testing Statistics...")
    stats = get_stats(db_path=db_path)
    print(f"   Total: {stats['total']}")
    print(f"   By Type: {stats['by_type']}")
    print(f"   Unique Plates: {stats['unique_plates']}")
    print(f"   Avg Confidence: {stats['avg_confidence']:.2f}")
    print(f"   Compliance: {stats['compliance']}")

    print("\n9. Testing TempFileManager...")
    tfm = TempFileManager(cleanup_on_exit=False)
    tmp_path = tfm.create(suffix=".jpg")
    print(f"   Temp file created: {tmp_path}")
    assert os.path.exists(tmp_path)
    tfm.cleanup()
    assert not os.path.exists(tmp_path)
    print("   TempFileManager OK")

    print("\n10. Testing Migration...")
    migrate_database(db_path)
    print("   Migration OK")

    print("\n11. Cleaning Up...")
    for d in ['evidence', 'reports', 'data', 'uploads', 'logs']:
        if os.path.exists(d):
            shutil.rmtree(d)
    if os.path.exists(db_path):
        os.remove(db_path)

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
