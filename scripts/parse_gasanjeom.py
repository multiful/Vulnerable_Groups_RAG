# File: scripts/parse_gasanjeom.py
# Last Updated: 2026-05-15
# Content Hash: SHA256:TBD
# Role: 공무원임용시험령 별표12 가산점 자격증 목록 파싱 → gasanjeom_index.json 생성
#
# 입력: data/raw/pdf/level_0008(1).pdf (별표 12, 페이지 3~11)
# 출력: data/index_ready/gasanjeom_index.json
# 구조: { "자격증명": { "직렬": [...], "grade": "기사", "rate_7급": 5, "rate_9급": 3, "source": "별표12" }, ... }
#
# PDF 특성:
#   - 2컬럼 레이아웃: 왼쪽 자격증 목록, 오른쪽 가산비율 주석
#   - 행이 컬럼 너비 내에서 잘려 한 자격증 이름이 여러 줄로 나뉨
#   - 직렬+등급이 같은 줄에 표기되거나 (예: "항공우주 기술사: 기계, ...") 분리됨
#   - pdfplumber bbox 크롭으로 왼쪽 컬럼만 추출

from __future__ import annotations

import json
import re
from pathlib import Path

# ── 상수 ────────────────────────────────────────────────────────────
GRADE_RATES: dict[str, dict[str, int]] = {
    "기술사":   {"rate_7급": 5, "rate_9급": 5},
    "기능장":   {"rate_7급": 5, "rate_9급": 5},
    "기사":     {"rate_7급": 5, "rate_9급": 3},
    "산업기사": {"rate_7급": 3, "rate_9급": 3},
    "기능사":   {"rate_7급": 0, "rate_9급": 3},
}

GRADE_ORDER = ["기술사", "기능장", "기사", "산업기사", "기능사"]

# 등급 헤더: 줄 앞에서 "기사:", "산업기사:", "기능사:" 등
GRADE_ONLY_RE = re.compile(r'^(기술사|기능장|기사|산업기사|기능사)\s*[:：](.*)')

# 직렬+등급 헤더: "항공우주 기술사:", "공업 전기 기사:" 등
# 직렬/직류 이름 목록 (한글 1~5글자)
_SERIAL_NAMES = (
    "공업|농업|수산|산림|해양수산|기상|보건|방역|의료기술|의료기|식품위생|식품위|"
    "환경|시설|디자인|방재안전|방송통신|행정|검찰|교정|보호|철도경찰|세무|관세|"
    "직업상담|사회복지|통계|감사|재경|국제통상|고용노동|문화홍보|교육행정|회계|"
    "축산|생명유전|임업"
)
_JIKRYU_NAMES = (
    "일반기계|운전|항공우주|전기|전자|원자력|조선|금속|섬유|화공|자원|물리|"
    "일반농업|식물검역|축산|생명유전|산림조경|산림자원|산림보호|산림이용|"
    "일반해양|일반수산|어로|수로|해양교통|기상|지진|보건|방역|의료기술|식품위생|"
    "일반환경|수질|대기|폐기물|도시계획|일반토목|농업토목|건축|측지|교통시설|"
    "시설조경|방재안전|통신사|통신기술|전송기술|전자통신기술"
)

SERIAL_GRADE_RE = re.compile(
    rf'^(?:(?:{_SERIAL_NAMES})\s+)?(?:{_JIKRYU_NAMES})\s+(기술사|기능장|기사|산업기사|기능사)\s*[:：](.*)'
)

# 직렬 헤더만 (등급 없이): "공업 일반기계", "농업 축산" 등 — 주로 단독 행
SERIAL_ONLY_RE = re.compile(
    rf'^({_SERIAL_NAMES})\s+(\S+)$'
)

# 가산비율 주석 패턴
SIDE_NOTE_RE = re.compile(
    r'(가산비율적용|가산 비율|자격증 가산|비율적용|비율 적용|직렬|직류|국가기술자격|따른 자격증|법령에|이전 취득)'
)

_PROJECT_ROOT = Path(__file__).parents[1]
_PDF_PATH     = _PROJECT_ROOT / "data" / "raw" / "pdf" / "level_0008(1).pdf"
_CATALOG_JSON = _PROJECT_ROOT / "data" / "index_ready" / "national_cert_catalog.json"
_OUT_JSON     = _PROJECT_ROOT / "data" / "index_ready" / "gasanjeom_index.json"

RIGHT_COL_X = 326.0  # 오른쪽 가산비율 컬럼 시작 x (실측값 ~328 pt에 여유)


# ── PDF 텍스트 추출 ─────────────────────────────────────────────────

