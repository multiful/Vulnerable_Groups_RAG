// Content Hash: SHA256:<AUTO_HASH_OR_TBD>

export interface CertCandidate {
  row_type: string;
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
  text_for_dense: string;
  text_for_sparse: string;
  valid_from: string | null;
  valid_to: string | null;
  source_ids: string[];
  quality_flags: Record<string, unknown>;
  updated_at: string;
  content_hash: string;
  exam_sessions_per_year?: number | null;
}
