# SHL Assessment Recommender Assistant

A conversational assistant designed for recruiters to recommend relevant SHL assessments based on job role, seniority level, and candidate skill requirements. The assistant leverages a custom pure-Python **BM25 TF-IDF Retrieval-Augmented Generation (RAG)** engine grounded strictly on the SHL product catalog to prevent hallucination.

## Features

- **Dynamic Grounded RAG Recommendations:** Selects and explains the 5 most relevant SHL assessments from the catalog based on the job role.
- **State-Tracking Dialogue Manager:** Tracks recruiter requirements across conversation turns, with smart filters for greetings, off-topic chats, and gibberish.
- **Seniority Bleed Prevention:** Automatically resets state/seniority checks when switching between different job roles.
- **Unified Interface:** Serves a premium, responsive web chat client directly from the FastAPI backend.
- **Render Ready:** Includes cloud deployment configurations out of the box.

---

## Project Structure

```text
├── agent.py          # Dialogue processing and prompt manager
├── catalog.py        # Local TF-IDF BM25 retrieval index
├── catalog.json      # SHL Product Assessment catalog database
├── llm_client.py     # Google Gemini API connector with mock fallback
├── main.py           # FastAPI server and static file endpoints
├── test_ui.html      # Premium HTML/JS web chat interface
├── requirements.txt  # Python package dependencies
└── render.yaml       # Render cloud deployment blueprint
```

---

## Local Setup & Run

### 1. Install Dependencies
Make sure you have Python 3.8+ installed. Run:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY="your_google_gemini_api_key_here"
```

### 3. Run the Server
Start the FastAPI backend server:
```bash
python main.py
```
By default, the server runs on `http://localhost:8000`. 

### 4. Access the Application
Open your browser and visit:
```text
http://localhost:8000/
```
This loads the dynamic web client interface directly.

---

## Deployment on Render

This project is configured to deploy as a unified Web Service on Render.

1. Go to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** and select **Blueprint**.
3. Connect this GitHub repository.
4. Render will read the configuration from `render.yaml` automatically.
5. In the environment variables prompt, enter your `GEMINI_API_KEY`.
6. Click **Approve** and let Render build and deploy.

---

## Architecture Detail: BM25 RAG
To prevent LLM hallucination:
1. Recruiter requests are analyzed to extract the target job role.
2. A pure-Python **BM25 TF-IDF** engine tokenizes and ranks matching assessments from the 41 items in `catalog.json`, giving higher weights to rare technology terms (e.g. `java`, `python`, `deductive`).
3. The ranked candidates are injected into the Gemini context.
4. Gemini selects exactly 5 assessments and writes a professional explanation grounded *strictly* in the provided catalog text.
