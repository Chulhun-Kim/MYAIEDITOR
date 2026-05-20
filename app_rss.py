# app_rss.py
# ------------------------------------------------------------
# RSS 수집 모듈 (Streamlit UI 컴포넌트 + RSS 파싱/정규화)
# 핵심: Streamlit rerun 구조 때문에 "RSS 불러오기" 결과를 session_state에 캐시해
#       다음 rerun(Workspace/Buffer 반영 버튼 클릭)에서도 값이 유지되게 함.
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
import datetime as dt
import re

import streamlit as st

try:
    import requests
except Exception:
    requests = None

try:
    import feedparser
except Exception:
    feedparser = None


# ----------------------------
# 데이터 구조
# ----------------------------
@dataclass
class RssItem:
    title: str
    link: str
    published: str
    summary: str
    source: str
    fetched_at: str


def _now_iso() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _clean_text(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _extract_entry_text(entry) -> str:
    """
    feedparser entry에서 summary/content를 최대한 뽑아냄.
    """
    summary = ""
    if hasattr(entry, "summary"):
        summary = entry.summary or ""
    if not summary and hasattr(entry, "description"):
        summary = entry.description or ""

    # content 우선
    if hasattr(entry, "content") and entry.content:
        try:
            summary = entry.content[0].get("value", "") or summary
        except Exception:
            pass
    return _clean_text(summary)

def _extract_published(entry) -> str:
    if hasattr(entry, "published") and entry.published:
        return _clean_text(entry.published)
    if hasattr(entry, "updated") and entry.updated:
        return _clean_text(entry.updated)

    for k in ("published_parsed", "updated_parsed"):
        t = getattr(entry, k, None)
        if t:
            try:
                d = dt.datetime(*t[:6])
                return d.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass

    return ""

def fetch_rss_items(
    feed_url: str,
    source_name: str,
    limit: int = 20,
    timeout: int = 20,
) -> List[RssItem]:
    """
    RSS URL을 파싱해 RssItem 리스트로 반환

    보완 내용:
    1. Streamlit Cloud에서 차단을 줄이기 위해 브라우저처럼 보이는 headers 사용
    2. requests 방식 실패 시 feedparser.parse(url)로 한 번 더 재시도
    3. 빈 RSS 결과와 연결 오류를 구분해 메시지 표시
    """
    if feedparser is None:
        raise RuntimeError("feedparser가 설치되어 있지 않습니다. pip install feedparser")

    fetched_at = _now_iso()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "close",
    }

    parsed = None
    last_error = None

    # ------------------------------------------------------------
    # 1차 시도: requests로 RSS 원문을 가져온 뒤 feedparser로 파싱
    # ------------------------------------------------------------
    if requests is not None:
        try:
            resp = requests.get(
                feed_url,
                timeout=timeout,
                headers=headers,
            )
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)

        except Exception as e:
            last_error = e

    # ------------------------------------------------------------
    # 2차 시도: requests 실패 시 feedparser가 URL을 직접 읽도록 재시도
    # ------------------------------------------------------------
    if parsed is None:
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as e:
            last_error = e

    # ------------------------------------------------------------
    # 그래도 실패한 경우
    # ------------------------------------------------------------
    if parsed is None:
        raise RuntimeError(f"RSS 수집 실패: {last_error}")

    entries = getattr(parsed, "entries", []) or []

    # feedparser는 실패해도 parsed 객체를 반환할 수 있으므로 bozo 체크
    bozo = getattr(parsed, "bozo", False)
    bozo_exception = getattr(parsed, "bozo_exception", None)

    if not entries:
        if last_error:
            raise RuntimeError(
                f"RSS 항목을 가져오지 못했습니다. 원인: {last_error}"
            )

        if bozo and bozo_exception:
            raise RuntimeError(
                f"RSS 파싱은 되었지만 항목이 없습니다. 원인: {bozo_exception}"
            )

        raise RuntimeError(
            "RSS 항목이 없습니다. RSS 주소가 맞는지, 해당 사이트가 RSS 제공을 중단했는지 확인하세요."
        )

    items: List[RssItem] = []

    for e in entries[:limit]:
        title = _clean_text(getattr(e, "title", "") or "")
        link = _clean_text(getattr(e, "link", "") or "")
        published = _extract_published(e)
        summary = _extract_entry_text(e)

        items.append(
            RssItem(
                title=title,
                link=link,
                published=published,
                summary=summary,
                source=source_name,
                fetched_at=fetched_at,
            )
        )

    return items

