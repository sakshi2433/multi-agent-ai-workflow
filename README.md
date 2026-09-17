# 🤖 Multi-Agent AI Workflow with Tool Calling

A production-style agentic AI system where multiple specialized agents collaborate to complete complex user requests — built with **LangGraph**, **FastAPI**, and **PostgreSQL**.

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-orchestration-6f42c1.svg)
![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)

---

## ✨ Overview

This project implements a multi-agent AI workflow system featuring:

- 🧠 **Planner Agent** — Breaks down user requests into structured plans
- 🔎 **Research Agent** — Collects and analyzes information
- 🗄️ **Database Agent** — Executes safe database queries
- 💻 **Code Agent** — Performs controlled code analysis and transformations
- 🧩 **Synthesis Agent** — Combines results into coherent responses

<!--
📸 SCREENSHOT 1 — Dashboard
-->
<p align="center">
  <img src="docs/screenshots/dashboard.png" alt="Dashboard screenshot" width="800">
  <br>
  <em>Dashboard overview</em>
</p>

---

## 🏗️ Architecture

```mermaid
graph TD
    Client((Client)) --> API[FastAPI API]
    API --> Orchestrator[LangGraph Orchestrator]
    Orchestrator --> Planner[Planner Agent]
    Orchestrator --> Workers[Worker Agents]
    Workers --> ToolLayer[Tool Layer]
    ToolLayer --> DB[(PostgreSQL)]
    ToolLayer --> External
    ToolLayer --> Cache[(Redis)]
    Orchestrator -.-> Approval[Human Approval Checkpoint]
```

<!--
📸 SCREENSHOT 2 — Dynamic Agent Visualization
-->
<p align="center">
  <img src="docs/screenshots/agent-visualization.png" alt="Dynamic agent visualization" width="800">
  <br>
  <em>Dynamic agent visualization</em>
</p>

---

## 🤖 Agent Responsibilities

### 1. Planner Agent
- Receives high-level user goals
- Decomposes into ordered subtasks
- Assigns subtasks to appropriate workers
- Creates structured execution plans

### 2. Research Agent
- Conducts web searches and research
- Gathers relevant information
- Returns structured findings
- Handles search failures gracefully

### 3. Database Agent
- Executes safe database queries
- Never allows destructive operations
- Uses typed tool parameters
- Returns structured query results

### 4. Code Agent
- Performs controlled code analysis
- Executes safe code transformations
- Provides structured output
- Includes execution metadata

### 5. Synthesis Agent
- Combines worker outputs
- Creates coherent final responses
- Distinguishes success/failure
- Formats user-friendly results

---

## 🔄 Workflow Lifecycle

1. **User Request** — Client submits a task to `/workflows`
2. **Planning** — Planner decomposes the request into subtasks
3. **Execution** — Workers execute assigned subtasks
4. **Human Approval** — Critical actions pause for approval
5. **Synthesis** — Results are combined and formatted
6. **Completion** — Final response is returned to client

---

## 🛡️ Safety Mechanisms

| Mechanism | Description |
|---|---|
| **Step Limits** | Maximum configurable steps per workflow; prevents infinite execution; marks workflows as "limited" when exceeded |
| **Loop Prevention** | Tracks agent transitions, monitors repeated tool calls, detects and blocks cycles |
| **Budget Enforcement** | Per-run token/cost budget with continuous usage monitoring and automatic termination |
| **Human-in-the-Loop** | Approval required for destructive actions via explicit approve/reject endpoints; resumes only after approval |

---

## 📡 API Endpoints

### Workflow Management
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/workflows` | Create and start a workflow |
| `GET` | `/workflows/{id}` | Get workflow state |
| `GET` | `/workflows/{id}/trace` | Get execution trace |
| `POST` | `/workflows/{id}/approve` | Approve pending checkpoint |
| `POST` | `/workflows/{id}/reject` | Reject pending checkpoint |
| `POST` | `/workflows/{id}/resume` | Resume interrupted workflow |

### Health Check
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health status |

---

## 🚀 Local Setup

### Prerequisites
- Python 3.12+
- PostgreSQL (9.6+)
- Redis (optional but recommended)

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd project-directory

# Install Python dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_database.py

# Set up environment
export $(cat .env)

# Run migrations
python -m alembic upgrade head

# Start the application
python -m app.api.main
```

### Docker Setup

```bash
# Build and start services
docker-compose up -d
```

| Service | URL |
|---|---|
| FastAPI API | http://localhost:8000 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

---

## ⚙️ Environment Variables

```env
# LLM Configuration
# Set LLM_MODE to "online" to use real OpenRouter API, or "offline" for mock mode
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=your_model_name
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
LLM_MODE=offline
LLM_TIMEOUT_SECONDS=30

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/yourdb

# Redis
REDIS_URL=redis://localhost:6379

# Workflow Configuration
MAX_WORKFLOW_STEPS=100
WORKFLOW_BUDGET_LIMIT=10.0  # USD

# Tool Configuration
TOOL_TIMEOUT=30
MAX_RETRIES=3

# Approval Configuration
APPROVAL_REQUIRED=true
```

---

## 🔌 LLM Integration

This project uses OpenRouter for LLM integration with support for multiple models and providers.

