# ============================================================
# LawMate 리그레션 스위트
#
# 실행: python scripts/regression_suite.py
# 성공 시 종료 코드 0, 실패 시 1
#
# 범위 (Ollama·API 호출 없이 순수 로직만 검증)
# 1. 28개 profile × 여러 자연 표현 매칭
# 2. FOLLOW_UP_HINT + likely_follow_up 짧은 명사구 감지
# 3. NEW_TOPIC 감지
# 4. focus_summary 초점 섹션 필터
# 5. focus_labels 배지 라벨 정제
# 6. quote_strip 따옴표 감싸진 입력 처리
# 7. PROFILE_CASE_TYPES 매핑 존재 여부
# ============================================================

import sys, re
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ---- 정규식·헬퍼 발췌 (engine.py verify 의존 회피) ----
FOLLOW_UP_HINT = re.compile(
    r"^(?:그럼|그러면|그래서|그리고|"
    r"그\s*(?:경우|사건|사람|법|조문|것|거|건|때|쪽)|"
    r"그거|그건|그것|이거|이건|이것|"
    r"위(?:\s*(?:조항|조문|법|사건|경우))?|"
    r"앞(?:의|서)|방금|아까|"
    r"더|또|추가로|자세히|그럼\s*(?:만약|만일))|"
    r"(?:피해자|가해자|당사자|회사|근로자|배우자|자녀|상속인)가?\s*.*(?:면|경우|때)[?？]?$"
)
NEW_TOPIC_HINT = re.compile(r"(?:새\s*주제|새\s*질문|다른\s*질문|별개(?:의)?\s*사건)")

def _strip_quotes(text):
    s = str(text or "")
    while s:
        stripped = s.strip().strip('"').strip("'").strip("“").strip("”").strip("‘").strip("’")
        if stripped == s: break
        s = stripped
    return s

def likely_follow_up(question, history):
    q = _strip_quotes(question)
    if not history or NEW_TOPIC_HINT.search(q): return False
    if FOLLOW_UP_HINT.search(q): return True
    if len(q) <= 20 and re.search(r"[?？]$", q) and re.search(r"(?:은|는|이|가|을|를|도|만|과|와)\s*(?:\S{0,10})[?？]$", q):
        return True
    # FOCUS_KEYWORDS 명사가 있는 짧은 질문 (조사 없이도)
    if len(q) <= 15 and re.search(r"[?？]$", q):
        try:
            from services.law.summary_focus import FOCUS_KEYWORDS
            if any(key in q for key in FOCUS_KEYWORDS.keys()): return True
        except ImportError:
            pass
    return False


# ============================================================
# 검증 결과 집계
# ============================================================
PASS, FAIL = 0, 0
FAIL_DETAILS = []

def check(name, actual, expected):
    global PASS, FAIL
    ok = actual == expected
    if ok:
        PASS += 1
    else:
        FAIL += 1
        FAIL_DETAILS.append((name, expected, actual))
    return ok


# ============================================================
# 1. Profile 매칭 (28개 × 자연 표현)
# ============================================================
print("=" * 70)
print("[1] Profile 매칭")
print("=" * 70)

from services.law.search_hints import search_hints, PROFILES, PROFILE_CASE_TYPES