def _extract_left_column_lines() -> list[str]:
    """
    pdfplumber word-level 추출로 왼쪽 컬럼(x0 < RIGHT_COL_X)의 단어만 모아
    줄별로 재구성. 페이지 3~11 처리 (0-indexed 2~10).
    """
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        raise ImportError("pdfplumber is required: pip install pdfplumber")

    result_lines: list[str] = []
    with pdfplumber.open(_PDF_PATH) as pdf:
        total = len(pdf.pages)
        for pi in range(2, min(11, total)):
            page = pdf.pages[pi]
            words = page.extract_words(
                x_tolerance=3, y_tolerance=3,
                keep_blank_chars=False, use_text_flow=False,
            )
            left_words = [w for w in words if w["x0"] < RIGHT_COL_X]
            if not left_words:
                continue

            left_words.sort(key=lambda w: (round(w["top"] / 6), w["x0"]))
            lines_by_top: dict[int, list[dict]] = {}
            for w in left_words:
                bucket = round(w["top"] / 6)
                lines_by_top.setdefault(bucket, []).append(w)

            for bucket in sorted(lines_by_top):
                row_words = sorted(lines_by_top[bucket], key=lambda w: w["x0"])
                line_text = " ".join(w["text"] for w in row_words).strip()
                if line_text:
                    result_lines.append(line_text)

    return result_lines


# ── 줄 분류 헬퍼 ───────────────────────────────────────────────────

def _line_type(line: str) -> str:
    """
    'serial_grade'  : 직렬 + 등급 헤더 ("항공우주 기술사: ...")
    'grade_only'    : 등급 헤더만 ("기사: ...")
    'serial_only'   : 직렬/직류 단독 행
    'note'          : 주석/무시 행
    'cert_cont'     : 자격증 이름 연속 행
    """
    s = line.strip()
    if not s or s.startswith("비고") or SIDE_NOTE_RE.search(s):
        return 'note'
    if SERIAL_GRADE_RE.match(s):
        return 'serial_grade'
    if GRADE_ONLY_RE.match(s):
        return 'grade_only'
    if SERIAL_ONLY_RE.match(s):
        return 'serial_only'
    return 'cert_cont'


def _is_section_start(line: str) -> bool:
    lt = _line_type(line)
    return lt in ('serial_grade', 'grade_only', 'serial_only', 'note')


# ── 줄 연속 접합 ───────────────────────────────────────────────────

def _join_wrapped_lines(raw_lines: list[str]) -> list[str]:
    """
    PDF bbox 잘림으로 인해 한 단어가 2줄에 걸쳐 나뉜 것을 복원.
    현재 줄이 쉼표로 끝나지 않고 마지막 문자가 한글/영문/숫자이면
    다음 줄(새 섹션 아닌 경우)의 첫 부분을 직접 이어붙인다.
    """
    joined: list[str] = []
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        while i + 1 < len(raw_lines):
            nxt = raw_lines[i + 1]
            # 다음 줄이 새 섹션이면 중단
            if _is_section_start(nxt):
                break
            tail = line.rstrip()
            if not tail:
                break
            # 쉼표 또는 완성 부호로 끝나면 접합 안 함
            if tail[-1] in (",", "，", "）", ")"):
                break
            # 마지막 문자가 한글/영문/숫자/열린괄호 → 잘린 것
            if re.match(r'[가-힣a-zA-Z0-9\(（]', tail[-1]):
                line = tail + nxt
                i += 1
                continue
            break
        joined.append(line)
        i += 1
    return joined


# ── 자격증 이름 추출 ───────────────────────────────────────────────

def _extract_names(segment: str) -> list[str]:
    names: list[str] = []
    for token in re.split(r'[,，、]', segment):
        name = token.strip().rstrip(".,；;")
        if name and len(name) >= 2:
            names.append(name)
    return names


# ── 메인 파싱 ─────────────────────────────────────────────────────

def parse_gasanjeom() -> dict[str, dict]:
    raw_lines = _extract_left_column_lines()
    lines = _join_wrapped_lines(raw_lines)

    result: dict[str, dict] = {}
    current_serial = ""
    current_jikryu = ""
    i = 0

    while i < len(lines):
        line = lines[i]
        lt = _line_type(line)

        # ── 직렬+등급 헤더 (가장 흔한 패턴) ──
        if lt == 'serial_grade':
            m = SERIAL_GRADE_RE.match(line)
            if m:
                # group(1) = 직렬(optional), group(2) = 직류, group(3) = 등급, group(4) = 첫 이름들
                # 패턴: (?:직렬\s+)?직류\s+등급[:](이름들)
                # 직류는 그룹2, 등급은 그룹3
                # 하지만 optional group이면 그룹 번호가 달라질 수 있음 → 직접 추출
                grade_m = re.search(r'(기술사|기능장|기사|산업기사|기능사)\s*[:：](.*)', line)
                if grade_m:
                    before_grade = line[:line.index(grade_m.group(0))].strip()
                    grade = grade_m.group(1)
                    after_colon = grade_m.group(2).strip()
                    # before_grade = "공업 일반기계" 또는 "항공우주" 등
                    parts = before_grade.split()
                    if len(parts) >= 2:
                        current_serial = parts[0]
                        current_jikryu = parts[1]
                    elif len(parts) == 1:
                        current_jikryu = parts[0]
                    # 이름 수집
                    segments = [after_colon] if after_colon else []
                    j = i + 1
                    while j < len(lines) and not _is_section_start(lines[j]):
                        segments.append(lines[j])
                        j += 1
                    names = _extract_names(" ".join(segments))
                    _add_names(result, names, grade, current_jikryu or current_serial)
                    i = j
                    continue

        # ── 등급 헤더만 ──
        if lt == 'grade_only':
            m = GRADE_ONLY_RE.match(line)
            if m:
                grade = m.group(1)
                after_colon = m.group(2).strip()
                segments = [after_colon] if after_colon else []
                j = i + 1
                while j < len(lines) and not _is_section_start(lines[j]):
                    segments.append(lines[j])
                    j += 1
                names = _extract_names(" ".join(segments))
                _add_names(result, names, grade, current_jikryu or current_serial)
                i = j
                continue

        # ── 직렬 단독 ──
        if lt == 'serial_only':
            m2 = SERIAL_ONLY_RE.match(line)
            if m2:
                current_serial = m2.group(1)
                current_jikryu = m2.group(2)
            i += 1
            continue

        # ── 주석/기타 ──
        i += 1

    return result


