// Content Hash: SHA256:fbedb0e908838cf8b2ddf34880b39f06cece160ddc88cc120db1da10a0fe9557
// 완료된 위험군 진단 결과 + 오늘의 행동 완료 이력을 localStorage에 보존.
// pipelineState.ts(sessionStorage, 탭 닫으면 소멸)와 달리 재방문(다음 날 이후)에도
// "이어서 하기" 경험을 제공하기 위한 영속 저장소.

const HISTORY_KEY = 'didim_user_history_v1';
const HISTORY_TTL_MS = 60 * 24 * 60 * 60 * 1000; // 60일 — 오래된 진단은 재진단 유도

export interface UserHistory {
  lastStage?: string;
  lastStageLabel?: string;
  lastDomainId?: string;
  lastDomainName?: string;
  completedAt?: number;
  actionStreak?: number;
  lastActionDate?: string; // YYYY-MM-DD, 로컬 타임존 기준
  totalActionsCompleted?: number;
}

function _today(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function _yesterday(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** 저장된 사용자 히스토리를 반환. TTL 만료 시 null. */
export function loadUserHistory(): UserHistory | null {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as UserHistory & { savedAt?: number };
    if (data.savedAt && Date.now() - data.savedAt > HISTORY_TTL_MS) {
      localStorage.removeItem(HISTORY_KEY);
      return null;
    }
    return data;
  } catch {
    return null;
  }
}

/** 히스토리를 저장(기존 값과 병합). */
export function saveUserHistory(partial: Partial<UserHistory>): void {
  try {
    const prev = loadUserHistory() ?? {};
    localStorage.setItem(HISTORY_KEY, JSON.stringify({ ...prev, ...partial, savedAt: Date.now() }));
  } catch { /* localStorage 비활성 환경 무시 */ }
}

/** 진단 완료 시 호출 — 재방문 시 "이어서 하기"의 근거가 되는 상태를 남긴다. */
export function recordDiagnosisComplete(stage: string, stageLabel?: string): void {
  saveUserHistory({ lastStage: stage, lastStageLabel: stageLabel, completedAt: Date.now() });
}

/** 관심 도메인 선택 완료 시 호출 — "이어서 하기"가 로드맵/대시보드로 더 정확히 연결되게 한다. */
export function recordDomainSelected(domainId: string, domainName?: string): void {
  saveUserHistory({ lastDomainId: domainId, lastDomainName: domainName });
}

/**
 * 오늘의 행동 완료 체크. 연속 방문(어제 완료 → 오늘 완료)이면 스트릭 +1,
 * 오늘 이미 완료했으면 변화 없음(중복 카운트 방지), 그 외엔 스트릭 1로 리셋.
 */
export function markTodayActionComplete(): UserHistory {
  const prev = loadUserHistory() ?? {};
  const today = _today();
  if (prev.lastActionDate === today) {
    return prev as UserHistory; // 오늘 이미 완료 — 중복 방지
  }
  const continuing = prev.lastActionDate === _yesterday();
  const next: UserHistory = {
    ...prev,
    lastActionDate: today,
    actionStreak: continuing ? (prev.actionStreak ?? 0) + 1 : 1,
    totalActionsCompleted: (prev.totalActionsCompleted ?? 0) + 1,
  };
  saveUserHistory(next);
  return next;
}

/** 오늘 이미 완료했는지 여부. */
export function isTodayActionDone(): boolean {
  const h = loadUserHistory();
  return h?.lastActionDate === _today();
}

/** 히스토리 전체 초기화 (새로 진단하기 선택 시). */
export function clearUserHistory(): void {
  try { localStorage.removeItem(HISTORY_KEY); } catch { /* noop */ }
}
