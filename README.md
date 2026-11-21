<div align="center">

<!-- Animated Architectural Hero Banner (Embedded Official ET DEVNEXT'26 Lockup + SVG Motion) -->
<a href="https://devnext-adk-145989035319.asia-south1.run.app">
  <img src="assets/hero-banner.svg" alt="ET TechGig DevNext '26 — Google ADK + Hybrid Gemini RAG Concierge" width="100%" />
</a>

<br />

<!-- Primary Action CTA Badges -->
[![Live Demo on Cloud Run](https://img.shields.io/badge/%F0%9F%9A%80_LIVE_DEMO-CLOUD_RUN_(ASIA--SOUTH1)-CFA55A?style=for-the-badge&logo=googlecloud&logoColor=1E1915&labelColor=1E1915)](https://devnext-adk-145989035319.asia-south1.run.app)
[![Official Event Page](https://img.shields.io/badge/%F0%9F%8F%9B%EF%B8%8F_EVENT_SITE-TECHGIG.COM%2FDEVNEXT-A67C37?style=for-the-badge&labelColor=2A1D10)](https://techgig.com/devnext)
[![Connect on LinkedIn](https://img.shields.io/badge/LINKEDIN-ASHUTOSH_S._BHAKARE-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/abhakare/)

<!-- Technology Stack Logo Badges -->
![Google ADK](https://img.shields.io/badge/Google_ADK-v2.15+-4285F4?style=flat-square&logo=google&logoColor=white)
![Gemini 3.8 Flash](https://img.shields.io/badge/Gemini_3.8_Flash-Agent_LLM-8E75B2?style=flat-square&logo=googlegemini&logoColor=white)
![Gemini Embeddings](https://img.shields.io/badge/gemini--embedding--001-Vector_RAG-34A853?style=flat-square&logo=googlegemini&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Custom_UI_Backend-009688?style=flat-square&logo=fastapi&logoColor=white)
![Python 3.11](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-Cosine_%2B_BM25-013243?style=flat-square&logo=numpy&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=flat-square&logo=docker&logoColor=white)
![Cloud Run](https://img.shields.io/badge/Google_Cloud_Run-Serverless-FBBC04?style=flat-square&logo=googlecloud&logoColor=black)

<p align="center">
  <strong>An event-scoped AI Concierge built with the Google Agent Development Kit (<code>google-adk</code>) and Hybrid Gemini RAG — wrapped in a bespoke <em>ET TechGig DevNext ’26</em> interface instead of the default <code>adk web</code> UI.</strong>
</p>

</div>

<img src="assets/gold-divider.svg" alt="" width="100%" />

## `// LIVE CONVERSATION & GUARDRAIL PREVIEW`

<div align="center">
  <img src="assets/live-demo-preview.svg" alt="Animated DevNext '26 Chat & Guardrail Preview" width="100%" />
</div>

<br />

| Capability | What Makes This Implementation Different |
| :--- | :--- |
| 🎨 **Authentic DevNext ’26 UI** | Replaces default `adk web` developer chrome with the live event's **warm ivory (`#FAF6F0`), espresso-bronze, chamfered stat cards, metallic gold CTAs, and floating pill navbar**. |
| 🧠 **Google ADK Stateful Engine** | Uses `Agent`, `Runner`, and `InMemorySessionService` with **`gemini-3.8-flash`** for multi-turn conversational context over clean FastAPI endpoints. |
| ⚡ **Hybrid Vector + BM25 RAG** | Fuses **`gemini-embedding-001`** dense cosine similarity (`0.70`) + **BM25** lexical ranking (`0.30`) with `.rag_cache.json` disk caching and inline **Grounded Source Citations**. |
| 🛡️ **Strict Event-Only Guardrail** | Hard-locked to **ET TechGig DevNext ’26** (Hyderabad • Nov 21, 2026); politely declines general coding, math, trivia, or off-topic prompts. |
| ☁️ **Zero-Cold-Wait Cloud Run** | Containerized and deployed on **Google Cloud Run (`asia-south1`)** with precomputed vector cache for instant startup. |

<img src="assets/gold-divider.svg" alt="" width="100%" />

## `// ANIMATED SYSTEM ARCHITECTURE`

<div align="center">
  <img src="assets/rag-pipeline-animated.svg" alt="Animated Google ADK + Hybrid RAG Pipeline" width="100%" />
</div>

<details>
<summary><strong>📐 View Mermaid Architecture Source</strong></summary>

```mermaid
flowchart LR
    UI["Custom DevNext '26 Web UI<br/>(HTML / CSS / JS)"] -->|POST /api/chat| API["FastAPI Backend<br/>(app.py)"]
    API --> Runner["Google ADK Runner +<br/>InMemorySessionService"]
    Runner --> Agent["ADK Agent<br/>(gemini-3.8-flash)"]
    Agent -->|Function Tool| RAG["search_devnext_knowledge<br/>(rag.py)"]
    RAG --> Embed["Gemini Embeddings<br/>(gemini-embedding-001)"]
    RAG --> BM25["BM25 Lexical Index"]
    Embed & BM25 --> KB[("Event Corpus<br/>knowledge_base/*.md")]
```

</details>

<img src="assets/gold-divider.svg" alt="" width="100%" />

## `// REPOSITORY STRUCTURE`

```text
devnext-adk/
├── app.py                        # FastAPI server wiring ADK Runner, Sessions & custom UI routes
├── devnext_agent/
│   ├── __init__.py               # Package exports (root_agent, build_agent)
│   ├── agent.py                  # Google ADK Agent (gemini-3.8-flash) + strict event-only instructions
│   └── rag.py                    # Hybrid RAG engine (gemini-embedding-001 + BM25 + citation tracking)
├── knowledge_base/
│   └── devnext_2026_kb.md        # 10 structured event sections from techgig.com/devnext
├── templates/
│   └── index.html                # Custom ET TechGig DevNext '26 UI layout
├── static/
│   ├── styles.css                # Warm bronze/gold/ivory DevNext '26 design system
│   └── app.js                    # Session chat, Markdown renderer & RAG source citations drawer
├── assets/                       # Animated SVG hero, RAG pipeline & chat showcase graphics
├── image.png                     # Official ET TechGig DevNext '26 hero logo lockup
├── Dockerfile                    # Production container image for Google Cloud Run
└── requirements.txt              # Python dependencies
```

<img src="assets/gold-divider.svg" alt="" width="100%" />

## `// QUICK START (LOCAL & CLOUD RUN)`

### 1. Clone & Install Dependencies

```powershell
git clone https://github.com/bhakareashutosh/devnext-adk.git
cd devnext-adk

python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt   # Linux/macOS: ./.venv/bin/pip install -r requirements.txt
```

### 2. Configure Your Gemini API Key

Copy `.env.example` to `.env` and set your [Google AI Studio API Key](https://aistudio.google.com/apikey) *(or click **Configure Key** directly in the web UI navbar)*:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash
EMBEDDING_MODEL=gemini-embedding-001
```

### 3. Run Locally

```powershell
.\.venv\Scripts\python.exe app.py
```

Open **`http://127.0.0.1:8080`** in your browser. Drop any extra `.md` or `.txt` files into `knowledge_base/` to automatically index additional event content.

### 4. One-Command Deploy to Google Cloud Run

```bash
gcloud run deploy devnext-adk \
  --source . \
  --project=YOUR_GCP_PROJECT_ID \
  --region=asia-south1 \
  --allow-unauthenticated \
  --port=8080 \
  --memory=1Gi \
  --set-env-vars="GOOGLE_API_KEY=YOUR_API_KEY,GEMINI_MODEL=gemini-3.8-flash,EMBEDDING_MODEL=gemini-embedding-001"
```

<img src="assets/gold-divider.svg" alt="" width="100%" />

## `// AUTHOR & SPEAKER SPOTLIGHT`

<div align="center">

### **Ashutosh S. Bhakare**
**Featured Speaker — ET TechGig DevNext ’26 (Hyderabad)**  
*Founder & CEO at **[BYOLabs.in](https://byolabs.in)** • Director & Chief Corporate Trainer at **[Unnati Development & Training Centre Pvt. Ltd.](https://unnatidevelopment.in)***

<br />

<!-- Credentials & Ecosystem Badges with Official Logos -->
![Google Authorized Trainer](https://img.shields.io/badge/Google_Authorized_Trainer-Cloud_%26_AI-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)
![Docker Captain](https://img.shields.io/badge/Docker_Captain-Community_Leader-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Red Hat RHCA / RHCI](https://img.shields.io/badge/Red_Hat-RHCA_%26_RHCI-EE0000?style=for-the-badge&logo=redhat&logoColor=white)
![CNCF Certified](https://img.shields.io/badge/CNCF-CKA_%7C_CKAD_%7C_CKS-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)
![SUSE Certified Instructor](https://img.shields.io/badge/SUSE-Certified_Instructor-73BA25?style=for-the-badge&logo=suse&logoColor=white)

<p align="center">
  25+ years of international consulting, architecture, and corporate training experience across <strong>Cloud Computing, Agentic AI Systems, Kubernetes, DevOps, and Enterprise Linux</strong> across India, Australia, Singapore, Indonesia, and Hong Kong.
</p>

[![LinkedIn](https://img.shields.io/badge/Connect_on_LinkedIn-@abhakare-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/abhakare/)
[![GitHub](https://img.shields.io/badge/Follow_on_GitHub-@bhakareashutosh-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/bhakareashutosh)
[![BYOLabs](https://img.shields.io/badge/Interactive_Labs-BYOLabs.in-CFA55A?style=for-the-badge&labelColor=1E1915)](https://byolabs.in)

</div>