def _add_names(
    result: dict[str, dict],
    names: list[str],
    grade: str,
    serial_label: str,
) -> None:
    rates = GRADE_RATES.get(grade, {})
    for short_name in names:
        if not short_name:
            continue
        has_suffix = any(short_name.endswith(g) for g in GRADE_ORDER)
        full_name = short_name if has_suffix else short_name + grade
        if full_name in result:
            if serial_label and serial_label not in result[full_name]["직렬"]:
                result[full_name]["직렬"].append(serial_label)
        else:
            result[full_name] = {
                "직렬": [serial_label] if serial_label else [],
                "grade": grade,
                "rate_7급": rates.get("rate_7급", 0),
                "rate_9급": rates.get("rate_9급", 0),
                "source": "별표12",
            }


# ── 카탈로그 매칭 ─────────────────────────────────────────────────

def _load_catalog_names() -> set[str]:
    if not _CATALOG_JSON.exists():
        return set()
    try:
        with _CATALOG_JSON.open(encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("index", {}).keys())
    except Exception:
        return set()


def _match_with_catalog(
    gasanjeom_raw: dict[str, dict],
    catalog_names: set[str],
) -> dict[str, dict]:
    final: dict[str, dict] = {}
    matched_count = 0

    for raw_name, info in gasanjeom_raw.items():
        if raw_name in catalog_names:
            final[raw_name] = info
            matched_count += 1
            continue

        norm_raw = re.sub(r'[\s\(\)\[\]（）]', '', raw_name).lower()
        matched_key = None
        for cat_name in catalog_names:
            norm_cat = re.sub(r'[\s\(\)\[\]（）]', '', cat_name).lower()
            if norm_raw and norm_cat and (norm_raw == norm_cat or
               norm_raw in norm_cat or norm_cat in norm_raw):
                matched_key = cat_name
                break

        if matched_key:
            if matched_key in final:
                for s in info["직렬"]:
                    if s not in final[matched_key]["직렬"]:
                        final[matched_key]["직렬"].append(s)
            else:
                final[matched_key] = info
            matched_count += 1
        else:
            final[raw_name] = info

    unmatched = len(gasanjeom_raw) - matched_count
    print(f"  총 파싱: {len(gasanjeom_raw)}개 / 카탈로그 매칭: {matched_count}개 / 미매칭: {unmatched}개")
    return final


# ── main ──────────────────────────────────────────────────────────

def main() -> None:
    print(f"PDF 경로: {_PDF_PATH}")
    if not _PDF_PATH.exists():
        print(f"ERROR: PDF 파일이 없습니다: {_PDF_PATH}")
        return

    print("1. 왼쪽 컬럼 추출 및 파싱 중…")
    gasanjeom_raw = parse_gasanjeom()
    print(f"   파싱 완료: {len(gasanjeom_raw)}개 항목")

    spaced = [k for k in gasanjeom_raw if ' ' in k]
    if spaced:
        print(f"   경고: 공백 포함 이름 {len(spaced)}개 (샘플: {spaced[:5]})")
    else:
        print("   공백 포함 이름 없음 (OK)")

    print("2. 카탈로그 매칭 중…")
    catalog_names = _load_catalog_names()
    print(f"   카탈로그 로드: {len(catalog_names)}개")
    final = _match_with_catalog(gasanjeom_raw, catalog_names)

    print("3. 결과 저장 중…")
    _OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with _OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print(f"   저장 완료: {_OUT_JSON}")
    print(f"   총 항목: {len(final)}개")

    samples = list(final.items())[:5]
    print("\n── 샘플 출력 ──")
    for name, info in samples:
        print(f"  {name!r}: grade={info['grade']}, 7급={info['rate_7급']}%, 9급={info['rate_9급']}%, 직렬={info['직렬'][:3]}")

    # 특정 자격증 확인
    test_names = ["자동차정비기사", "일반기계기사", "정보처리기사", "산업안전기사", "전기기사", "정보보안기사"]
    print("\n── 특정 자격증 확인 ──")
    for n in test_names:
        if n in final:
            print(f"  ✓ {n}: {final[n]}")
        else:
            print(f"  ✗ {n}: 없음")


if __name__ == "__main__":
    main()
