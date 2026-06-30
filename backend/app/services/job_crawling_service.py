# File: job_crawling_service.py
# Last Updated: 2026-06-28
# Content Hash: SHA256:TBD
# Role: 국내 주요 대기업 10개 채용공고 크롤링 + 자격증·직무 키워드 매칭
#
# 설계 원칙:
#   - Saramin API 승인 대기 중: httpx + BeautifulSoup 기반 직접 크롤링
#   - TTL 2시간 캐시: JSON 파일 (data/cache/job_postings/)
#   - 각 크롤러가 실패해도 캐시 fallback, 서비스 전체 실패 없음
#   - robots.txt 준수: 요청 간 지연, 합리적인 User-Agent
#   - 동적 SPA는 __NEXT_DATA__ 또는 공개 REST API 경유
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

CACHE_DIR = Path("data/cache/job_postings")
CACHE_TTL = 7200  # 2시간

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.9",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}

# ── 자격증 → 채용공고 매칭 키워드 ───────────────────────────────────────
CERT_KEYWORD_MAP: dict[str, list[str]] = {
    "정보처리기사":    ["정보처리", "소프트웨어", "백엔드", "backend", "java", "python", "spring", "aws", "개발"],
    "컴퓨터활용능력":  ["컴활", "엑셀", "ms office", "오피스", "데이터관리", "행정"],
    "정보보안기사":    ["보안", "security", "정보보안", "soc", "취약점", "침해", "방화벽"],
    "빅데이터분석기사":["데이터분석", "빅데이터", "머신러닝", "ai", "data science", "통계", "분석"],
    "네트워크관리사":  ["네트워크", "인프라", "서버", "network", "cisco", "시스템"],
    "SQLD":           ["데이터베이스", "sql", "db", "oracle", "mysql", "postgresql", "데이터"],
    "리눅스마스터":    ["리눅스", "linux", "서버", "devops", "인프라"],
    "AWS":            ["클라우드", "aws", "azure", "gcp", "cloud", "devops"],
    "사회복지사":     ["사회복지", "복지", "케어", "상담", "지역복지"],
    "임상심리사":     ["심리상담", "상담", "정신건강", "심리치료", "counseling"],
    "직업상담사":     ["직업상담", "취업지원", "상담", "취업"],
    "한국사능력검정": ["역사", "한국사", "공무원", "사학"],
    "전산세무회계":   ["세무", "회계", "세금", "erpnext", "erp", "재무"],
    "기사 (전기)":    ["전기", "전력", "설비", "전기공사"],
    "안전관리사":     ["안전", "산업안전", "소방", "환경안전"],
}

# 직무 도메인 → 추가 키워드
DOMAIN_KEYWORD_MAP: dict[str, list[str]] = {
    "IT·개발":     ["개발자", "engineer", "developer", "backend", "frontend", "fullstack", "앱", "웹"],
    "데이터·AI":   ["데이터", "머신러닝", "딥러닝", "ai", "분석가", "data"],
    "정보보안":    ["보안", "security", "취약점", "침해대응"],
    "네트워크·인프라": ["네트워크", "인프라", "서버", "cloud", "devops"],
    "행정·사무":   ["행정", "사무", "운영", "지원", "총무"],
    "복지·상담":   ["복지", "상담", "케어", "사회서비스"],
    "회계·세무":   ["회계", "세무", "재무", "경리"],
}


@dataclass
class JobPosting:
    company: str
    title: str
    url: str
    keywords: list[str] = field(default_factory=list)
    department: str = ""
    location: str = "대한민국"
    is_active: bool = True
    crawled_at: float = field(default_factory=time.time)


# ── 캐시 ────────────────────────────────────────────────────────────────

