# AI-Agent-System

> 회의록, 문서, 음성 데이터를 AI Agent가 분석하여 업무 정보를 자동으로 정리하는 플랫폼

<br />

## Service Overview

AI-Agent-System은 회의록, 문서, 음성 파일 등 업무 과정에서 발생하는 비정형 데이터를 AI Agent가 분석하여 핵심 내용을 요약하고, 할 일을 추출하며, RAG 기반 질의응답을 제공하는 업무 자동화 플랫폼입니다.

사용자는 문서나 음성 파일을 업로드하거나 채팅을 통해 질문할 수 있으며, 시스템은 업로드된 자료와 이전 대화 내용을 바탕으로 적절한 답변을 생성합니다.

이를 통해 반복적인 문서 확인 작업을 줄이고, 흩어진 업무 정보를 하나의 지식 자산으로 관리하는 것을 목표로 합니다.

<br />

## Key Features

| 기능 | 설명 |
| --- | --- |
| AI Chat | 채팅 기반으로 AI에게 질문하고 답변을 받을 수 있습니다. |
| Document Analysis | PDF, 이미지, 문서 파일의 내용을 추출하고 분석합니다. |
| Voice Processing | 음성 파일을 STT를 통해 텍스트로 변환합니다. |
| Summarization | 문서, 회의록, 음성 내용을 요약합니다. |
| Task Extraction | 회의나 문서에서 할 일을 자동으로 추출합니다. |
| RAG Search | 업로드된 문서를 기반으로 질문에 답변합니다. |
| Notion Integration | 요약 결과와 할 일 목록을 Notion에 저장합니다. |
| Conversation Management | 채팅방과 대화 기록을 관리합니다. |

<br />

## Architecture

```text
User
  │
  ├── Chat Input
  ├── Document Upload
  └── Voice Upload
        │
        ▼
FastAPI Backend
        │
        ├── Chat Service
        ├── Document Service
        ├── STT Service
        ├── RAG Service
        └── Notion Service
        │
        ▼
LangGraph Agent
        │
        ├── Question Classification
        ├── Memory Search
        ├── RAG Search
        ├── Task Extraction
        ├── Notion Save
        └── Final Answer Generation
        │
        ▼
Response / Chat History / Notion
```

<br />

## Tech Stack

### Backend

| Category | Stack |
| --- | --- |
| Language | Python |
| Framework | FastAPI |
| Database | SQLite |
| Schema Validation | Pydantic |

### AI / Agent

| Category | Stack |
| --- | --- |
| Agent Workflow | LangGraph |
| LLM | Ollama |
| Vector Database | ChromaDB |
| Search | RAG |
| Embedding | Embedding Model |

### Document Processing

| Category | Stack |
| --- | --- |
| Layout Analysis | Docling |
| Text Extraction | PyMuPDF |
| Text Table Extraction | pdfplumber |
| OCR | PaddleOCR |
| Vision-Language Model | PaddleOCR-VL 비활성화 |
| 비활성화 사유 | VRAM 사용량 문제 |

### Voice Processing

| Category | Stack |
| --- | --- |
| STT | faster-whisper |

### Frontend

| Category | Stack |
| --- | --- |
| Language | TypeScript |
| Framework | React |
| Build Tool | Vite |
| Styling | Tailwind CSS |
| Linting | ESLint |

### External Integration

| Category | Stack |
| --- | --- |
| Workspace Tool | Notion API |

<br />

## Document Processing Pipeline

문서 처리 모듈은 업로드된 PDF 또는 이미지 문서에서 레이아웃, 텍스트, 표, OCR 정보를 추출하여 RAG 검색에 활용 가능한 형태로 변환합니다.

| 처리 영역 | 사용 기술 | 설명 |
| --- | --- | --- |
| Layout | Docling | 문서의 레이아웃 구조를 분석합니다. |
| Text | PyMuPDF | PDF 내부 텍스트를 추출합니다. |
| Text Table | pdfplumber | PDF 내 텍스트 기반 표 데이터를 추출합니다. |
| OCR | PaddleOCR | 이미지 기반 문서 또는 스캔 문서의 텍스트를 인식합니다. |
| VL | PaddleOCR-VL | VRAM 문제로 현재 비활성화 상태입니다. |

<br />

## API Flow

### Chat Flow

```text
POST /api/chat
  ↓
사용자 메시지 저장
  ↓
AgentState 생성
  ↓
LangGraph Agent 실행
  ↓
질문 유형 분류
  ↓
필요한 노드 실행
  ↓
최종 답변 반환
```

### Document Flow

```text
POST /api/documents/upload
  ↓
문서 파일 업로드
  ↓
문서 레이아웃 분석
  ↓
텍스트 / 표 / OCR 데이터 추출
  ↓
Document JSON 생성
  ↓
문서 메타데이터 저장
  ↓
ChromaDB에 문서 Chunk 저장
  ↓
RAG 검색에 활용
```

### Voice Flow

```text
POST /api/stt
  ↓
음성 파일 업로드
  ↓
STT를 통한 텍스트 변환
  ↓
STT JSON 생성
  ↓
요약 및 할 일 추출에 활용
```

<br />

