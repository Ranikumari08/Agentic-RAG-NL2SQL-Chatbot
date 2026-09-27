Built an agentic RAG + NL2SQL chatbot using LangGraph with autonomous agents handling generic queries, deep research, tool calling, and structured database queries via hybrid search, metadata filtering, chunk-based reasoning, and NL2SQL generation

Designed a flexible ingestion pipeline supporting PDF, TXT, HTML, MP3, and web links, with scrape/crawl options, document- and chunk-level metadata extraction, and embedding storage for both RAG and NL2SQL query

Enabled user-defined field configurations as dynamic filters across agentic and NL2SQL workflows; used Pydantic for structured outputs and Celery with SQS for async ingestion and task orchestration

Integrated support for user-defined tools (API calls) and database access via cURL and SQL execution, triggered when the supervisor agent detects the need, enabling dynamic external tool usage and real-time NL2SQL execution

Currently building this project:

Concrete build is for a healthcare clinic (Lifespring Clinic): Postgres backend (via psycopg2 pool in db.py) with tables departments, doctors, patients, appointments, billing, lab_tests, medical_records, medications, prescriptions

Has agent tool modules per domain: doctors_tools.py (availability), appointment_tools.py (book/cancel), pharmacy_tools.py (medicine availability), lab_tools.py (test availability), notification_tools.py (send notification)

Has supporting scripts: insert_data.py (loads CSVs into Postgres), schema_check.py (verifies DB schema), test_tools.py (exercises the tool functions)
Also has 11 clinic PDFs (billing, pharmacy policy, emergency, treatment info, symptoms guidance, follow-up care, consultation process, clinic services/overview, appointment booking, doctor profiles) as the RAG corpus alongside the CSV-backed structured data

Project folder is named Lifespring_Agentic_AI, structured as: nl2sql/data (CSVs + generate_data.py + insert_data.py), rag/ (the 11 PDFs), tools/ (db.py, appointment_tools.py, doctors_tools.py, lab_tools.py, notification_tools.py, pharmacy_tools.py, schema_check.py, test_tools.py, requirements.txt, .env)

Data generation, CSV creation, and Postgres insertion are already done via VS Code; virtual environment is already set up

Target architecture: one supervisor agent receives the query and routes to three sub-agents — a RAG agent, an NL2SQL agent, and a tool-calling agent — which together complete the flow

Project structure preference: all agent files (rag_agent.py, and the upcoming NL2SQL agent and tool-calling agent) live together under one agent/ folder, alongside the existing rag/ (docs) and tools/ (tool functions) folders

RAG agent (agent/rag_agent.py) and ingestion script (ingest_pdfs.py) are working end-to-end: chunks the 11 PDFs (flatten-then-size-split approach, ~1000 char chunks, 3 per doc, 33 total) into ChromaDB via its built-in ONNX embedding function, retrieves via similarity search, and generates answers via Groq (openai/gpt-oss-120b)

NL2SQL agent (agent/nl2sql_agent.py) built and tested successfully: generates SQL via Groq against the confirmed Postgres schema (departments, doctors, patients, appointments, billing, lab_tests, medical_records, medications, prescriptions), guards against non-SELECT/stacked queries, executes via tools/db.py's existing connection pool, and summarizes results in natural language — passed lookup, aggregation, empty-result, and write-action-refusal test cases

Tool-calling agent (agent/tool_calling_agent.py) built and tested successfully: wraps the 5 existing tool modules (doctors, appointment book/cancel, pharmacy, lab, notification) as Groq function-calling tools, with a multi-round dispatch loop, argument-parsing/unknown-tool error handling, and a guard against runaway tool-call loops — passed availability check, medicine check, real appointment booking (wrote to Postgres), and correctly made zero tool calls on an off-topic query

All three sub-agents (RAG, NL2SQL, tool-calling) are now built and individually tested; next step is the supervisor agent + LangGraph routing between them
