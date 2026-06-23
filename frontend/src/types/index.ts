export interface Violation {
  id: string;
  type: string;
  confidence: number;
  bbox: [number, number, number, number];
  plateText?: string;
  plateConfidence?: number;
  plateValid?: boolean;
  timestamp: string;
  vehicleType?: string;
  detectionDetails?: string;
  imageUrl?: string;
}

export interface DetectionResult {
  violations: Violation[];
  detections?: Detection[];
  stats: {
    total: number;
    byType: Record<string, number>;
    avgConfidence: number;
    totalPlates: number;
    validPlates: number;
  };
  annotated_image_url?: string;
  frames_processed?: number;
  error?: string;
}

export interface Detection {
  className: string;
  confidence: number;
  bbox: [number, number, number, number];
}

export interface JobStatus {
  success: boolean;
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
  status?: string;
  officer_notes?: string;
  reviewed_at?: string;
  evidence_path?: string;
  image_path?: string;
  bbox?: string;
  metadata?: string;
}

export interface ReportData {
  generatedAt: string;
  totalViolations: number;
  stats: {
    total: number;
    byType: Record<string, number>;
    totalVehicles: number;
    compliance: { helmetCompliance: number; seatbeltCompliance: number };
  };
  violations: Array<{
    id: number;
    type: string;
    plateText: string | null;
    confidence: number;
    timestamp: string;
  }>;
}

export interface Camera {
  id: number;
  name: string;
  status: 'online' | 'offline' | 'warning';
  location: string;
  lat?: number;
  lng?: number;
}

export interface EvidenceItem {
  id: string;
  evidenceId?: string;
  violationType: string;
  plateText: string;
  timestamp: string;
  imageUrl: string;
  annotatedImageUrl?: string;
  confidence: number;
  status?: string;
}

export interface ReviewItem {
  id: string;
  violation_type: string;
  plate_text: string;
  confidence: number;
  image_url: string;
  timestamp: string;
  status?: 'pending' | 'approved' | 'rejected';
  notes?: string;
}

export interface RiskData {
  plate: string;
  risk_score: number;
  risk_level: string;
  violation_count: number;
  recent_violations: number;
  last_violation: string;
}

export interface SummaryData {
  title: string;
  summary: string;
  total: number;
  by_type: Record<string, number>;
  unique_plates: number;
  avg_confidence: number;
  insights: string[];
}

export interface MetricsData {
  accuracy: number;
  precision: number;
  mAP: number;
  totalSamples: number;
  truePositives: number;
  falsePositives: number;
  falseNegatives: number;
  avgConfidence: number;
  byType: Record<string, number>;
  mapPerClass: Record<string, number>;
  inferenceTimeMs: number;
  p95InferenceTime: number;
  p99InferenceTime: number;
  fps: number;
  inferenceTimeSeries: { time: string; p95: number; p99: number }[];
  confidenceDistribution: { bin: string; count: number }[];
}

export interface DangerousJunction {
  location: string;
  lat: number;
  lng: number;
  total: number;
  byType: Record<string, number>;
  severityScore: number;
  heatmapData?: { lat: number; lng: number; weight: number }[];
}

export interface RepeatOffender {
  plate: string;
  count: number;
  types: string[];
  riskScore: number;
  riskLevel: 'low' | 'medium' | 'high';
  firstViolation: string;
  lastViolation: string;
  avgConfidence: number;
  violationHistory?: { timestamp: string; type: string; confidence: number }[];
}

export interface ViolationLocation {
  lat: number;
  lng: number;
  count: number;
  type: string;
  severity: number;
}