## Main APIs

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/api/chat` | 채팅 메시지 전송 |
| GET | `/api/conversations` | 채팅방 목록 조회 |
| GET | `/api/conversations/{room_id}/messages` | 특정 채팅방 메시지 조회 |
| POST | `/api/documents/upload` | 문서 업로드 및 분석 |
| POST | `/api/stt` | 음성 파일 업로드 및 STT 처리 |
| POST | `/api/agent` | AI Agent 실행 |

<br />

## AgentState

LangGraph Agent는 `AgentState`를 기반으로 각 노드 간 데이터를 전달합니다.

| 필드명 | 설명 |
| --- | --- |
| `room_id` | 현재 채팅방 ID |
| `user_message` | 사용자 입력 메시지 |
| `messages` | 이전 대화 기록 |
| `document_json` | 문서 또는 음성 처리 결과 |
| `question_type` | 질문 유형 |
| `memory_context` | 이전 대화 기반 메모리 |
| `rag_context` | 문서 검색 결과 |
| `summary` | 요약 결과 |
| `tasks` | 추출된 할 일 목록 |
| `notion_result` | Notion 저장 결과 |
| `final_answer` | 최종 응답 |
| `error` | 오류 정보 |

<br />

## Folder Structure

```text
AI-Agent-System/
├── backend/
│   ├── main.py
│   ├── routers/
│   │   ├── chat_router.py
│   │   ├── agent_router.py
│   │   ├── document_router.py
│   │   └── stt_router.py
│   ├── services/
│   │   ├── chat_service.py
│   │   ├── document_service.py
│   │   ├── ollama_service.py
│   │   ├── rag_service.py
│   │   ├── memory_service.py
│   │   └── notion_service.py
│   ├── graphs/
│   │   ├── agent_graph.py
│   │   └── nodes/
│   ├── schemas/
│   │   ├── chat_schema.py
│   │   ├── agent_schema.py
│   │   ├── document_schema.py
│   │   ├── stt_schema.py
│   │   └── response_schema.py
│   ├── db/
│   └── modules/
│
├── frontend/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── data/
│   │   ├── fonts/
│   │   ├── pages/
│   │   ├── App.css
│   │   ├── App.tsx
│   │   ├── index.css
│   │   └── main.tsx
│   ├── .gitignore
│   ├── .gitkeep
│   ├── README.md
│   ├── convertFont.py
│   ├── eslint.config.js
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.app.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   └── vite.config.ts
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

<br />

## Getting Started

### 1. Repository Clone

```bash
git clone https://github.com/botato1/AI-Agent-System.git
cd AI-Agent-System
```

<br />

## Backend 실행 방법

### 1. 가상환경 생성

```bash
python -m venv .venv
```

### 2. 가상환경 활성화

Mac / Linux

```bash
source .venv/bin/activate
```

Windows

```bash
source .venv/Scripts/activate
```

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정

`.env.example` 파일을 참고하여 `.env` 파일을 생성합니다.

```bash
cp .env.example .env
```

예시:

```env
NOTION_TOKEN=
NOTION_DATABASE_ID=
OLLAMA_BASE_URL=
CHROMA_DB_PATH=
```

### 5. 로컬 개발 서버 실행

```bash
uvicorn backend.main:app --reload
```

로컬 환경에서는 아래 주소에서 API 문서를 확인할 수 있습니다.

```text
http://127.0.0.1:8000/docs
```

### 6. 서버 환경 실행

서버 환경에서 외부 접속이 필요한 경우에는 아래처럼 실행합니다.

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

서버 환경에서는 아래 주소에서 API 문서를 확인할 수 있습니다.

```text
http://192.168.0.22:8000/docs
```

<br />

## Frontend 실행 방법

### 1. 프론트엔드 폴더로 이동

```bash
cd frontend
```

### 2. 패키지 설치

```bash
npm install
```

### 3. 개발 서버 실행

```bash
npm run dev
```

실행 후 터미널에 표시되는 로컬 주소로 접속합니다.

```text
http://localhost:5173
```

<br />

## Contributors

| Name | Role |
| --- | --- |
| 가동현 | Project Lead, Agent Workflow, LangGraph |
| 문지수 | Backend, FastAPI, LangGraph Agent, API Integration |
| 이승주 | LLM, RAG, ChromaDB, Embedding |
| 정승현 | Document Processing, PDF Parser, OCR |
| 이준오 | Voice Processing, Whisper STT |
| 김나연 | Frontend, React UI |

<br />

## Branch Convention

| Branch | Description |
| --- | --- |
| `main` | 배포 가능한 최종 브랜치 |
| `develop` | 개발 통합 브랜치 |
| `feature/*` | 기능 개발 브랜치 |


<br />

## Commit Convention

| Type | Description |
| --- | --- |
| `feat` | 새로운 기능 추가 |
| `fix` | 버그 수정 |
| `docs` | 문서 수정 |
| `refactor` | 코드 리팩토링 |
| `chore` | 설정, 빌드, 패키지 등 기타 작업 |
| `test` | 테스트 코드 추가 또는 수정 |

예시:

```bash
feat: add document upload API
fix: resolve document_id mismatch in RAG search
docs: update README
```

<br />

## Expected Effect

- 회의록, 문서, 음성 자료를 자동으로 정리할 수 있습니다.
- 사용자는 긴 문서를 직접 읽지 않고 필요한 내용을 빠르게 확인할 수 있습니다.
- 회의나 문서에서 나온 할 일을 자동으로 추출할 수 있습니다.
- 업로드된 문서를 기반으로 질문하고 답변받을 수 있습니다.
- 정리된 업무 정보를 Notion에 저장하여 팀 단위로 관리할 수 있습니다.

<br />

## Future Improvements

- 사용자별 문서 권한 관리
- 채팅방별 문서 연결 기능 고도화
- IDE 또는 터미널 로그 자동 수집 기능
- 일정 추출 및 캘린더 연동
- Agent 실행 흐름 시각화
- PaddleOCR-VL 활성화 및 문서 이해 성능 개선
- 서버 이관 및 배포 환경 구축

<br />

## License

This project is developed for academic and team project purposes.
