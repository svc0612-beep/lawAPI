# ============================================================
# 법률 코퍼스 확장 스크립트 (v2)
#
# 역할
# 1. 사용자가 실제로 물어볼 법률 분야를 폭넓게 커버
# 2. 국가법령 / 자치법규 / 행정규칙을 한 번에 적재
# 3. 실패 원인을 로그로 남김
#
# 실행:
#   .\.venv\Scripts\python.exe -X utf8 scripts/expand_legal_corpus.py
#
# 결과는 data/rag_evaluation/corpus_expansion.json 에 저장된다.
# ============================================================

import json
import sys
import time
from pathlib import Path

# 프로젝트 루트를 sys.path 에 등록
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from legal_rag.config import Settings
from legal_rag.store import Store
from legal_rag.ingest import ingest_api_cache
from legal_rag.supplemental import refresh_supplemental


# ============================================================
# 1. 국가법령 목록
#
# 분야별로 사용자가 실제로 물어볼 법령을 광범위하게 정리한다.
# 매우 유사한 이름이 여러 개일 경우 정식명칭을 사용한다.
# ============================================================

NATIONAL_LAWS = [

    # ---- 헌법 / 기본법 ----
    "대한민국헌법",
    "행정기본법",
    "정부조직법",

    # ---- 민사·상사 ----
    "민법",
    "상법",
    "민사소송법",
    "민사집행법",
    "민사조정법",
    "가사소송법",
    "채무자 회생 및 파산에 관한 법률",
    "부동산등기법",
    "부동산 거래신고 등에 관한 법률",
    "부동산 실권리자명의 등기에 관한 법률",
    "주택임대차보호법",
    "상가건물 임대차보호법",
    "전세사기피해자 지원 및 주거안정에 관한 특별법",
    "집합건물의 소유 및 관리에 관한 법률",

    # ---- 형사 / 형사특별법 ----
    "형법",
    "형사소송법",
    "폭력행위 등 처벌에 관한 법률",
    "특정범죄 가중처벌 등에 관한 법률",
    "특정경제범죄 가중처벌 등에 관한 법률",
    "성폭력범죄의 처벌 등에 관한 특례법",
    "성폭력방지 및 피해자보호 등에 관한 법률",
    "가정폭력범죄의 처벌 등에 관한 특례법",
    "아동학대범죄의 처벌 등에 관한 특례법",
    "스토킹범죄의 처벌 등에 관한 법률",
    "성매매알선 등 행위의 처벌에 관한 법률",
    "마약류 관리에 관한 법률",
    "국가보안법",
    "소년법",

    # ---- 국가배상 / 행정 절차 / 행정소송 ----
    "국가배상법",
    "행정절차법",
    "행정소송법",
    "행정심판법",
    "질서위반행위규제법",

    # ---- 출입국 / 국적 ----
    "출입국관리법",
    "출입국관리법 시행령",
    "출입국관리법 시행규칙",
    "국적법",
    "난민법",

    # ---- 교육 / 청소년 ----
    "교육기본법",
    "초ㆍ중등교육법",
    "고등교육법",
    "유아교육법",
    "학교급식법",
    "학교폭력예방 및 대책에 관한 법률",
    "청소년 보호법",
    "아동복지법",

    # ---- 노동 / 근로 ----
    "근로기준법",
    "근로기준법 시행령",
    "최저임금법",
    "남녀고용평등과 일ㆍ가정 양립 지원에 관한 법률",
    "고용상 연령차별금지 및 고령자고용촉진에 관한 법률",
    "기간제 및 단시간근로자 보호 등에 관한 법률",
    "파견근로자 보호 등에 관한 법률",
    "근로자퇴직급여 보장법",
    "노동조합 및 노동관계조정법",
    "근로자참여 및 협력증진에 관한 법률",
    "산업안전보건법",
    "중대재해 처벌 등에 관한 법률",
    "고용보험법",
    "산업재해보상보험법",
    "국민연금법",
    "장애인고용촉진 및 직업재활법",

    # ---- 개인정보 / 정보통신 / 디지털 ----
    "개인정보 보호법",
    "정보통신망 이용촉진 및 정보보호 등에 관한 법률",
    "통신비밀보호법",
    "정보통신기반 보호법",
    "신용정보의 이용 및 보호에 관한 법률",
    "전자문서 및 전자거래 기본법",
    "전자금융거래법",

    # ---- 소비자 / 상거래 ----
    "소비자기본법",
    "전자상거래 등에서의 소비자보호에 관한 법률",
    "방문판매 등에 관한 법률",
    "할부거래에 관한 법률",
    "표시ㆍ광고의 공정화에 관한 법률",
    "약관의 규제에 관한 법률",
    "독점규제 및 공정거래에 관한 법률",
    "대부업 등의 등록 및 금융이용자 보호에 관한 법률",

    # ---- 조세 / 관세 ----
    "국세기본법",
    "국세징수법",
    "소득세법",
    "법인세법",
    "부가가치세법",
    "상속세 및 증여세법",
    "조세특례제한법",
    "지방세법",
    "지방세기본법",
    "지방세징수법",
    "관세법",

    # ---- 보건 / 의료 / 복지 ----
    "국민건강보험법",
    "의료법",
    "약사법",
    "식품위생법",
    "공중위생관리법",
    "감염병의 예방 및 관리에 관한 법률",
    "장애인복지법",
    "노인복지법",
    "국민기초생활 보장법",
    "사회보장기본법",

    # ---- 환경 ----
    "환경정책기본법",
    "폐기물관리법",
    "물환경보전법",
    "대기환경보전법",

    # ---- 국토 / 건축 / 주거 ----
    "국토의 계획 및 이용에 관한 법률",
    "건축법",
    "도시 및 주거환경정비법",
    "공동주택관리법",
    "민간임대주택에 관한 특별법",

    # ---- 교통 / 안전 ----
    "도로교통법",
    "교통사고처리 특례법",
    "자동차관리법",
    "자동차손해배상 보장법",
    "재난 및 안전관리 기본법",

    # ---- 지식재산 ----
    "저작권법",
    "특허법",
    "상표법",
    "디자인보호법",
    "부정경쟁방지 및 영업비밀보호에 관한 법률",

    # ---- 금융 / 자본시장 ----
    "자본시장과 금융투자업에 관한 법률",
    "은행법",
    "보험업법",

    # ---- 선거 / 공직 ----
    "공직선거법",
    "국가공무원법",
    "지방공무원법",
    "공무원 징계령",
    "공무원 징계령 시행규칙",

    # ---- 지방자치 ----
    "지방자치법",

    # ---- 병역 ----
    "병역법",

    # ---- 동물 ----
    "동물보호법",
]


