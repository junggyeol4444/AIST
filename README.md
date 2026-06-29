# AIST — AI Streamer

24/7급 운영을 목표로 하는 한국어 AI 스트리머 시스템.
본인 목소리로 클로닝된 TTS + 로컬 LLM으로 토크/게임 방송을 진행하고,
OBS 위에 채팅 오버레이를 띄운다. 진짜 시청자 채팅을 읽고 반응한다.

> 상태: **Phase 1 (페르소나 + LLM 단독 동작)**. Ollama 없이도 mock 백엔드로 검증 가능.

## 아키텍처 개요

```
오케스트레이터 ── LLM 엔진(로컬) ── TTS 엔진(로컬) ── 채팅 수집기 ── 채팅 생성기
        │                                  │                          │
   상태/이벤트 라우팅                 가상 케이블→OBS            HTML 오버레이(OBS 브라우저 소스)
        └────────────────── 페르소나 시스템 (방송인 + 시청자) ──────────────────┘
```

## 디렉토리 구조

| 경로 | 역할 |
|------|------|
| `config/` | 전역/페르소나/플랫폼 설정 (YAML) |
| `core/` | 오케스트레이터, 이벤트 버스, 상태 관리, 로깅 |
| `llm/` | 로컬 LLM 추론 엔진, 프롬프트 조립, 컨텍스트 관리 |
| `tts/` | 목소리 클로닝 TTS, 오디오 출력, 추임새 처리 |
| `chat/` | 플랫폼별 채팅 수집, 가짜 채팅 생성, 스케줄러 |
| `overlay/` | FastAPI + WebSocket 오버레이 서버, OBS용 HTML/CSS/JS |
| `game_context/` | (후반) 게임 화면/사운드 인지 |
| `data/` | 목소리 녹음 원본, 전사, 페르소나 캐시 (git 미추적) |
| `scripts/` | 환경설정·페르소나 다운로드·실행 스크립트 |
| `tests/` | 테스트 |

## Phase 로드맵

- **Phase 0** — 환경/디렉토리/의존성 (현재)
- **Phase 1** — 페르소나 시스템 + LLM 단독 동작
- **Phase 2** — 가짜 채팅 생성 + OBS 오버레이
- **Phase 3** — TTS 통합 (목소리 클로닝)
- **Phase 4** — 실제 시청자 채팅 수집기
- **Phase 5** — 오케스트레이터 통합 (무인 운영)
- **Phase 6** — 게임/토크 컨텍스트 보강
- **Phase 7** — 8시간 무중단 안정화
- **Phase 8** — 미세 조정

## 설치 (Phase 0 검증)

```bash
python -m venv .venv && source .venv/bin/activate   # Python 3.11
pip install -r requirements.txt
pytest -q                                            # import/설정 스모크 테스트
```

> LLM/TTS/플랫폼 의존성 일부는 결정 후 `requirements.txt`에서 주석 해제.

테스트는 `pytest -q` 또는 의존성 없이 `python tests/run_checks.py`로 실행.

## Phase 1 사용법

페르소나 시스템 + LLM 래퍼가 동작한다. **mock 백엔드**는 모델/서버 없이 배선을
검증하고, **ollama 백엔드**는 실제 응답을 생성한다.

```bash
# 모델/서버 없이 파이프라인 확인 (mock)
python scripts/persona_chat.py --role streamer --backend mock
python scripts/persona_chat.py --role viewer  --backend mock --count 8

# 실제 LLM (Ollama 설치 + 모델 pull 후)
ollama pull qwen2.5:14b-instruct-q4_K_M
python scripts/persona_chat.py --role streamer --backend ollama
```

- 방송인 페르소나: `config/streamer_persona.yaml` (D2/D3 — 본인 설정으로 교체)
- 시청자 페르소나: `config/viewer_personas.yaml` (Nemotron 스키마 기반 큐레이션 10종)
- Nemotron에서 재생성: `python scripts/load_personas.py --num 10` (datasets + 네트워크 필요)

## 결정 필요 (진행 순서)

| 코드 | 내용 | 필요 시점 |
|------|------|-----------|
| D1 | 로컬 LLM 모델 | Phase 1 |
| D2 | 방송인 페르소나 (이름/나이/말투/백스토리) | Phase 1 |
| D3 | "너 AI지?" 대응 방향 | Phase 1 |
| D4 | 가짜 채팅 분당 빈도 | Phase 2 |
| D5 | TTS 모델 | Phase 3 |
| D6 | 방송 플랫폼 | Phase 4 |
| D7 | 게임 종류 / 화면 인지 필요 여부 | Phase 6 |

## 윤리 메모

가짜 시청자 채팅은 시청자 기만 소지가 있는 회색지대 기능이다. 플랫폼 약관 위반
및 평판 리스크가 있을 수 있으며, 노출 방식(공개/비공개)은 운영자가 결정한다.
시청자수 조작(뷰봇), 플랫폼 채팅창 봇 작성, 후원/구독 자동화는 **비목표**로 다루지 않는다.
