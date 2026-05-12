// Content Hash: SHA256:<AUTO_HASH_OR_TBD>
// FE 슬림 JSON 스키마 (scripts/build_frontend_data.py가 생성).
// 무거운 필드(text_for_dense, text_for_sparse, content_hash, source_ids 등)는 서버에만 보관.
// 합격률·검정 횟수는 explicit 필드로 추출됨.

export interface CertCandidate {
  candidate_id: string;
  cert_id: string;
  cert_name: string;
  aliases: string[];
  issuer: string;
  primary_domain: string;
  related_domains: string[];
  related_jobs: string[];
  related_majors: string[];
  recommended_risk_stages: string[];
  roadmap_stages: string[];
  cert_grade_tier: string;
  avg_pass_rate_3yr: number | null;
  exam_sessions_per_year: number | null;

  // Legacy / optional — 슬림 빌드에서는 제거됨. 점진 마이그레이션 위한 옵셔널 유지.
  row_type?: string;
  text_for_dense?: string;
  text_for_sparse?: string;
  valid_from?: string | null;
  valid_to?: string | null;
  source_ids?: string[];
  quality_flags?: Record<string, unknown>;
  updated_at?: string;
  content_hash?: string;
}