# ============================================================
# 2. 행정규칙 검색어
#
# 국민 생활에 자주 영향을 주는 고시·훈령·예규 분야
# ============================================================

ADMINISTRATIVE_QUERIES = [
    "교육과정",
    "출입국",
    "개인정보",
    "산업안전",
    "환경",
    "의료",
    "학교폭력",
    "지방자치",
    "재난안전",
    "전자금융",
    "청소년",
    "장애인",
    "세관",
    "도로교통",
    "주택",
    "노인복지",
    "아동복지",
    "국민건강",
    "식품",
    "약사",
    "자동차",
    "화재",
    "건축",
    "국세",
    "지방세",
    "보험",
    "저작권",
    "특허",
    "상표",
    "공무원 징계",
    "노동",
    "근로",
    "선거",
    "병역",
    "동물보호",
]


# ============================================================
# 3. 자치법규 검색어
#
# 17개 광역 지자체 × 주요 생활 분야
# ============================================================

LOCAL_GOVERNMENTS = [
    "서울특별시",
    "부산광역시",
    "대구광역시",
    "인천광역시",
    "광주광역시",
    "대전광역시",
    "울산광역시",
    "세종특별자치시",
    "경기도",
    "강원특별자치도",
    "충청북도",
    "충청남도",
    "전북특별자치도",
    "전라남도",
    "경상북도",
    "경상남도",
    "제주특별자치도",
]

# 광역별로 순회할 주제
ORDINANCE_TOPICS = [
    "청년 기본 조례",
    "주민참여예산 조례",
    "학교급식",
    "재난 안전",
    "개인정보 보호",
    "저출생 지원",
]

# 광역 × 주제 조합 + 특수 케이스 몇 개 (약 60개 이하로 유지)
ORDINANCE_QUERIES = [
    f"{lg} {topic}" for lg in LOCAL_GOVERNMENTS for topic in ORDINANCE_TOPICS[:3]
] + [
    "서울특별시 청년 기본 조례",
    "서울특별시 저출생 대응 조례",
    "부산광역시 청년 기본 조례",
    "인천광역시 주택",
    "경기도 학교급식",
    "제주특별자치도 청년기금",
]


