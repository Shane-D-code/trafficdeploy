export interface Violation {
  id: string;
  type: string;
  confidence: number;
  bbox: [number, number, number, number];
  plateText?: string;
  plateConfidence?: number;
  plateValid?: boolean;
  timestamp: string;
}

export interface DetectionResult {
  violations: Violation[];
  stats: {
    total: number;
    byType: Record<string, number>;
    avgConfidence: number;
    totalPlates: number;
    validPlates: number;
  };
}

export interface JobStatus {
  jobId: string;
  status: 'processing' | 'complete' | 'error';
  progress: number;
  message?: string;
  result?: DetectionResult;
}

export interface AnalyticsStats {
  total: number;
  byType: Record<string, number>;
  byDate: Record<string, number>;
  totalVehicles: number;
  compliance: {
    helmetCompliance: number;
    seatbeltCompliance: number;
  };
}

export interface ViolationRecord {
  id: number;
  evidence_id: string;
  timestamp: string;
  violation_type: string;
  plate_text: string | null;
  confidence: number;
  detection_confidence: number | null;
  ocr_confidence: number | null;
  plate_valid: number;
  bbox: string;
  image_path: string | null;
  evidence_path: string | null;
  location: string | null;
  metadata: string | null;
  job_id?: string | null;
  status?: string;
  officer_notes?: string | null;
  reviewed_at?: string | null;
  annotated_image_path?: string | null;
}
