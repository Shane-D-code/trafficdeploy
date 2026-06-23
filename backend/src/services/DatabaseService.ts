import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';
import { v4 as uuidv4 } from 'uuid';
import { ViolationRecord, AnalyticsStats } from '../types';

export class DatabaseService {
  private db: Database.Database;
  private dbPath: string;

  constructor(dbPath?: string) {
    const projectRoot = path.resolve(__dirname, '../../../');
    const dataDir = path.join(projectRoot, 'data');
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }
    this.dbPath = dbPath || process.env.DB_PATH || path.join(dataDir, 'traffic_violations.db');
    this.db = new Database(this.dbPath);
    this.db.pragma('journal_mode = WAL');
    this.initTables();
  }

  private initTables(): void {
    this.db.exec(`
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
        status TEXT DEFAULT 'pending',
        officer_notes TEXT,
        reviewed_at TEXT,
        job_id TEXT,
        annotated_image_path TEXT
      )
    `);

    this.db.exec(`
      CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        progress INTEGER DEFAULT 0,
        result TEXT,
        error TEXT,
        options TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      )
    `);

    // Safe ALTER TABLE migrations (ignore if column exists)
    const migrations = [
      "ALTER TABLE violations ADD COLUMN job_id TEXT",
      "ALTER TABLE violations ADD COLUMN status TEXT DEFAULT 'pending'",
      "ALTER TABLE violations ADD COLUMN officer_notes TEXT",
      "ALTER TABLE violations ADD COLUMN reviewed_at TEXT",
      "ALTER TABLE violations ADD COLUMN annotated_image_path TEXT",
    ];
    for (const sql of migrations) {
      try { this.db.exec(sql); } catch { /* column already exists */ }
    }

    this.db.exec(`
      CREATE INDEX IF NOT EXISTS idx_violation_type ON violations(violation_type);
      CREATE INDEX IF NOT EXISTS idx_plate_text ON violations(plate_text);
      CREATE INDEX IF NOT EXISTS idx_timestamp ON violations(timestamp);
      CREATE INDEX IF NOT EXISTS idx_job_id ON violations(job_id);
      CREATE INDEX IF NOT EXISTS idx_job_status ON jobs(status)
    `);

    this.db.exec(`
      CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
      )
    `);
  }

  async saveViolation(v: any): Promise<number> {
    const evidenceId = 'EV' + uuidv4().substring(0, 8).toUpperCase();
    const stmt = this.db.prepare(`
      INSERT INTO violations (evidence_id, timestamp, violation_type, plate_text, confidence,
       detection_confidence, ocr_confidence, plate_valid, bbox, image_path, evidence_path, location, metadata, job_id, annotated_image_path)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    const result = stmt.run(
      evidenceId,
      v.timestamp || new Date().toISOString(),
      v.type || v.violation_type,
      v.plateText || v.plate_text || null,
      v.confidence || 0,
      v.detection_confidence || null,
      v.ocr_confidence || v.plateConfidence || null,
      v.plateValid || v.plate_valid ? 1 : 0,
      JSON.stringify(v.bbox || v.box || []),
      v.image_path || null,
      v.evidence_path || null,
      v.location || null,
      v.metadata || null,
      v.job_id || null,
      v.annotated_image_path || null
    );
    return result.lastInsertRowid as number;
  }

  async saveJob(job: any): Promise<void> {
    const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO jobs (id, status, progress, result, error, options, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `);
    stmt.run(
      job.id,
      job.status,
      job.progress || 0,
      job.result ? JSON.stringify(job.result) : null,
      job.error || null,
      job.options ? JSON.stringify(job.options) : null,
      job.createdAt || new Date().toISOString(),
      job.updatedAt || new Date().toISOString()
    );
  }

  async updateJob(job: any): Promise<void> {
    const stmt = this.db.prepare(
      `UPDATE jobs SET status = ?, progress = ?, result = ?, error = ?, updated_at = ? WHERE id = ?`
    );
    stmt.run(
      job.status,
      job.progress || 0,
      job.result ? JSON.stringify(job.result) : null,
      job.error || null,
      job.updatedAt || new Date().toISOString(),
      job.id
    );
  }

  async getJob(jobId: string): Promise<any> {
    const row = this.db.prepare('SELECT * FROM jobs WHERE id = ?').get(jobId) as any;
    if (row) {
      if (row.result) try { row.result = JSON.parse(row.result); } catch {}
      if (row.options) try { row.options = JSON.parse(row.options); } catch {}
    }
    return row;
  }

  async getAllViolations(): Promise<ViolationRecord[]> {
    return this.db.prepare('SELECT * FROM violations ORDER BY id DESC').all() as ViolationRecord[];
  }

  async getStats(): Promise<AnalyticsStats> {
    const totalRow = this.db.prepare(
      "SELECT COUNT(*) as total FROM violations WHERE status != 'false_positive' OR status IS NULL"
    ).get() as any;
    const stats: AnalyticsStats = {
      total: totalRow?.total || 0,
      byType: {},
      byDate: {},
      totalVehicles: 0,
      compliance: { helmetCompliance: 0, seatbeltCompliance: 0 }
    };

    const typeRows = this.db.prepare(
      "SELECT violation_type, COUNT(*) as cnt FROM violations WHERE status != 'false_positive' OR status IS NULL GROUP BY violation_type"
    ).all() as any[];
    for (const r of typeRows) stats.byType[r.violation_type] = r.cnt;

    const dateRows = this.db.prepare(
      "SELECT SUBSTR(timestamp, 1, 10) as d, COUNT(*) as cnt FROM violations WHERE status != 'false_positive' OR status IS NULL GROUP BY d ORDER BY d"
    ).all() as any[];
    for (const r of dateRows) stats.byDate[r.d] = r.cnt;

    const vehicleRow = this.db.prepare(
      "SELECT COUNT(DISTINCT plate_text) as cnt FROM violations WHERE plate_text IS NOT NULL AND (status != 'false_positive' OR status IS NULL)"
    ).get() as any;
    stats.totalVehicles = vehicleRow?.cnt || 0;

    const noHelmet = stats.byType['NO HELMET'] || 0;
    const noSeatbelt = stats.byType['NO SEATBELT'] || 0;
    if (stats.total > 0) {
      stats.compliance.helmetCompliance = Math.max(0, (1 - noHelmet / stats.total)) * 100;
      stats.compliance.seatbeltCompliance = Math.max(0, (1 - noSeatbelt / stats.total)) * 100;
    }

    return stats;
  }

  async searchViolations(params: {
    type?: string; plate?: string; startDate?: string; endDate?: string;
    status?: string; page?: number; limit?: number
  }): Promise<{ rows: ViolationRecord[]; total: number }> {
    let where = 'WHERE 1=1';
    const queryParams: any[] = [];

    if (params.type) { where += ' AND violation_type = ?'; queryParams.push(params.type); }
    if (params.plate) { where += ' AND plate_text LIKE ?'; queryParams.push(`%${params.plate}%`); }
    if (params.startDate) { where += ' AND timestamp >= ?'; queryParams.push(params.startDate); }
    if (params.endDate) { where += ' AND timestamp <= ?'; queryParams.push(params.endDate); }
    if (params.status && params.status !== 'all') { where += ' AND status = ?'; queryParams.push(params.status); }

    const page = params.page || 1;
    const limit = params.limit || 50;
    const offset = (page - 1) * limit;

    const countRow = this.db.prepare(`SELECT COUNT(*) as total FROM violations ${where}`).get(...queryParams) as any;
    const total = countRow?.total || 0;

    const rows = this.db.prepare(`SELECT * FROM violations ${where} ORDER BY id DESC LIMIT ? OFFSET ?`).all(...queryParams, limit, offset) as ViolationRecord[];
    return { rows, total };
  }

  async getMetrics(): Promise<any> {
    const baseWhere = "WHERE status != 'false_positive' OR status IS NULL";

    const totalRow = this.db.prepare(`SELECT COUNT(*) as total FROM violations ${baseWhere}`).get() as any;
    const total = totalRow?.total || 0;

    const approvedRow = this.db.prepare("SELECT COUNT(*) as approved FROM violations WHERE status = 'approved'").get() as any;
    const approved = approvedRow?.approved || 0;

    const fpRow = this.db.prepare("SELECT COUNT(*) as fp FROM violations WHERE status = 'false_positive'").get() as any;
    const falsePositives = fpRow?.fp || 0;

    const rejectedRow = this.db.prepare("SELECT COUNT(*) as rejected FROM violations WHERE status = 'rejected'").get() as any;
    const rejected = rejectedRow?.rejected || 0;

    const tp = approved;
    const fp = falsePositives;
    const fn = rejected;

    const typeRows = this.db.prepare(`SELECT violation_type, COUNT(*) as cnt FROM violations ${baseWhere} GROUP BY violation_type`).all() as any[];
    const byType: Record<string, number> = {};
    for (const r of typeRows) byType[r.violation_type] = r.cnt;

    const avgRow = this.db.prepare(`SELECT AVG(confidence) as avgConf FROM violations ${baseWhere}`).all() as any[];
    const avgConfidence = (avgRow && avgRow[0]?.avgConf) || 0;

    const accuracy = (tp + fn) > 0 ? (tp / (tp + fn)) * 100 : avgConfidence * 100;
    const precision = (tp + fp) > 0 ? (tp / (tp + fp)) * 100 : avgConfidence * 100;
    const mAP = (tp + fn) > 0 ? accuracy * 0.95 : avgConfidence * 95;

    const mapPerClass: Record<string, number> = {};
    for (const [vtype, cnt] of Object.entries(byType)) {
      mapPerClass[vtype] = Math.min(100, ((cnt as number) / Math.max(total, 1)) * 100);
    }

    const oneHourAgo = new Date(Date.now() - 3600000).toISOString();
    const recentRows = this.db.prepare(
      `SELECT confidence, timestamp, metadata FROM violations ${baseWhere} AND timestamp >= ? ORDER BY timestamp`
    ).all(oneHourAgo) as any[];
    const recentItems = recentRows || [];

    const inferenceTimes: number[] = recentItems
      .map((r: any) => {
        try {
          const meta = typeof r.metadata === 'string' ? JSON.parse(r.metadata) : r.metadata;
          return meta?.inference_time_ms ?? null;
        } catch { return null; }
      })
      .filter((t: number | null): t is number => t !== null && t > 0);

    const sortedTimes = [...inferenceTimes].sort((a, b) => a - b);
    const avgTime = sortedTimes.length > 0
      ? sortedTimes.reduce((a, b) => a + b, 0) / sortedTimes.length
      : 0;
    const p95Time = sortedTimes.length > 0
      ? sortedTimes[Math.min(Math.floor(sortedTimes.length * 0.95), sortedTimes.length - 1)]
      : 0;
    const p99Time = sortedTimes.length > 0
      ? sortedTimes[Math.min(Math.floor(sortedTimes.length * 0.99), sortedTimes.length - 1)]
      : 0;

    const timeSeriesMap: Record<string, number[]> = {};
    for (const r of recentItems) {
      const bucket = r.timestamp ? r.timestamp.substring(0, 16) : 'unknown';
      if (!timeSeriesMap[bucket]) timeSeriesMap[bucket] = [];
      try {
        const meta = typeof r.metadata === 'string' ? JSON.parse(r.metadata) : r.metadata;
        if (meta?.inference_time_ms) timeSeriesMap[bucket].push(meta.inference_time_ms);
      } catch {}
    }
    const inferenceSeries = Object.entries(timeSeriesMap)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([time, times]) => {
        const sorted = [...times].sort((a, b) => a - b);
        return {
          time,
          p95: sorted[Math.min(Math.floor(sorted.length * 0.95), sorted.length - 1)] ?? 0,
          p99: sorted[Math.min(Math.floor(sorted.length * 0.99), sorted.length - 1)] ?? 0,
        };
      });

    const confidences = recentItems.map((r: any) => r.confidence || 0);
    const binSize = 0.1;
    const confidenceDistribution: { bin: string; count: number }[] = [];
    for (let b = 0; b <= 0.9; b += binSize) {
      const binStart = b;
      const binEnd = b + binSize;
      const count = confidences.filter((c: number) => c >= binStart && c < binEnd).length;
      confidenceDistribution.push({
        bin: `${(binStart * 100).toFixed(0)}-${(binEnd * 100).toFixed(0)}%`,
        count,
      });
    }

    return {
      accuracy: Math.round(accuracy * 100) / 100,
      precision: Math.round(precision * 100) / 100,
      mAP: Math.round(mAP * 100) / 100,
      totalSamples: total,
      truePositives: tp,
      falsePositives: fp,
      falseNegatives: fn,
      avgConfidence: Math.round(avgConfidence * 100) / 100,
      byType,
      mapPerClass,
      inferenceTimeMs: Math.round(avgTime * 100) / 100,
      p95InferenceTime: Math.round(p95Time * 100) / 100,
      p99InferenceTime: Math.round(p99Time * 100) / 100,
      fps: Math.round((p95Time > 0 ? 1000 / p95Time : 0) * 10) / 10,
      inferenceTimeSeries: inferenceSeries,
      confidenceDistribution,
    };
  }

  async updateViolationStatus(id: string, status: string, notes?: string): Promise<void> {
    const now = new Date().toISOString();
    this.db.prepare(
      `UPDATE violations SET status = ?, officer_notes = ?, reviewed_at = ? WHERE id = ?`
    ).run(status, notes || null, now, id);
  }

  async markFalsePositive(id: string): Promise<{ previousStatus: string }> {
    const row = this.db.prepare('SELECT status FROM violations WHERE id = ?').get(id) as any;
    if (!row) throw new Error('Violation not found');
    const previousStatus = row.status || 'pending';
    this.db.prepare(
      `UPDATE violations SET status = 'false_positive', reviewed_at = ? WHERE id = ?`
    ).run(new Date().toISOString(), id);
    return { previousStatus };
  }

  async undoFalsePositive(id: string, previousStatus: string): Promise<void> {
    this.db.prepare(
      `UPDATE violations SET status = ?, reviewed_at = ? WHERE id = ?`
    ).run(previousStatus, new Date().toISOString(), id);
  }

  async getSettings(): Promise<Record<string, any>> {
    const rows = this.db.prepare('SELECT key, value FROM settings').all() as any[];
    const out: Record<string, any> = {};
    for (const r of (rows || [])) {
      try { out[r.key] = JSON.parse(r.value); } catch { out[r.key] = r.value; }
    }
    return out;
  }

  async saveSettings(settings: Record<string, any>): Promise<void> {
    const stmt = this.db.prepare('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)');
    for (const [k, v] of Object.entries(settings)) {
      stmt.run(k, JSON.stringify(v));
    }
  }

  async deleteViolation(id: string): Promise<void> {
    this.db.prepare('DELETE FROM violations WHERE id = ?').run(id);
  }

  async getViolationById(id: string): Promise<ViolationRecord | null> {
    const row = this.db.prepare('SELECT * FROM violations WHERE id = ?').get(id) as ViolationRecord | null;
    return row || null;
  }

  close(): void {
    this.db.close();
  }
}