def _items_to_workspace_text(items: List[RssItem], heading: str) -> str:
    """
    Workspace에 넣기 좋은 텍스트(마크다운 호환)
    """
    lines: List[str] = []
    lines.append(f"# {heading}")
    lines.append(f"- 생성시각: {items[0].fetched_at if items else _now_iso()}")
    lines.append("")

    for i, it in enumerate(items, start=1):
        lines.append(f"## {i}. {it.title}")
        if it.published:
            lines.append(f"- 일시: {it.published}")
        lines.append(f"- 출처: {it.source}")
        if it.link:
            lines.append(f"- 링크: {it.link}")
        if it.summary:
            lines.append("")
            lines.append(it.summary)
        lines.append("\n---\n")

    return "\n".join(lines).strip() + "\n"

def _items_to_buffer(items: List[RssItem]) -> List[Dict]:
    """
    app4.py의 buffer_items 형식으로 변환
    """
    out: List[Dict] = []
    for it in items:
        out.append(
            {
                "type": "rss_item",
                "title": it.title,
                "text": it.summary,  # LLM 입력용 본문(요약/설명/본문)
                "meta": {
                    "source": it.source,
                    "published": it.published,
                    "url": it.link,
                    "fetched_at": it.fetched_at,
                    "raw": asdict(it),
                },
            }
        )
    return out