# ============================================================
# 4. 국가법령 하나 조회 (실패 재시도 포함)
# ============================================================

def _fetch_national_law(
    name: str,
    max_attempts: int = 2
):

    from services.law.full_text import get_full_law

    last_error = None

    for attempt in range(max_attempts):

        try:
            result = get_full_law(name)

            # 정상 응답이면 즉시 반환
            if isinstance(result, dict):
                return result

        except Exception as e:
            last_error = str(e)[:120]

            # 잠깐 쉬고 재시도
            time.sleep(1.0)

    return {
        "status": "error",
        "error": last_error or "unknown",
    }


# ============================================================
# 5. 국가법령 일괄 확보
# ============================================================

def collect_national_laws(
    names,
    show_progress: bool = True
):

    results = []

    total = len(names)

    for index, name in enumerate(
        names,
        1
    ):

        if show_progress:
            print(
                f"[{index}/{total}] {name}",
                flush=True
            )

        result = _fetch_national_law(name)

        results.append({
            "requested": name,
            "status": result.get("status", "error"),
            "resolved": result.get("law_name", ""),
            "articles": result.get("article_count", 0),
            "law_type": result.get("law_type", ""),
            "error": result.get("error", ""),
        })

        # 법제처 API에 무리한 부하가 가지 않도록 소폭 대기
        time.sleep(0.15)

    return results


# ============================================================
# 6. 메인
# ============================================================

def main():

    settings = Settings.from_env()
    store = Store(settings.database)

    print(
        "="*70,
        flush=True
    )
    print(
        f"1) 국가법령 조회 ({len(NATIONAL_LAWS)}건)",
        flush=True
    )
    print(
        "="*70,
        flush=True
    )

    # 국가법령 조회
    national = collect_national_laws(NATIONAL_LAWS)

    # 성공/실패 카운트
    success_count = sum(
        1 for row in national if row["status"] == "success"
    )
    failed = [
        {"requested": row["requested"], "reason": row["status"], "error": row["error"]}
        for row in national
        if row["status"] != "success"
    ]

    print(
        f"\n국가법령 성공: {success_count}/{len(national)}",
        flush=True
    )

    # ------------------------------------------------------------
    # 캐시에 담긴 법제처 API 응답을 store 에 인제스트
    # ------------------------------------------------------------
    print(
        "\n2) 캐시 → store 적재",
        flush=True
    )
    national_ingestion = ingest_api_cache(store)
    print(
        json.dumps(national_ingestion, ensure_ascii=False),
        flush=True
    )

    # ------------------------------------------------------------
    # 행정규칙
    # ------------------------------------------------------------
    print(
        f"\n3) 행정규칙 ({len(ADMINISTRATIVE_QUERIES)}건)",
        flush=True
    )
    admin_stats = refresh_supplemental(
        store,
        "admrul",
        ADMINISTRATIVE_QUERIES
    )
    print(
        json.dumps(admin_stats, ensure_ascii=False),
        flush=True
    )

    # ------------------------------------------------------------
    # 자치법규
    # ------------------------------------------------------------
    print(
        f"\n4) 자치법규 ({len(ORDINANCE_QUERIES)}건)",
        flush=True
    )
    ordin_stats = refresh_supplemental(
        store,
        "ordin",
        ORDINANCE_QUERIES
    )
    print(
        json.dumps(ordin_stats, ensure_ascii=False),
        flush=True
    )

    # ------------------------------------------------------------
    # 결과 저장
    # ------------------------------------------------------------
    result = {
        "national": national,
        "national_success": success_count,
        "national_failed": failed,
        "national_ingestion": national_ingestion,
        "administrative_rules": admin_stats,
        "local_ordinances": ordin_stats,
    }

    path = Path("data/rag_evaluation/corpus_expansion.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # ------------------------------------------------------------
    # 요약 출력 (핵심만)
    # ------------------------------------------------------------
    print(
        "\n" + "="*70,
        flush=True
    )
    print(
        "요약",
        flush=True
    )
    print(
        "="*70,
        flush=True
    )
    print(
        json.dumps(
            {
                "national_total": len(national),
                "national_success": success_count,
                "national_failed_count": len(failed),
                "national_failed": [
                    x["requested"] for x in failed
                ],
                "national_ingestion": national_ingestion,
                "administrative_rules": admin_stats,
                "local_ordinances": ordin_stats,
            },
            ensure_ascii=False,
            indent=2
        ),
        flush=True
    )


if __name__ == "__main__":
    main()