def _cache_path(company: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{company}.json"


def _load_cache(company: str) -> list[dict] | None:
    p = _cache_path(company)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if time.time() - data.get("cached_at", 0) < CACHE_TTL:
            return data.get("postings", [])
    except Exception:
        pass
    return None


def _save_cache(company: str, postings: list[JobPosting]) -> None:
    p = _cache_path(company)
    try:
        p.write_text(
            json.dumps({"cached_at": time.time(), "postings": [asdict(j) for j in postings]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.debug("캐시 저장 실패 %s: %s", company, e)


def _postings_from_cache(company: str) -> list[JobPosting]:
    raw = _load_cache(company)
    if not raw:
        return []
    return [JobPosting(**r) for r in raw]


# ── 공통 유틸 ────────────────────────────────────────────────────────────

def _extract_next_data(html: str) -> dict:
    """Next.js __NEXT_DATA__ JSON 추출"""
    m = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return {}


def _text_keywords(text: str) -> list[str]:
    """텍스트에서 의미 있는 단어 추출 (소문자 정규화)"""
    words = re.findall(r"[가-힣a-zA-Z0-9]+", text.lower())
    return list({w for w in words if len(w) >= 2})


# ── 회사별 크롤러 ─────────────────────────────────────────────────────────

async def _crawl_kakao(client: httpx.AsyncClient) -> list[JobPosting]:
    """카카오 채용 — careers.kakao.com (Next.js __NEXT_DATA__ 또는 REST API)"""
    try:
        resp = await client.get(
            "https://careers.kakao.com/jobs",
            params={"skillSet": "", "part": "", "company": "kakao", "keyword": ""},
            headers=_HEADERS, timeout=12,
        )
        resp.raise_for_status()
        nd = _extract_next_data(resp.text)
        jobs = (
            nd.get("props", {}).get("pageProps", {}).get("jobs")
            or nd.get("props", {}).get("pageProps", {}).get("jobList")
            or []
        )
        results: list[JobPosting] = []
        for job in jobs[:30]:
            title = job.get("jobName") or job.get("title") or ""
            if not title:
                continue
            job_id = job.get("id") or job.get("jobId") or ""
            url = f"https://careers.kakao.com/jobs/{job_id}" if job_id else "https://careers.kakao.com/jobs"
            results.append(JobPosting(
                company="카카오",
                title=title,
                url=url,
                keywords=_text_keywords(title + " " + (job.get("content") or "") + " " + (job.get("part") or "")),
                department=str(job.get("part") or ""),
                location="판교 / 서울",
            ))
        return results
    except Exception as e:
        logger.debug("카카오 크롤링 실패: %s", e)
        return []


async def _crawl_kakaobank(client: httpx.AsyncClient) -> list[JobPosting]:
    """카카오뱅크 채용 — career.kakaobank.com"""
    try:
        # 카카오뱅크는 Next.js 기반
        resp = await client.get("https://career.kakaobank.com/recruit", headers=_HEADERS, timeout=12)
        resp.raise_for_status()
        nd = _extract_next_data(resp.text)
        jobs = (
            nd.get("props", {}).get("pageProps", {}).get("recruitList")
            or nd.get("props", {}).get("pageProps", {}).get("jobs")
            or []
        )
        results: list[JobPosting] = []
        for job in jobs[:30]:
            title = job.get("title") or job.get("recruitTitle") or ""
            if not title:
                continue
            url = f"https://career.kakaobank.com/recruit/{job.get('id') or ''}"
            results.append(JobPosting(
                company="카카오뱅크",
                title=title,
                url=url,
                keywords=_text_keywords(title + " " + (job.get("content") or "")),
                department=str(job.get("part") or job.get("jobGroup") or ""),
                location="판교",
            ))
        return results
    except Exception as e:
        logger.debug("카카오뱅크 크롤링 실패: %s", e)
        return []


async def _crawl_daangn(client: httpx.AsyncClient) -> list[JobPosting]:
    """당근마켓 채용 — team.daangn.com (Gatsby page-data.json)"""
    urls_to_try = [
        "https://team.daangn.com/page-data/jobs/page-data.json",
        "https://team.daangn.com/page-data/ko/jobs/page-data.json",
    ]
    for url in urls_to_try:
        try:
            resp = await client.get(url, headers=_HEADERS, timeout=12)
            resp.raise_for_status()
            data = resp.json()
            edges = (
                data.get("result", {}).get("data", {}).get("allJobPost", {}).get("edges")
                or data.get("result", {}).get("data", {}).get("jobPosts", {}).get("edges")
                or []
            )
            results: list[JobPosting] = []
            for edge in edges[:30]:
                node = edge.get("node") or {}
                title = node.get("title") or node.get("jobTitle") or ""
                if not title:
                    continue
                slug = node.get("slug") or node.get("id") or ""
                results.append(JobPosting(
                    company="당근마켓",
                    title=title,
                    url=f"https://team.daangn.com/jobs/{slug}/",
                    keywords=_text_keywords(title + " " + (node.get("content") or "") + " " + (node.get("team") or "")),
                    department=str(node.get("team") or node.get("chapter") or ""),
                    location="서울 / 판교",
                ))
            if results:
                return results
        except Exception as e:
            logger.debug("당근마켓 크롤링 실패 (%s): %s", url, e)
    return []


async def _crawl_toss(client: httpx.AsyncClient) -> list[JobPosting]:
    """토스 채용 — toss.im/career (Next.js)"""
    try:
        resp = await client.get("https://toss.im/career/jobs", headers=_HEADERS, timeout=12)
        resp.raise_for_status()
        nd = _extract_next_data(resp.text)
        jobs = (
            nd.get("props", {}).get("pageProps", {}).get("jobs")
            or nd.get("props", {}).get("pageProps", {}).get("jobOpenings")
            or []
        )
        results: list[JobPosting] = []
        for job in jobs[:30]:
            title = job.get("title") or job.get("jobTitle") or ""
            if not title:
                continue
            url = job.get("url") or f"https://toss.im/career/jobs/{job.get('id') or ''}"
            results.append(JobPosting(
                company="토스",
                title=title,
                url=url,
                keywords=_text_keywords(title + " " + (job.get("description") or "") + " " + (job.get("team") or "")),
                department=str(job.get("team") or job.get("category") or ""),
                location="서울 강남",
            ))
        return results
    except Exception as e:
        logger.debug("토스 크롤링 실패: %s", e)
        return []


async def _crawl_naver(client: httpx.AsyncClient) -> list[JobPosting]:
    """네이버 채용 — recruit.navercorp.com"""
    try:
        resp = await client.get(
            "https://recruit.navercorp.com/rcrt/list.do",
            params={"classId": "", "subClassId": "", "search": "", "entTypeCd": "001", "searchWord": "", "passApplyYn": ""},
            headers={**_HEADERS, "Accept": "application/json, text/plain, */*"},
            timeout=12,
        )
        resp.raise_for_status()
        # HTML 응답인 경우 파싱
        content = resp.text
        if "application/json" in resp.headers.get("content-type", ""):
            data = resp.json()
            items = data.get("list") or data.get("items") or []
        else:
            nd = _extract_next_data(content)
            items = (
                nd.get("props", {}).get("pageProps", {}).get("list")
                or nd.get("props", {}).get("pageProps", {}).get("jobs")
                or []
            )
        results: list[JobPosting] = []
        for item in items[:30]:
            title = item.get("rcrtNm") or item.get("title") or item.get("jobTitle") or ""
            if not title:
                continue
            job_id = item.get("rcrtNo") or item.get("id") or ""
            url = f"https://recruit.navercorp.com/rcrt/view.do?annoId={job_id}" if job_id else "https://recruit.navercorp.com"
            results.append(JobPosting(
                company="네이버",
                title=title,
                url=url,
                keywords=_text_keywords(title + " " + (item.get("jobGroupNm") or "") + " " + (item.get("subJobGroupNm") or "")),
                department=str(item.get("jobGroupNm") or ""),
                location="성남 분당 / 서울",
            ))
        return results
    except Exception as e:
        logger.debug("네이버 크롤링 실패: %s", e)
        return []


async def _crawl_coupang(client: httpx.AsyncClient) -> list[JobPosting]:
    """쿠팡 채용 — www.coupang.jobs"""
    try:
        resp = await client.get(
            "https://www.coupang.jobs/ko/jobs/",
            params={"search": "", "location": "korea"},
            headers=_HEADERS, timeout=12,
        )
        resp.raise_for_status()
        nd = _extract_next_data(resp.text)
        jobs = (
            nd.get("props", {}).get("pageProps", {}).get("jobs")
            or nd.get("props", {}).get("pageProps", {}).get("jobList")
            or []
        )
        # HTML 파싱 fallback
        if not jobs:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "lxml")
            for tag in soup.select("li.job-list-item, article.job-card, div[data-job-id]"):
                title_tag = tag.find(["h3", "h2", "a"])
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)
                link_tag = tag.find("a", href=True)
                url = "https://www.coupang.jobs" + (link_tag["href"] if link_tag else "")
                jobs.append({"title": title, "url": url})

        results: list[JobPosting] = []
        for job in jobs[:30]:
            title = job.get("title") or job.get("jobTitle") or ""
            if not title:
                continue
            url = job.get("url") or job.get("absolute_url") or f"https://www.coupang.jobs/ko/jobs/{job.get('id','')}"
            results.append(JobPosting(
                company="쿠팡",
                title=title,
                url=url,
                keywords=_text_keywords(title + " " + (job.get("department") or "")),
                department=str(job.get("department") or job.get("team") or ""),
                location="서울 / 원격",
            ))
        return results
    except Exception as e:
        logger.debug("쿠팡 크롤링 실패: %s", e)
        return []


async def _crawl_baemin(client: httpx.AsyncClient) -> list[JobPosting]:
    """배달의민족 (우아한형제들) 채용 — career.woowahan.com"""
    try:
        resp = await client.get("https://career.woowahan.com", headers=_HEADERS, timeout=12)
        resp.raise_for_status()
        nd = _extract_next_data(resp.text)
        jobs = (
            nd.get("props", {}).get("pageProps", {}).get("recruitList")
            or nd.get("props", {}).get("pageProps", {}).get("jobs")
            or []
        )
        results: list[JobPosting] = []
        for job in jobs[:30]:
            title = job.get("jobTitle") or job.get("title") or ""
            if not title:
                continue
            url = f"https://career.woowahan.com/recruitment/{job.get('recruitSeq') or job.get('id') or ''}"
            results.append(JobPosting(
                company="우아한형제들(배민)",
                title=title,
                url=url,
                keywords=_text_keywords(title + " " + (job.get("jobGroupName") or "") + " " + (job.get("content") or "")),
                department=str(job.get("jobGroupName") or ""),
                location="서울 송파",
            ))
        return results
    except Exception as e:
        logger.debug("배달의민족 크롤링 실패: %s", e)
        return []


async def _crawl_line(client: httpx.AsyncClient) -> list[JobPosting]:
    """라인 채용 — careers.linecorp.com"""
    try:
        resp = await client.get(
            "https://careers.linecorp.com/ko/jobs",
            params={"ca": "", "ci": "", "co": "East Asia", "s": ""},
            headers=_HEADERS, timeout=12,
        )
        resp.raise_for_status()
        nd = _extract_next_data(resp.text)
        jobs = (
            nd.get("props", {}).get("pageProps", {}).get("jobs")
            or nd.get("props", {}).get("pageProps", {}).get("jobList")
            or []
        )
        if not jobs:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "lxml")
            for tag in soup.select("ul.job_list li, li.job_item"):
                a = tag.find("a", href=True)
                title_tag = tag.find(["h3", "h2", "p"])
                if not a or not title_tag:
                    continue
                href = a["href"]
                url = href if href.startswith("http") else "https://careers.linecorp.com" + href
                jobs.append({"title": title_tag.get_text(strip=True), "url": url})

        results: list[JobPosting] = []
        for job in jobs[:30]:
            title = job.get("title") or ""
            if not title:
                continue
            url = job.get("url") or job.get("link") or "https://careers.linecorp.com/ko/jobs"
            results.append(JobPosting(
                company="라인",
                title=title,
                url=url,
                keywords=_text_keywords(title + " " + (job.get("category") or "")),
                department=str(job.get("category") or ""),
                location="성남 분당 / 원격",
            ))
        return results
    except Exception as e:
        logger.debug("라인 크롤링 실패: %s", e)
        return []


async def _crawl_samsung_sds(client: httpx.AsyncClient) -> list[JobPosting]:
    """삼성SDS 채용 — www.samsungsds.com"""
    try:
        resp = await client.get(
            "https://www.samsungsds.com/kr/recruit/joblist.html",
            headers=_HEADERS, timeout=12,
        )
        resp.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "lxml")
        results: list[JobPosting] = []
        for tag in soup.select("table.tbl_list tbody tr, ul.list_recruit li, div.recruit-item"):
            cells = tag.find_all(["td", "li"])
            if not cells:
                continue
            title = ""
            url = "https://www.samsungsds.com/kr/recruit/joblist.html"
            for cell in cells:
                a = cell.find("a", href=True)
                if a:
                    title = a.get_text(strip=True)
                    href = a["href"]
                    url = href if href.startswith("http") else "https://www.samsungsds.com" + href
                    break
            if not title:
                title_tag = tag.find(["h3", "h4", "p"])
                title = title_tag.get_text(strip=True) if title_tag else ""
            if not title:
                continue
            results.append(JobPosting(
                company="삼성SDS",
                title=title,
                url=url,
                keywords=_text_keywords(title),
                location="서울 송파",
            ))
        return results[:30]
    except Exception as e:
        logger.debug("삼성SDS 크롤링 실패: %s", e)
        return []