# ------------------------------------------------------------
# Streamlit UI 컴포넌트
# ------------------------------------------------------------
DEFAULT_FEEDS: Dict[str, Dict[str, str]] = {

   # Google News 일반
    "Google RSS": {
        "한국 주요뉴스": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
        "정치": "https://news.google.com/rss/search?q=정치&hl=ko&gl=KR&ceid=KR:ko",
        "경제": "https://news.google.com/rss/search?q=경제&hl=ko&gl=KR&ceid=KR:ko",
        "국제": "https://news.google.com/rss/search?q=국제&hl=ko&gl=KR&ceid=KR:ko",
        "AI": "https://news.google.com/rss/search?q=AI&hl=ko&gl=KR&ceid=KR:ko",
    },

    "연합뉴스": {
        "전체": "https://www.yna.co.kr/rss/news.xml",
        "정치": "https://www.yna.co.kr/rss/politics.xml",
        "경제": "https://www.yna.co.kr/rss/economy.xml",
        "사회": "https://www.yna.co.kr/rss/society.xml",
        "국제": "https://www.yna.co.kr/rss/international.xml",
        "문화": "https://www.yna.co.kr/rss/culture.xml",
    },

    "KBS World": {
        "국내(Domestic)": "http://world.kbs.co.kr/rss/rss_news.htm?lang=e&id=Dm",
        "국제(International)": "http://world.kbs.co.kr/rss/rss_news.htm?lang=e&id=In",
        "문화(Culture)": "http://world.kbs.co.kr/rss/rss_news.htm?lang=e&id=Cu",
        "경제(Economy)": "http://world.kbs.co.kr/rss/rss_news.htm?lang=e&id=Ec",
    },

    # BBC RSS 추가
    "BBC": {
        "Top": "http://feeds.bbci.co.uk/news/rss.xml",
        "World": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "Business": "http://feeds.bbci.co.uk/news/business/rss.xml",
        "Technology": "http://feeds.bbci.co.uk/news/technology/rss.xml",
    },

    # NHK RSS 추가
    "NHK": {
        "일본 주요뉴스": "https://www3.nhk.or.jp/rss/news/cat0.xml",
        "사회": "https://www3.nhk.or.jp/rss/news/cat1.xml",
        "정치": "https://www3.nhk.or.jp/rss/news/cat4.xml",
        "국제": "https://www3.nhk.or.jp/rss/news/cat6.xml",
        "경제": "https://www3.nhk.or.jp/rss/news/cat5.xml",
    },

    "Reuters (via Google News)": {
        "Top": "https://news.google.com/rss/search?q=site:reuters.com&hl=en-US&gl=US&ceid=US:en",
        "World": "https://news.google.com/rss/search?q=site:reuters.com+world&hl=en-US&gl=US&ceid=US:en",
        "Business": "https://news.google.com/rss/search?q=site:reuters.com+business&hl=en-US&gl=US&ceid=US:en",
        "Tech": "https://news.google.com/rss/search?q=site:reuters.com+technology&hl=en-US&gl=US&ceid=US:en",
        "Korea": "https://news.google.com/rss/search?q=site:reuters.com+korea&hl=en-US&gl=US&ceid=US:en",
    },

    "AP (via Google News)": {
        "Top": "https://news.google.com/rss/search?q=site:apnews.com&hl=en-US&gl=US&ceid=US:en",
        "World": "https://news.google.com/rss/search?q=site:apnews.com+world&hl=en-US&gl=US&ceid=US:en",
        "Politics": "https://news.google.com/rss/search?q=site:apnews.com+politics&hl=en-US&gl=US&ceid=US:en",
        "Business": "https://news.google.com/rss/search?q=site:apnews.com+business&hl=en-US&gl=US&ceid=US:en",
        "Tech": "https://news.google.com/rss/search?q=site:apnews.com+technology&hl=en-US&gl=US&ceid=US:en",
    },

    "정책브리핑": {
        # 공통 RSS
        "정책뉴스": "https://www.korea.kr/rss/policy.xml",
        "보도자료": "https://www.korea.kr/rss/pressrelease.xml",
        "사실은 이렇습니다": "https://www.korea.kr/rss/fact.xml",
        "부처 브리핑": "https://www.korea.kr/rss/ebriefing.xml",
        "청와대 브리핑": "https://www.korea.kr/rss/president.xml",
        "국무회의 브리핑": "https://www.korea.kr/rss/cabinet.xml",
        "연설문": "https://www.korea.kr/rss/speech.xml",

        # 부처
        "국무조정실": "https://www.korea.kr/rss/dept_opm.xml",
        "재정경제부": "https://www.korea.kr/rss/dept_moef.xml",
        "과학기술정보통신부": "https://www.korea.kr/rss/dept_msit.xml",
        "교육부": "https://www.korea.kr/rss/dept_moe.xml",
        "외교부": "https://www.korea.kr/rss/dept_mofa.xml",
        "통일부": "https://www.korea.kr/rss/dept_unikorea.xml",
        "법무부": "https://www.korea.kr/rss/dept_moj.xml",
        "국방부": "https://www.korea.kr/rss/dept_mnd.xml",
        "행정안전부": "https://www.korea.kr/rss/dept_mois.xml",
        "국가보훈부": "https://www.korea.kr/rss/dept_mpva.xml",
        "문화체육관광부": "https://www.korea.kr/rss/dept_mcst.xml",
        "농림축산식품부": "https://www.korea.kr/rss/dept_mafra.xml",
        "산업통상부": "https://www.korea.kr/rss/dept_motir.xml",
        "보건복지부": "https://www.korea.kr/rss/dept_mw.xml",
        "기후에너지환경부": "https://www.korea.kr/rss/dept_mcee.xml",
        "고용노동부": "https://www.korea.kr/rss/dept_moel.xml",
        "성평등가족부": "https://www.korea.kr/rss/dept_mogef.xml",
        "국토교통부": "https://www.korea.kr/rss/dept_molit.xml",
        "해양수산부": "https://www.korea.kr/rss/dept_mof.xml",
        "중소벤처기업부": "https://www.korea.kr/rss/dept_mss.xml",
        "기획예산처": "https://www.korea.kr/rss/dept_mpb.xml",
        "인사혁신처": "https://www.korea.kr/rss/dept_mpm.xml",
        "법제처": "https://www.korea.kr/rss/dept_moleg.xml",
        "식품의약품안전처": "https://www.korea.kr/rss/dept_mfds.xml",
        "국가데이터처": "https://www.korea.kr/rss/dept_mods.xml",
        "지식재산처": "https://www.korea.kr/rss/dept_moip.xml",

        # 청
        "국세청": "https://www.korea.kr/rss/dept_nts.xml",
        "관세청": "https://www.korea.kr/rss/dept_customs.xml",
        "조달청": "https://www.korea.kr/rss/dept_pps.xml",
        "우주항공청": "https://www.korea.kr/rss/dept_kasa.xml",
        "재외동포청": "https://www.korea.kr/rss/dept_oka.xml",
        "검찰청": "https://www.korea.kr/rss/dept_spo.xml",
        "병무청": "https://www.korea.kr/rss/dept_mma.xml",
        "방위사업청": "https://www.korea.kr/rss/dept_dapa.xml",
        "경찰청": "https://www.korea.kr/rss/dept_npa.xml",
        "소방청": "https://www.korea.kr/rss/dept_nfa.xml",
        "국가유산청": "https://www.korea.kr/rss/dept_khs.xml",
        "농촌진흥청": "https://www.korea.kr/rss/dept_rda.xml",
        "산림청": "https://www.korea.kr/rss/dept_forest.xml",
        "질병관리청": "https://www.korea.kr/rss/dept_kdca.xml",
        "기상청": "https://www.korea.kr/rss/dept_kma.xml",
        "행정중심복합도시건설청": "https://www.korea.kr/rss/dept_macc.xml",
        "새만금개발청": "https://www.korea.kr/rss/dept_sda.xml",
        "해양경찰청": "https://www.korea.kr/rss/dept_kcg.xml",

        # 위원회
        "방송미디어통신위원회": "https://www.korea.kr/rss/dept_kmcc.xml",
        "원자력안전위원회": "https://www.korea.kr/rss/dept_nssc.xml",
        "공정거래위원회": "https://www.korea.kr/rss/dept_ftc.xml",
        "금융위원회": "https://www.korea.kr/rss/dept_fsc.xml",
        "국민권익위원회": "https://www.korea.kr/rss/dept_acrc.xml",
        "개인정보보호위원회": "https://www.korea.kr/rss/dept_pipc.xml",

        # 대통령 소속 위원회
        "국민통합위원회": "https://www.korea.kr/rss/dept_k_cohesion.xml",
        "저출산고령사회위원회": "https://www.korea.kr/rss/dept_betterfuture.xml",
        "경제사회노동위원회": "https://www.korea.kr/rss/dept_esdc.xml",
        "국가기후위기대응위원회": "https://www.korea.kr/rss/dept_pcccr.xml",
    },
}