PROFILE_TESTS = [
    # (질문, 매칭되어야 할 profile id)
    ("헌법소원 청구 어떻게?", "constitutional_complaint"),
    ("헌법소원 어떻게 하나요", "constitutional_complaint"),
    ("기본권 침해 당했어", "rights"),
    ("자유와 권리가 제한된다는데", "rights"),
    ("월급을 안 주면?", "wages"),
    ("임금 체불 신고", "wages"),
    ("부당해고 당했어", "dismissal"),
    ("퇴직금 못 받으면", "retirement"),
    ("최저임금 위반", "minimum_wage"),
    ("산재 처리는?", "workplace_injury"),
    ("업무상 재해 인정", "workplace_injury"),
    ("회사가 장애인 고용 안하면?", "disability_employment"),
    ("음주운전 처벌?", "drink_driving"),
    ("음주운전 하면 어떤 처벌", "drink_driving"),
    ("무면허운전", "unlicensed"),
    ("폭행 당했어", "assault"),
    ("SNS 명예훼손 신고", "online_speech"),
    ("악플 달렸어", "online_speech"),
    ("사기 당했어", "fraud"),
    ("절도 처벌", "theft"),
    ("성폭력 신고", "sexual_violence"),
    ("스토킹 당하고 있어", "stalking"),
    ("아동학대 신고", "child_abuse"),
    ("학교폭력 신고", "school_violence"),
    ("마약 처벌", "drug"),
    ("특허 침해", "patent"),
    ("개인정보 유출", "privacy"),
    ("청약철회 하고 싶어", "refund"),
    ("환불 받고 싶어", "refund"),
    ("반품 어떻게 해?", "refund"),
    ("전세보증금 안 돌려주면?", "housing_deposit"),
    ("빌려준 돈 안 갚아", "loan"),
    ("대여금 반환 청구", "loan"),
    ("이혼하려면?", "divorce"),
    ("이혼하려면 어떻게 해?", "divorce"),
    ("상속받으면", "inheritance"),
    ("상속받으면 어떻게 해?", "inheritance"),
    ("세금 체납", "tax_default"),
    # G) 신규 profile
    ("개인회생 신청하려면", "bankruptcy"),
    ("파산선고 받으면", "bankruptcy"),
    ("빚 못 갚아서 회생", "bankruptcy"),
    ("부동산 경매 참여하려면", "real_estate_auction"),
    ("강제경매 절차", "real_estate_auction"),
    ("낙찰 받은 뒤 어떻게", "real_estate_auction"),
    ("상표 등록하려면", "trademark"),
    ("상표권 침해 당했어", "trademark"),
    ("교통사고 났어", "traffic_accident"),
    ("접촉사고 처리", "traffic_accident"),
    ("12대 중과실 처벌", "traffic_accident"),
    ("뺑소니 신고", "traffic_accident"),
    # O) 신규 profile
    ("근로계약서 안 써줘", "labor_contract"),
    ("수습 기간 해고", "labor_contract"),
    ("채용 조건 위반", "labor_contract"),
    ("채권추심 협박 받았어", "debt_collection"),
    ("사채업자가 밤에 전화", "debt_collection"),
    ("빚 독촉 어디 신고", "debt_collection"),
    ("육아휴직 신청하려면", "parental_leave"),
    ("출산휴가 며칠", "parental_leave"),
    ("배우자 출산휴가", "parental_leave"),
    ("부동산 매매 절차", "real_estate_purchase"),
    ("계약금 반환 받을 수 있어?", "real_estate_purchase"),
    ("잔금 못 받으면", "real_estate_purchase"),
    # Q) 신규 profile
    ("의료사고 손해배상", "medical_malpractice"),
    ("수술 사고 어떻게 대응", "medical_malpractice"),
    ("오진 신고", "medical_malpractice"),
    ("층간소음 신고", "environmental_pollution"),
    ("환경오염 손해배상", "environmental_pollution"),
    ("공해로 피해 봤어", "environmental_pollution"),
    ("계약 해제 위약금", "contract_general"),
    ("계약 파기 손해배상", "contract_general"),
    ("서비스 계약 해지", "contract_general"),
    ("과태료 이의신청", "traffic_fine"),
    ("무인단속 딱지 어떻게", "traffic_fine"),
    ("범칙금 안 내면", "traffic_fine"),
]

for q, expected_pid in PROFILE_TESTS:
    r = search_hints(q)
    pids = r.get("profile_ids", [])
    check(f"매칭 [{q}] → {expected_pid}", expected_pid in pids, True)

print(f"  통과: {PASS} / {PASS + FAIL}")


# ============================================================
# 2. Follow-up 감지 (지시대명사·짧은 명사구·따옴표)
# ============================================================
print("\n" + "=" * 70)
print("[2] Follow-up 감지")
print("=" * 70)

hist_a = ["이혼하려면 어떻게?"]
hist_b = ["헌법소원 청구 어떻게?"]

FOLLOWUP_TESTS = [
    # (질문, history, 기대값)
    ("그럼 재판이혼 위자료는?", hist_a, True),
    ("위자료는 얼마야?", hist_a, True),
    ("재산분할은 어떻게?", hist_a, True),
    ("그거 얼마?", hist_a, True),
    ("그건 어떤 서류?", hist_a, True),
    ("앞의 조문 다시 보여줘", hist_a, True),
    ("위 조항 시행일?", hist_a, True),
    ("청구기간은 얼마?", hist_b, True),
    ("대리인 꼭 필요해?", hist_b, True),
    # 따옴표 감싸진 케이스 (Streamlit UI 특성)
    ('"청구기간은 얼마?"', hist_b, True),
    ("'재산분할은 얼마?'", hist_a, True),
    ('  "위자료는?"  ', hist_a, True),
    # 새 주제 (감지 안 되어야)
    ("새 질문 있어 사기 당했어", hist_a, False),
    ("별개 사건인데 폭행 당했어", hist_a, False),
    # history 없을 때
    ("그럼 어떻게?", [], False),
    ("청구기간은 얼마?", [], False),
]

