# File: parse_national_cert_catalog.py
# Last Updated: 2026-05-12
# Content Hash: SHA256:TBD
# Role: 국가자격 정보집 PDF → national_cert_catalog.json 변환
#
# 입력: data/raw/pdf/국가정보자격집_20260122-압축됨.pdf
# 출력: data/index_ready/national_cert_catalog.json
#
# 추출 필드: cert_name, purpose(도입목적), exam_fee, career(진로/자격활용),
#            agency(시행기관), ministry(소관부처)
#
# 실행: python -m scripts.parse.parse_national_cert_catalog
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]
PDF_PATH = PROJECT_ROOT / "data/raw/pdf/국가정보자격집_20260122-압축됨.pdf"
OUT_PATH = PROJECT_ROOT / "data/index_ready/national_cert_catalog.json"

CONTENT_START_PAGE = 20  # 0-indexed; 실제 자격 정보는 21페이지(index 20)부터


def _clean(text: str) -> str:
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def _extract_cert_name_and_purpose(text: str) -> tuple[str, str]:
    """cert_name과 도입목적을 분리해 반환.

    페이지 구조:
      [cert_name line(s)] — 공백 없는 한글 단어
      [purpose line(s)]   — 공백 포함 문장
      National Qualification Information / 취득준비
      ...
    """
    boundary = re.search(r'(National Qualification Information|취득준비)', text)
    if not boundary:
        return '', ''

    header = text[:boundary.start()].strip()
    lines = [_clean(l) for l in header.split('\n') if _clean(l)]
    if not lines:
        return '', ''

    name_parts: list[str] = []
    purpose_parts: list[str] = []

    for line in lines:
        if ' ' not in line:
            # No space → part of cert name (e.g. "가축인공", "수정사")
            name_parts.append(line)
        else:
            # Space → purpose or qualifier starts here
            purpose_parts = lines[len(name_parts):]
            break

    cert_name = ''.join(name_parts)

    # Filter out leading qualifier lines that are sub-type lists
    # (e.g. "1, 2, 3급", "일반, 기계") before the real purpose sentence
    real_purpose_parts = []
    for p in purpose_parts:
        # Skip if the line is only category labels (numbers, Korean short labels, commas)
        if re.match(r'^[\d,·\. 급]+$', p):
            continue
        if re.match(r'^[가-힣A-Za-z]{1,8}(?:\s*,\s*[가-힣A-Za-z]{1,8})+$', p):
            continue
        real_purpose_parts.append(p)

    purpose = ' '.join(real_purpose_parts)[:400]
    return cert_name, purpose


def parse_page(text: str, page_idx: int) -> dict | None:
    text = re.sub(r'[ \t]{2,}', ' ', text)

    cert_name, purpose = _extract_cert_name_and_purpose(text)
    if not cert_name or len(cert_name) < 2:
        return None

    # 응시료: "응시료(1차)\n25,000원" 또는 "응시료\n90,000원"
    fee_m = re.search(r'응시료(?:\(1차\))?\s+([^\n]+)', text)
    exam_fee = _clean(fee_m.group(1)) if fee_m else ''

    # 진로(자격활용)
    career_m = re.search(
        r'진로\s*\(자격활용\)\s*[:：]\s*(.*?)(?=\s*시행기관|\s*소관부처|\Z)',
        text,
        re.DOTALL,
    )
    career = ''
    if career_m:
        career = ' '.join(career_m.group(1).split())[:600]

    # 시행기관 (URL 포함)
    agency_m = re.search(r'시행기관\s*[:：]\s*([^\n]+)', text)
    agency = _clean(agency_m.group(1)) if agency_m else ''

    # 소관부처
    ministry_m = re.search(r'소관부처\s*[:：]\s*([^\n]+)', text)
    ministry = _clean(ministry_m.group(1)) if ministry_m else ''

    return {
        'cert_name': cert_name,
        'purpose': purpose,
        'exam_fee': exam_fee,
        'career': career,
        'agency': agency,
        'ministry': ministry,
        'source_page': page_idx + 1,
    }


def parse_pdf(pdf_path: Path) -> list[dict]:
    try:
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTTextContainer
    except ImportError:
        print('pdfminer.six 패키지가 없습니다. pip install pdfminer.six', file=sys.stderr)
        sys.exit(1)

    results: list[dict] = []
    seen: set[str] = set()

    for page_idx, page in enumerate(extract_pages(str(pdf_path))):
        if page_idx < CONTENT_START_PAGE:
            continue

        text = ''.join(
            e.get_text() for e in page
            if isinstance(e, LTTextContainer)
        ).strip()
        if not text:
            continue

        rec = parse_page(text, page_idx)
        if not rec:
            continue

        name = rec['cert_name']
        if name in seen:
            continue
        seen.add(name)
        results.append(rec)

    return results


def build_index(records: list[dict]) -> dict[str, dict]:
    """cert_name → record 인덱스. 공백 정규화 alias도 등록."""
    index: dict[str, dict] = {}
    for rec in records:
        name = rec['cert_name']
        index[name] = rec
        # 괄호 내 한글 별칭 등록 (예: "박물관·미술관학예사")
        m = re.search(r'[(\[（]([^)）\]]+)[)）\]]', name)
        if m:
            alias = m.group(1).strip()
            if alias and alias not in index:
                index[alias] = rec
        # 영문/숫자 제거 후 한글만 등록
        korean_only = re.sub(r'[A-Za-z0-9·\s\(\)\[\]（）]+', '', name).strip()
        if korean_only and korean_only != name and korean_only not in index:
            index[korean_only] = rec
    return index


def main() -> None:
    print(f'파싱 중: {PDF_PATH}')
    if not PDF_PATH.exists():
        print(f'PDF 파일 없음: {PDF_PATH}', file=sys.stderr)
        sys.exit(1)

    records = parse_pdf(PDF_PATH)
    print(f'  → {len(records)}개 자격 추출')

    index = build_index(records)
    print(f'  → {len(index)}개 인덱스 키 생성')

    # Verify some expected entries
    for test_name in ['가축인공수정사', '감정사', '공인노무사']:
        found = '✓' if test_name in index else '✗'
        print(f'  {found} {test_name}')

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'meta': {
            'source': '국가정보자격집_20260122-압축됨.pdf',
            'total_records': len(records),
            'total_index_keys': len(index),
            'generated': '2026-05-12',
        },
        'records': records,
        'index': index,
    }
    with OUT_PATH.open('w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f'저장 완료: {OUT_PATH}')


if __name__ == '__main__':
    main()