def _init_rss_cache() -> None:
    """
    Streamlit rerun 대비: 마지막 RSS 결과를 캐시해둠
    """
    if "rss_last_ws_text" not in st.session_state:
        st.session_state.rss_last_ws_text = None
    if "rss_last_buffer" not in st.session_state:
        st.session_state.rss_last_buffer = []
    if "rss_last_info" not in st.session_state:
        st.session_state.rss_last_info = ""

def clear_rss_cache() -> None:
    st.session_state.rss_last_ws_text = None
    st.session_state.rss_last_buffer = []
    st.session_state.rss_last_info = ""

def render_rss_panel() -> Tuple[Optional[str], List[Dict]]:
    """
    RSS 패널을 렌더링하고,
    - workspace에 추가할 텍스트(str) 1개 (없으면 None)
    - buffer_items(list[dict]) (없으면 [])를 반환

    중요:
    - 'RSS 불러오기' 클릭 후 rerun이 일어나도,
      st.session_state.rss_last_* 캐시를 통해 값이 유지됨.
    """
    st.subheader("📰 RSS 수집")

    _init_rss_cache()

    if feedparser is None:
        st.error("feedparser 미설치: `pip install feedparser`")
        return st.session_state.rss_last_ws_text, st.session_state.rss_last_buffer

    top_row = st.columns([2, 2, 1, 1])
    with top_row[0]:
        provider = st.selectbox("제공처", list(DEFAULT_FEEDS.keys()), index=0)
    with top_row[1]:
        category = st.selectbox("카테고리", list(DEFAULT_FEEDS[provider].keys()), index=0)
    with top_row[2]:
        limit = st.number_input("개수", min_value=5, max_value=50, value=10, step=5)
    with top_row[3]:
        if st.button("RSS 캐시 비우기", use_container_width=True):
            clear_rss_cache()
            st.success("RSS 캐시를 비웠습니다.")
            # 캐시 비운 후 즉시 반영되도록 rerun
            st.rerun()

    feed_url = DEFAULT_FEEDS[provider][category]
    st.caption(f"RSS URL: {feed_url}")

    with st.expander("직접 RSS URL 입력(선택)"):
        custom_url = st.text_input("RSS URL", value="", key="rss_custom_url")
        custom_source = st.text_input("출처명", value="Custom RSS", key="rss_custom_source")
        use_custom = st.checkbox("직접 입력 URL 사용", value=False, key="rss_use_custom")
        if use_custom and custom_url.strip():
            feed_url = custom_url.strip()
            provider = (custom_source.strip() or "Custom RSS")
            category = "Custom"

    do_fetch = st.button("RSS 불러오기", use_container_width=True)
    # 새로 불러오지 않으면 "마지막 캐시"를 그대로 반환
    if not do_fetch:
        # 캐시가 있으면 상태 표시
        if st.session_state.rss_last_info:
            st.success(st.session_state.rss_last_info)
            st.info("수집된 항목은 아래 미리보기로 확인한 뒤, Workspace/Buffer에 반영하세요.")
        return st.session_state.rss_last_ws_text, st.session_state.rss_last_buffer

    # RSS 불러오기 실행
    try:
        with st.spinner("RSS 파싱 중..."):
            items = fetch_rss_items(feed_url, source_name=provider, limit=int(limit))
    except Exception as e:
        st.error(f"RSS 수집 실패: {e}")
        return st.session_state.rss_last_ws_text, st.session_state.rss_last_buffer

    if not items:
        st.warning("가져온 항목이 없습니다.")
        return st.session_state.rss_last_ws_text, st.session_state.rss_last_buffer

    st.success(f"{len(items)}건 수집 완료")
    st.info("수집된 항목은 아래 미리보기로 확인한 뒤, Workspace/Buffer에 반영하세요.")

    # 미리보기(상위 5개)
    with st.expander("미리보기(상위 5개)", expanded=True):
        for it in items[:5]:
            st.markdown(f"**{it.title}**")
            if it.published:
                st.caption(f"일시: {it.published}")
            if it.link:
                st.write(it.link)
            if it.summary:
                st.write(it.summary[:400] + ("..." if len(it.summary) > 400 else ""))
            st.divider()

    heading = f"{provider} RSS 수집({category})"
    ws_text = _items_to_workspace_text(items, heading=heading)
    buffer_items = _items_to_buffer(items)

    # 캐시 저장(핵심)
    st.session_state.rss_last_ws_text = ws_text
    st.session_state.rss_last_buffer = buffer_items
    st.session_state.rss_last_info = f"{provider}/{category} - {len(items)}건 (수집: {items[0].fetched_at})"

    return ws_text, buffer_items