for q, hist, expected in FOLLOWUP_TESTS:
    actual = likely_follow_up(q, hist)
    check(f"follow_up [{q!r}, history={len(hist)}]", actual, expected)


# ============================================================
# 3. focus_summary 초점 필터
# ============================================================
print("\n" + "=" * 70)
print("[3] focus_summary 초점 섹션 필터")
print("=" * 70)

from services.law.summary_focus import focus_summary, focus_labels

FOCUS_TESTS = [
    # (질문, profile_id, follow_up, 포함되어야, 제거되어야)
    ("그럼 재판이혼 위자료는?", "divorce", True,
     ["재판이혼 절차", "함께 정할 사항", "위자료"], ["협의이혼 절차"]),
    ("재산분할은 얼마?", "divorce", True,
     ["함께 정할 사항", "재산분할"], ["협의이혼 절차", "재판이혼 절차"]),
    ("그럼 상속포기는?", "inheritance", True,
     ["상속 절차 단계", "상속포기"], ["상속 순위 및 분할"]),
    ("유류분 얼마?", "inheritance", True,
     ["상속 순위 및 분할", "유류분"], ["상속 절차 단계"]),
    ("청구기간은 얼마?", "constitutional_complaint", True,
     ["청구 요건", "90일", "1년"], ["청구 절차 단계"]),
    ("대리인 꼭 필요해?", "constitutional_complaint", True,
     ["청구 절차 단계", "대리인", "변호사"], []),
    # 첫 질문 (follow_up=False) → 전체 유지
    ("이혼하려면 어떻게?", "divorce", False,
     ["협의이혼 절차", "재판이혼 절차", "함께 정할 사항"], []),
]

for q, pid, fu, must_have, must_miss in FOCUS_TESTS:
    r = search_hints(f"{pid.replace('_', ' ')} 어떻게?" if not fu else "이혼하려면?")
    # profile.summary 직접 조회
    p = next((x for x in PROFILES if x["id"] == pid), None)
    if not p or not p.get("summary"):
        check(f"focus [{q}] profile={pid} → summary 존재", False, True)
        continue
    focused = focus_summary(p["summary"], q, follow_up=fu, extra_terms=tuple(p.get("terms", [])))
    for kw in must_have:
        check(f"focus [{q}] '{kw}' 포함", kw in focused, True)
    for kw in must_miss:
        check(f"focus [{q}] '{kw}' 제거", kw not in focused, True)


# ============================================================
# 4. focus_labels 배지 라벨
# ============================================================
print("\n" + "=" * 70)
print("[4] focus_labels (배지)")
print("=" * 70)

LABEL_TESTS = [
    # (질문, 기대 라벨 중 첫 번째)
    ("그럼 재판이혼 위자료는?", "위자료"),
    ("재산분할은 얼마?", "재산분할"),
    ("그럼 상속포기는?", "상속포기"),
    ("유류분 얼마?", "유류분"),
    ("청구기간은 얼마?", "청구기간"),
    ("대리인 꼭 필요해?", "대리인"),
]

for q, first_label in LABEL_TESTS:
    labels = focus_labels(q, ())
    check(f"label [{q}] 첫 라벨='{first_label}'", labels[0] if labels else "", first_label)


# ============================================================
# 5. PROFILE_CASE_TYPES 매핑 존재
# ============================================================
print("\n" + "=" * 70)
print("[5] PROFILE_CASE_TYPES 매핑 커버리지")
print("=" * 70)

profile_ids = {p["id"] for p in PROFILES}
mapped_ids = set(PROFILE_CASE_TYPES.keys())
missing = profile_ids - mapped_ids
check(f"모든 profile ({len(profile_ids)}개) case_types 매핑 존재", len(missing), 0)

for pid in sorted(profile_ids):
    cts = PROFILE_CASE_TYPES.get(pid, [])
    check(f"case_types [{pid}] 비어있지 않음", len(cts) > 0, True)


# ============================================================
# 종합
# ============================================================
print("\n" + "=" * 70)
print(f"결과: {PASS} pass / {FAIL} fail (총 {PASS + FAIL}건)")
print("=" * 70)

if FAIL:
    print("\n실패한 테스트:")
    for name, exp, act in FAIL_DETAILS[:20]:
        print(f"  ❌ {name}")
        print(f"     expected: {exp}")
        print(f"     actual:   {act}")
    sys.exit(1)
else:
    print("\n✅ 전 테스트 통과")
    sys.exit(0)
