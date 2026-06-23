"""
review_system.py - Officer Review and Approval Workflow
"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ReviewSystem:
    """
    Complete officer review and approval workflow for violations
    """

    def __init__(self, db_path: str = 'traffic_violations.db'):
        self.db_path = db_path
        self._init_review_table()

    def _init_review_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                violation_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                officer_notes TEXT,
                reviewed_by TEXT,
                reviewed_at TEXT,
                evidence_path TEXT,
                status_history TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (violation_id) REFERENCES violations(id)
            )
        ''')
        conn.commit()
        conn.close()

    def get_pending_reviews(self, limit: int = 50) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT v.*, r.id as review_id, r.status as review_status,
                   r.officer_notes, r.reviewed_by, r.reviewed_at
            FROM violations v
            LEFT JOIN reviews r ON v.id = r.violation_id
            WHERE r.status IS NULL OR r.status = 'pending'
            ORDER BY v.timestamp DESC
            LIMIT ?
        ''', (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def approve_violation(self, violation_id: int, officer_id: str,
                          notes: str = '', evidence_path: str = '') -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM reviews WHERE violation_id = ?', (violation_id,))
            existing = cursor.fetchone()
            now = datetime.now().isoformat()
            history = json.dumps([{'status': 'approved', 'by': officer_id, 'at': now, 'notes': notes}])
            if existing:
                cursor.execute('''
                    UPDATE reviews SET status = 'approved', officer_notes = ?,
                        reviewed_by = ?, reviewed_at = ?, evidence_path = ?,
                        status_history = ?, updated_at = ?
                    WHERE violation_id = ?
                ''', (notes, officer_id, now, evidence_path, history, now, violation_id))
            else:
                cursor.execute('''
                    INSERT INTO reviews
                    (violation_id, status, officer_notes, reviewed_by, reviewed_at, evidence_path, status_history)
                    VALUES (?, 'approved', ?, ?, ?, ?, ?)
                ''', (violation_id, notes, officer_id, now, evidence_path, history))
            conn.commit()
            conn.close()
            logger.info(f"Violation {violation_id} approved by {officer_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to approve violation: {e}")
            return False

    def reject_violation(self, violation_id: int, officer_id: str,
                         reason: str = '') -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            history = json.dumps([{'status': 'rejected', 'by': officer_id, 'at': now, 'reason': reason}])
            cursor.execute('''
                INSERT INTO reviews
                (violation_id, status, officer_notes, reviewed_by, reviewed_at, status_history)
                VALUES (?, 'rejected', ?, ?, ?, ?)
            ''', (violation_id, reason, officer_id, now, history))
            conn.commit()
            conn.close()
            logger.info(f"Violation {violation_id} rejected by {officer_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to reject violation: {e}")
            return False

    def mark_false_positive(self, violation_id: int, officer_id: str,
                            reason: str = '') -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            history = json.dumps([{'status': 'false_positive', 'by': officer_id, 'at': now, 'reason': reason}])
            cursor.execute('''
                INSERT INTO reviews
                (violation_id, status, officer_notes, reviewed_by, reviewed_at, status_history)
                VALUES (?, 'false_positive', ?, ?, ?, ?)
            ''', (violation_id, reason, officer_id, now, history))
            conn.commit()
            conn.close()
            logger.info(f"Violation {violation_id} marked false positive by {officer_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to mark false positive: {e}")
            return False

    def get_review_stats(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT status, COUNT(*) FROM reviews GROUP BY status')
        stats = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return {
            'pending': stats.get('pending', 0),
            'approved': stats.get('approved', 0),
            'rejected': stats.get('rejected', 0),
            'false_positive': stats.get('false_positive', 0),
            'total': sum(stats.values())
        }

    def get_officer_stats(self, officer_id: str) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT status, COUNT(*) FROM reviews
            WHERE reviewed_by = ? GROUP BY status
        ''', (officer_id,))
        stats = {row[0]: row[1] for row in cursor.fetchall()}
        total = sum(stats.values())
        conn.close()
        return {
            'officer_id': officer_id,
            'total_reviewed': total,
            'approved': stats.get('approved', 0),
            'rejected': stats.get('rejected', 0),
            'false_positive': stats.get('false_positive', 0),
            'approval_rate': round(stats.get('approved', 0) / total * 100, 1) if total > 0 else 0
        }