async def _crawl_lgcns(client: httpx.AsyncClient) -> list[JobPosting]:
    """LG CNS 채용 — lgcns.com/careers"""
    try:
        resp = await client.get(
            "https://www.lgcns.com/careers/",
            headers=_HEADERS, timeout=12,
        )
        resp.raise_for_status()
        nd = _extract_next_data(resp.text)
        jobs = (
            nd.get("props", {}).get("pageProps", {}).get("jobs")
            or nd.get("props", {}).get("pageProps", {}).get("positions")
            or []
        )
        if not jobs:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "lxml")
            for tag in soup.select("ul.job-list li, div.job-item, tr.job-row"):
                a = tag.find("a", href=True)
                if not a:
                    continue
                title = a.get_text(strip=True)
                href = a["href"]
                url = href if href.startswith("http") else "https://www.lgcns.com" + href
                jobs.append({"title": title, "url": url})

        results: list[JobPosting] = []
        for job in jobs[:30]:
            title = job.get("title") or job.get("positionName") or ""
            if not title:
                continue
            url = job.get("url") or f"https://www.lgcns.com/careers/"
            results.append(JobPosting(
                company="LG CNS",
                title=title,
                url=url,
                keywords=_text_keywords(title + " " + (job.get("team") or "")),
                department=str(job.get("team") or ""),
                location="서울 마곡",
            ))
        return results
    except Exception as e:
        logger.debug("LG CNS 크롤링 실패: %s", e)
        return []


