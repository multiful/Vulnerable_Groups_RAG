// Content Hash: SHA256:TBD
// 위험군 진단 → 관심 선택 → 로드맵 → 자격증 확인 파이프라인 상태를 sessionStorage에 보존.
// 페이지 새로고침이나 헤더 내비게이션으로 URL 파라미터가 사라져도 직전 컨텍스트를 복원한다.

const SESSION_KEY = 'didim_pipeline_v1';

export interface PipelineState {
  stage?: string;
  domain?: string;
  domainName?: string;
  job?: string;
  jobName?: string;
}

/** 파이프라인 상태를 저장(기존 값과 병합). */
export function savePipeline(partial: PipelineState): void {
  try {
    const prev = loadPipeline();
    sessionStorage.setItem(SESSION_KEY, JSON.stringify({ ...prev, ...partial }));
  } catch { /* sessionStorage 비활성 환경 무시 */ }
}

/** 저장된 파이프라인 상태를 반환. 없으면 빈 객체. */
export function loadPipeline(): PipelineState {
  try {
    return JSON.parse(sessionStorage.getItem(SESSION_KEY) ?? '{}') as PipelineState;
  } catch {
    return {};
  }
}

/** 파이프라인 상태 전체 초기화 (새 진단 시작 시 호출). */
export function clearPipeline(): void {
  try { sessionStorage.removeItem(SESSION_KEY); } catch { /* noop */ }
}
