# ⚖️ LawMate

**정확한 법률명을 몰라도 자연어로 물어볼 수 있는 한국 법률 참고 챗봇.**
법령·판례·법령해석례를 공식 원문 단위로 검증해 답변합니다.

![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Ollama](https://img.shields.io/badge/Ollama-Qwen3-orange)

---

## ✨ 주요 기능

- **자연어 질문 이해**: "회사에서 장애인 고용 안 하면?", "이혼하려면 어떻게 해?" 같이 정확한 법률명 몰라도 매칭
- **40개 도메인 커버**: 헌법·형사·민사·가사·노동·행정 등 전 영역 (요약·조문·판례 통합)
- **진짜 멀티턴**: "그럼 재판이혼 위자료는?" 같은 후속 질문에서 이전 컨텍스트 자동 이어받기
- **초점 답변**: follow-up 시 관련 섹션만 발췌해서 배지로 명시 ("🔎 위자료 중심으로 초점")
- **공식 원문 검증**: 법제처 API로 조문 원문을 실시간 검증. 검증 실패 시 답변 보류
- **국회도서관 참고문헌**: 관련 학술 자료 자동 검색
- **4단계 fallback**: `grounded_excerpt` → `context_carryover` → `advisory_summary` → 판례 없음 안내
- **한국형 UI**: ChatGPT 스타일 하단 sticky 입력창, status별 색상 알림, profile 태그

---

## 🏗️ 아키텍처

```
사용자 질문
    ↓
[search_hints] profile 매칭 (40개 profile)
    ↓
[Qwen: plan] 검색 쿼리 확장 · follow-up 판정
    ↓
[retrieval] SQLite FTS5 조문 검색 + 법제처 API 실시간 조회
    ↓
[Qwen: selection] 근거 조문 선택
    ↓
[verify] 조문 원문 일치 검증 (법제처)
    ↓
[render] 📌 핵심 요약 · 📎 근거 조문 · ⚖️ 관련 판례 · 📚 참고 문헌 · ⚠️ 유의사항
```

**핵심 원칙**: Qwen은 검색 계획과 근거 선택에만 사용. 실제 화면에 공개되는 법률 내용은 **공식 원문 검증 통과 조문·판례로만 제한**. 새 법률 결론은 생성하지 않음.

---

## 🚀 빠른 시작

### 1. 사전 조건

- Python 3.10+
- [Ollama](https://ollama.com) 설치 (로컬 LLM 서버)
- 법제처 API 키 (https://open.law.go.kr)
- 국회도서관 API 키 (https://open.nanet.go.kr)

### 2. 설치

```bash
# 저장소 클론
git clone https://github.com/svc0612-beep/lawAPI.git
cd lawAPI

# 가상환경 생성 & 활성화
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # macOS/Linux

# 의존성 설치
pip install -r requirements-rag.txt

# Qwen 모델 pull
ollama pull qwen3:1.7b-q4_K_M
```

### 3. 환경변수 설정

`.env.example`을 복사해서 `.env` 만들고 실제 API 키 입력:

```bash
cp .env.example .env
# 편집기로 .env 열어서 LAW_API_KEY, NANET_API_KEY 채우기
```

### 4. Corpus 구축 (첫 실행 시 한 번만)

```bash
python scripts/expand_legal_corpus.py
```

주요 법령 ~130개 조문을 SQLite에 인덱싱. **몇 분 걸림**.

### 5. 실행

```bash
streamlit run app.py
```

기본 http://localhost:8501 에서 열림.

---

## 📁 프로젝트 구조

```
lawAPI/
├── app.py                          # Streamlit 진입점
├── .streamlit/config.toml          # 테마 설정 (라이트 모드 강제)
│
├── legal_rag/                      # RAG 엔진 코어
│   ├── engine.py                   # 파이프라인 (plan → retrieve → verify)
│   ├── config.py                   # 모델·타임아웃·경로 설정
│   ├── ingest.py                   # 온라인 조회·hint 이어받기
│   ├── retrieval.py                # FTS5 검색 + reranking
│   ├── verify.py                   # 조문 원문 검증
│   ├── model.py                    # Ollama 호출 래퍼
│   ├── store.py                    # 세션·대화 저장 (SQLite)
│   ├── schemas.py                  # Qwen JSON schema
│   └── scope.py                    # 명시적 법령/조문 감지
│
├── services/
│   ├── law/                        # 법제처 API 통합
│   │   ├── search_hints.py         # 40개 profile 정의 (⭐ 핵심)
│   │   ├── summary_focus.py        # 초점 섹션 필터
│   │   └── ...
│   ├── library/search.py           # 국회도서관 API
│   ├── generation/verified_answer.py  # 답변 렌더러
│   └── ui/                         # Streamlit UI 컴포넌트
│       ├── rag_chat_view.py        # 대화 뷰 (색상 알림·profile 태그)
│       ├── search_panel.py         # hero·예시·chat_input
│       └── styles.py               # CSS
│
├── agents/query_analyzer.py        # 질문 유형 분류
├── scripts/
│   ├── regression_suite.py         # 161개 자동 검증
│   └── expand_legal_corpus.py      # 초기 corpus 구축
└── tests/                          # 단위 테스트
```

---

## 🧪 리그레션 스위트

코드 변경 후 언제나:

```bash
python scripts/regression_suite.py
```

**161개 케이스** (profile 매칭·follow-up 감지·focus_summary·case_types) 자동 검증. Ollama 호출 없이 순수 로직만 몇 초 안에 검증.

---

## 🎨 답변 형식

모든 답변은 다음 5개 섹션으로 통일:

1. **📌 핵심 요약** — 사람이 검토한 정형 안내 (필요 시 focus 배지)
2. **📎 근거 조문** — 시행일·법령정보센터 링크 포함
3. **⚖️ 관련 판례** — 검증된 대법원·헌법재판소 판례 (없으면 안내)
4. **📚 참고 문헌** — 국회도서관 학술 자료 링크
5. **⚠️ 유의사항** — 법 적용 한계와 전문가 상담 안내

---

## 🔒 원칙

- **verified evidence only**: 새 법률 결론을 만들어내지 않음
- **투명성**: 어떤 조문·판례가 근거인지 링크로 명시
- **한계 공지**: 사실관계·시점에 따라 결과가 달라질 수 있음을 항상 안내
- **참고 챗봇**: 실제 법 적용 판단은 법률 전문가와 상의 권고

---

## 📦 사용 API

| 서비스 | 용도 | 제공처 |
|---|---|---|
| 법제처 open API | 법령·판례·해석례 실시간 조회 | [open.law.go.kr](https://open.law.go.kr) |
| 국회도서관 open API | 학술 자료·참고 문헌 검색 | [open.nanet.go.kr](https://open.nanet.go.kr) |
| Ollama (로컬) | Qwen3 1.7B 로컬 추론 | [ollama.com](https://ollama.com) |

---

## 🐛 디버그 모드

파이프라인 흐름을 추적하려면:

```powershell
$env:LAWMATE_DEBUG="1"
streamlit run app.py
```

콘솔에 `[DEBUG]` 로그 활성화 (follow-up 판정, hint 이어받기, fallback 트리거 등).

---

## 📄 라이선스

교육·연구 목적의 개인 프로젝트. 실제 법률 자문으로 활용하지 마세요.