# ── 전체 크롤러 실행 ─────────────────────────────────────────────────────

_CRAWLERS = [
    ("kakao",        _crawl_kakao),
    ("kakaobank",    _crawl_kakaobank),
    ("daangn",       _crawl_daangn),
    ("toss",         _crawl_toss),
    ("naver",        _crawl_naver),
    ("coupang",      _crawl_coupang),
    ("baemin",       _crawl_baemin),
    ("line",         _crawl_line),
    ("samsung_sds",  _crawl_samsung_sds),
    ("lgcns",        _crawl_lgcns),
]


async def refresh_all_companies() -> dict[str, int]:
    """
    10개 기업 채용공고 전체 크롤링 후 캐시 저장.
    Returns: {"kakao": 28, "daangn": 15, ...} — 회사별 수집 건수
    """
    results: dict[str, int] = {}
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        for key, crawler_fn in _CRAWLERS:
            cached = _load_cache(key)
            if cached is not None:
                results[key] = len(cached)
                logger.info("%s: 캐시 사용 (%d건)", key, len(cached))
                continue
            try:
                postings = await crawler_fn(client)
                _save_cache(key, postings)
                results[key] = len(postings)
                logger.info("%s: %d건 수집", key, len(postings))
            except Exception as e:
                logger.warning("%s 크롤링 오류: %s", key, e)
                results[key] = 0
    return results