### Modes of Operation

#### 1. Online Mode (Production)
```env
LLM_MODE=online
OPENROUTER_API_KEY=your_actual_api_key
OPENROUTER_MODEL=openai/gpt-3.5-turbo
```
- PlannerAgent uses the LLM to intelligently decompose user requests into subtasks
- SynthesisAgent uses the LLM to generate natural language summaries of results
- All API calls go to OpenRouter
- Requires a valid API key

#### 2. Offline Mode (Development/Testing)
```env
LLM_MODE=offline
```
- PlannerAgent returns mock structured plans
- SynthesisAgent returns mock synthesized responses
- No API calls are made, no API key required
- Useful for testing and development without incurring API costs

### Setting Up OpenRouter API

1. Sign up at [openrouter.ai](https://openrouter.ai)
2. Get your API key from the dashboard
3. Add to `.env`:
   ```env
   OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxxxxxxxxxx
   ```

### Supported Models

OpenRouter supports hundreds of models from different providers:

```bash
# Popular options:
- openai/gpt-3.5-turbo       # fast, low cost
- openai/gpt-4               # most capable
- anthropic/claude-2         # strong reasoning
- meta-llama/llama-2-70b     # open source
```

Check available models at: https://openrouter.ai/docs/models

### Error Handling

The LLM client includes robust error handling for:
- **Missing API Key** — Falls back to offline mode if not provided
- **Network Errors** — Logs and falls back to keyword matching for planner
- **Malformed Responses** — Validates JSON structure and provides detailed errors
- **Timeout Errors** — Configurable timeout with graceful degradation
- **API Rate Limits** — Proper error messages for rate limit errors

All errors are logged but do not crash the workflow — the system continues with fallback mechanisms.

### Using the LLM Client

```python
from app.clients.llm import LLMClient

# Create client in online mode
llm = LLMClient(offline_mode=False)

# Generate text
result = await llm.generate("Your prompt here")
if result["success"]:
    print(result["content"])

# Generate and parse JSON
result = await llm.parse_json(
    prompt="Create a plan",
    expected_keys=["subtasks"]
)
if result["success"]:
    plan = result["data"]
```

---

## 📊 Example Workflow

**Request:** *"Research the recent advances in transformer models and create a summary."*

1. **Planning** — Planner creates subtasks:
   - Research recent transformer papers
   - Summarize key advances
   - Format final response

2. **Execution** — Research agent executes:
   - Searches web for recent papers
   - Extracts key information
   - Handles failures gracefully

<!--
📸 SCREENSHOT 3 — Execution Trace
-->
<p align="center">
  <img src="docs/screenshots/execution-trace.png" alt="Execution trace screenshot" width="800">
  <br>
  <em>Execution trace</em>
</p>

3. **Synthesis** — Synthesis agent compiles:
   - Combines findings
   - Distinguishes reliable info
   - Returns formatted response

4. **Completion** — Final response sent to client

<!--
📸 SCREENSHOT 4 — Final Synthesized Result
-->
<p align="center">
  <img src="docs/screenshots/final-result.png" alt="Final synthesized result screenshot" width="800">
  <br>
  <em>Final synthesized result</em>
</p>

---

## 🧪 Testing

The project includes comprehensive tests covering:

1. **Planner Functionality** — Plan creation and validation
2. **Agent Handoffs** — Worker agent coordination
3. **Tool Validation** — Schema verification and execution
4. **Safety Mechanisms** — Step limits, budget, loops
5. **API Endpoints** — All API functionality
6. **End-to-End Workflows** — Complete execution scenarios

```bash
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
python scripts/run_evaluation.py  # Evaluation suite
pytest                      # Run all tests
```

## 📈 Evaluation

The evaluation suite runs 20+ representative scenarios covering:

- Simple and multi-step research tasks
- Database operations
- Tool failures and retries
- Safety mechanism enforcement
- Human approval workflows
- Budget and step limits
- Workflow interruption and resumption

Results are saved to `evaluation_results.json`.

---

## ⚠️ Known Limitations

- Evaluation uses simulated APIs where real services aren't available
- Resource-intensive operations may hit budget limits
- Workflow state persistence is limited to PostgreSQL

## 🗺️ Future Improvements

- [ ] Add more specialized worker agents
- [ ] Integrate additional tool types
- [ ] Implement more advanced planning strategies
- [ ] Add support for external MCP servers
- [ ] Enhance monitoring and observability
- [ ] Implement workflow templates
- [ ] Add support for conversational memory

---

## 📁 Project Structure

```
.
├── app/
│   ├── api/            # FastAPI API layer
│   ├── agents/         # Agent implementations
│   ├── graph/          # LangGraph workflows
│   ├── tools/          # Tool implementations
│   ├── models/         # Pydantic schemas
│   ├── services/       # Business logic
│   ├── repositories/   # Database operations
│   ├── core/           # Core abstractions
│   ├── schemas/        # Shared schemas
│   └── observability/  # Monitoring and logging
├── tests/
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── evaluation/      # Evaluation scenarios
├── scripts/             # Development scripts
├── docker/              # Docker configurations
├── docs/
│   └── screenshots/     # README screenshots
├── .env.example         # Environment template
└── requirements.txt     # Dependencies
```

---
