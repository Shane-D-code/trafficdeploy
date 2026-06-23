import os
import tempfile

import pytest

from utils import (
    TempFileManager,
    confidence_color,
    ensure_dirs,
    format_timestamp,
    init_db,
    save_violation,
)
from datetime import datetime


class TestUtils:
    def test_confidence_color(self):
        assert confidence_color(0.9) == "#22c55e"
        assert confidence_color(0.7) == "#f59e0b"
        assert confidence_color(0.5) == "#ef4444"

    def test_format_timestamp(self):
        dt = datetime(2024, 1, 15, 10, 30)
        result = format_timestamp(dt)
        assert "Jan" in result
        assert "2024" in result

    def test_temp_file_manager(self):
        manager = TempFileManager(cleanup_on_exit=False)
        path = manager.create(suffix=".jpg")
        assert os.path.exists(path)
        manager.cleanup()
        assert not os.path.exists(path)

    def test_init_db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn = init_db(db_path)
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cursor.fetchall()]
            assert "violations" in tables
            conn.close()
        finally:
            os.unlink(db_path)

    def test_save_violation(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            row_id = save_violation(
                v_type="NO HELMET",
                plate="KA01AB1234",
                confidence=0.92,
                image_path="/tmp/test.jpg",
                db_path=db_path,
            )
            assert row_id is not None
            assert isinstance(row_id, int)
        finally:
            os.unlink(db_path)