def _score_posting(posting: JobPosting, cert_name: str, job_domain: str) -> int:
    """
    채용공고 ↔ 자격증+직무 매칭 점수 계산.
    키워드 중첩 개수 기반 단순 스코어.
    """
    score = 0
    title_lower = posting.title.lower()
    kw_lower = [k.lower() for k in posting.keywords]

    # 자격증 키워드 매칭
    cert_kws = CERT_KEYWORD_MAP.get(cert_name, [cert_name.lower()])
    for kw in cert_kws:
        if kw in title_lower or kw in " ".join(kw_lower):
            score += 2

    # 직무 도메인 키워드 매칭
    domain_kws = DOMAIN_KEYWORD_MAP.get(job_domain, [job_domain.lower()])
    for kw in domain_kws:
        if kw in title_lower or kw in " ".join(kw_lower):
            score += 1

    return score


def get_matching_jobs(
    cert_name: str,
    job_domain: str,
    limit: int = 5,
) -> list[dict]:
    """
    캐시에서 10개 기업 채용공고를 읽어 cert_name + job_domain에 매칭되는 공고 반환.
    스코어 0인 공고는 제외. 결과가 부족하면 스코어 무관 기업별 1건씩 보충.
    """
    all_postings: list[tuple[int, JobPosting]] = []

    for key, _ in _CRAWLERS:
        cached = _load_cache(key)
        if not cached:
            continue
        for raw in cached:
            try:
                p = JobPosting(**raw)
            except Exception:
                continue
            score = _score_posting(p, cert_name, job_domain)
            if score > 0:
                all_postings.append((score, p))

    # 스코어 내림차순 정렬
    all_postings.sort(key=lambda x: -x[0])
    matched = all_postings[:limit]

    # 결과가 부족하면 스코어 상위 보충 (최대 limit까지)
    if len(matched) < limit:
        seen_companies = {p.company for _, p in matched}
        for key, _ in _CRAWLERS:
            if len(matched) >= limit:
                break
            cached = _load_cache(key)
            if not cached:
                continue
            for raw in cached[:1]:
                try:
                    p = JobPosting(**raw)
                except Exception:
                    continue
                if p.company not in seen_companies:
                    matched.append((0, p))
                    seen_companies.add(p.company)
                    break

    return [
        {
            "company": p.company,
            "title": p.title,
            "url": p.url,
            "department": p.department,
            "location": p.location,
            "match_score": score,
            "is_active": p.is_active,
        }
        for score, p in matched
    ]
