# Content Hash: SHA256:TBD
# Role: 공인민간자격 정보자료집 PDF → private_cert_catalog.json 변환
#
# 입력: data/raw/pdf/붙임_2025년_공인민간자격_정보자료집(탑재용).pdf
# 출력: data/index_ready/private_cert_catalog.json
#
# 실행: python -m scripts.parse.parse_private_cert_catalog
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]
PDF_PATH = PROJECT_ROOT / "data/raw/pdf/붙임_2025년_공인민간자격_정보자료집(탑재용).pdf"
OUT_PATH  = PROJECT_ROOT / "data/index_ready/private_cert_catalog.json"

CONTENT_START_PAGE = 4   # 0-indexed; pages 0-3 are cover/TOC/blank


def _clean(text: str) -> str:
    """연속 공백·줄바꿈 정리."""
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def _extract_field(text: str, *patterns: str) -> str:
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return _clean(m.group(1))
    return ''


def _extract_usage(text: str) -> str:
    """'자격 활용 현황' 섹션 추출. + 로 시작하는 줄들."""
    m = re.search(r'자격\s*활용\s*현황(.*?)(?:검정\s*현황|\Z)', text, re.DOTALL)
    if not m:
        return ''
    section = m.group(1)
    lines = [_clean(l) for l in section.split('\n') if _clean(l).startswith('+')]
    return '\n'.join(lines)


def _extract_history(text: str) -> str:
    """검정 현황 최근 3년 숫자 요약 추출."""
    m = re.search(r'검정\s*현황\(최근\s*3년\)(.*?)(?:자격\s*활용|\Z)', text, re.DOTALL)
    if not m:
        return ''
    raw = _clean(m.group(1).replace('\n', ' '))
    return raw[:400]


def _extract_cert_name(text: str) -> str:
    """페이지 첫 번째 비어있지 않은 줄 = 자격명."""
    for line in text.split('\n'):
        line = _clean(line)
        if line:
            return line
    return ''


def parse_pdf(pdf_path: Path) -> list[dict]:
    try:
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTTextContainer
    except ImportError:
        print("pdfminer.six 패키지가 없습니다. pip install pdfminer.six", file=sys.stderr)
        sys.exit(1)

    results: list[dict] = []

    for page_idx, page in enumerate(extract_pages(str(pdf_path))):
        if page_idx < CONTENT_START_PAGE:
            continue

        text = ''.join(
            e.get_text() for e in page
            if isinstance(e, LTTextContainer)
        )
        text = text.strip()
        if not text:
            continue

        cert_name = _extract_cert_name(text)
        if not cert_name:
            continue

        gong_in_no = _extract_field(
            text,
            r'공인번호\s*[:：]\s*([^\n]+)',
        )
        ministry = _extract_field(
            text,
            r'주무부처\s*[:：]?\s*([^\n\d]+)',
        )
        # 숫자로 끝나는 부분(페이지 번호 등) 제거
        ministry = re.sub(r'\s*\d+\s*$', '', ministry).strip()

        exam_fee = _extract_field(
            text,
            r'응시료\s+([^\n]+)',
            r'응시\s*료\s*[:：]\s*([^\n]+)',
        )

        eligibility = _extract_field(
            text,
            r'응시\s*자격\s+([^\n]+)',
            r'응시\s*자격\s*[:：]\s*([^\n]+)',
        )

        validity = _extract_field(
            text,
            r'자격\s*유효기간\s+([^\n]+)',
            r'공인자격\s*유효기간\s+([^\n]+)',
        )

        pass_std = _extract_field(
            text,
            r'합격\s*기준\s+([^\n]+)',
        )

        usage_status = _extract_usage(text)
        exam_history = _extract_history(text)

        results.append({
            'cert_name': cert_name,
            'gong_in_no': _clean(gong_in_no),
            'ministry': _clean(ministry),
            'exam_fee': _clean(exam_fee),
            'eligibility': _clean(eligibility),
            'validity': _clean(validity),
            'pass_standard': _clean(pass_std),
            'usage_status': usage_status,
            'exam_history_summary': exam_history,
            'source_page': page_idx + 1,
        })

    return results


def build_index(records: list[dict]) -> dict[str, dict]:
    """cert_name → record 인덱스. 별칭(괄호 내 영문 포함)도 키로 등록."""
    index: dict[str, dict] = {}
    for rec in records:
        name = rec['cert_name']
        index[name] = rec
        # 괄호 안 별칭도 등록 (예: "IEQ(인터넷윤리자격)" → "인터넷윤리자격")
        m = re.search(r'[(\[（]([^)）\]]+)[)）\]]', name)
        if m:
            alias = m.group(1).strip()
            if alias and alias not in index:
                index[alias] = rec
        # 영문 약어 포함이면 한글 부분도 등록
        korean_only = re.sub(r'[A-Za-z0-9\s\(\)\[\]（）]+', '', name).strip()
        if korean_only and korean_only != name and korean_only not in index:
            index[korean_only] = rec
    return index


def main() -> None:
    print(f"파싱 중: {PDF_PATH}")
    if not PDF_PATH.exists():
        print(f"PDF 파일 없음: {PDF_PATH}", file=sys.stderr)
        sys.exit(1)

    records = parse_pdf(PDF_PATH)
    print(f"  → {len(records)}개 자격 추출")

    index = build_index(records)
    print(f"  → {len(index)}개 인덱스 키 생성")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {'records': records, 'index': index}
    with OUT_PATH.open('w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"저장 완료: {OUT_PATH}")


if __name__ == '__main__':
    main()
