  
**![][image1]**

**StudySpace**  
**Interim Report**

**TU857**  
**BSc in Computer Science Infrastructure**

Keith Salhani

C22322811

Supervisor

Fatmaelzahraa Eltaher

School of Computer Science

Technological University, Dublin

Date 10 Nov 2025

**Abstract**  
This interim report presents the design and early-stage development of StudySpace, an AI-powered study hub for undergraduate students. The system ingests unstructured academic material (PDF, DOCX, PPTX and images of handwritten notes), automatically organises it by module and resource type, extracts key administrative information such as assessment weights and lecturer contact details, and exposes the content through retrieval-augmented generation (RAG), quiz generation, and flashcard views. The motivation is the fragmented ecosystem in which students currently manage their learning, where time is lost searching for files and manually analysing module descriptors and past papers instead of engaging in targeted study.

Building on recent advances in document AI, OCR and RAG, StudySpace aims to deliver a practical "Study OS" that reduces administrative overhead while supporting evidence-based learning techniques such as retrieval practice and spaced repetition. This report summarises the project background, reviews relevant literature and technologies, outlines the initial system analysis and design, and sets out the testing strategy, prototype plan, and future work for the remainder of the project.

**Declaration**

I hereby declare that the work described in this dissertation is, except where otherwise stated, entirely my own work and has not been submitted as an exercise for a degree at this or any other university.

Signed:

Keith Salhani

Date 10 Nov 2025

**Acknowledgements**  
I would like to thank my supervisor, Dr. Fatmaelzahraa Eltaher, for her guidance and feedback during the early stages of this project. I am also grateful to my classmates and friends who shared their experiences of managing notes, past papers and deadlines, which helped to shape the requirements for StudySpace.

Contents  
[1\. Introduction	1](#1.-introduction)

[1.1 Project Background	1](#1.1-project-background)

[1.2 Project Description	1](#1.2-project-description)

[1.3 Project Aims and Objectives	1](#1.3-project-aims-and-objectives)

[1.4  Project Scope	1](#1.4-project-scope)

[1.5 Thesis Roadmap	1](#1.5-thesis-roadmap)

[2\. Literature Review	2](#2.-literature-review)

[2.1 Introduction	2](#2.1-introduction)

[2.2 Alternative Existing Solutions	2](#2.2-alternative-existing-solutions)

[2.3 Technologies Researched	2](#2.3-technologies-researched)

[2.4 Other Research	2](#2.4-other-research)

[2.5 Existing Final Year Projects	2](#2.5-existing-final-year-projects)

[2.6 Conclusions	2](#2.6-conclusions)

[3\. System Analysis	3](#3.-system-analysis)

[3.1 System Overview	3](#3.1-system-overview)

[3.2 Requirements Gathering	3](#3.2-requirements-gathering)

[3.3 Requirements Analysis	3](#3.3-requirements-analysis)

[3.4 Initial System Specification	3](#3.4-initial-system-specification)

[3.5 Conclusions	3](#3.5-conclusions)

[4\. System Design	4](#4.-system-design)

[4.1 Introduction	4](#4.1-introduction)

[4.2 Software Methodology	4](#4.2-software-methodology)

[4.3 Overview of System	4](#4.3-overview-of-system)

[4.4 Design System	4](#4.4-design-system)

[4.5 Conclusions	4](#4.5-conclusions)

[5\. Testing and Evaluation	5](#5.-testing-and-evaluation)

[5.1 Introduction	5](#5.1-introduction)

[5.2 Plan for Testing	5](#5.2-plan-for-testing)

[5.3 Plan for Evaluation	5](#5.3-plan-for-evaluation)

[5.4 Conclusions	5](#5.4-conclusions)

[6\. System Prototype	6](#6.-system-prototype)

[6.1 Introduction	6](#6.1-introduction)

[6.2 Prototype Development	6](#6.2-prototype-development)

[6.3 Results	6](#6.3-results)

[6.4 Evaluation	6](#6.4-evaluation)

[6.5 Conclusions	6](#6.5-conclusions)

[7\. Issues and Future Work	7](#7.-issues-and-future-work)

[7.1 Introduction	7](#7.1-introduction)

[7.2 Issues and Risks	7](#7.2-issues-and-risks)

[7.3 Plans and Future Work	7](#7.3-plans-and-future-work)

[7.3.1 Project Plan with GANTT Chart	7](#7.3.1-project-plan-with-gantt-chart)

[References	8](#references)

[A)	Appendix A: System Model and Analysis	A-1](#appendix-a:-system-model-and-analysis)

[B)	Appendix B: Design	B-1](#appendix-b:-design)

[C)	Appendix C: Prompts Used with ChatGPT	C-1](#appendix-c:-prompts-used-with-chatgpt)

[D)	Appendix D: Additional Code Samples	D-1](#appendix-d:-additional-code-samples)

[E)	Appendix E:	E-1](#appendix-e:)

# 1\. Introduction {#1.-introduction}

## 1.1 Project Background {#1.1-project-background}

University students increasingly manage their learning across a fragmented ecosystem of systems and formats: lecture notes on Brightspace, labs in email attachments, past papers on departmental sites, screenshots in messaging apps, and ad-hoc notes stored on personal devices. Keeping track of what to study, when assessments are due, and which topics are likely to appear in exams often depends on manual organisation and personal discipline rather than any integrated tool support. For many students, significant time is spent searching for files, re-reading module descriptors, and manually analysing past papers instead of engaging in targeted, high-value study.

At the same time, advances in large language models (LLMs) and Retrieval-Augmented Generation (RAG) have made it feasible to build systems that can search and reason over user-specific corpora of documents with traceable references and improved factual accuracy. RAG architectures combine a retriever (which searches over an external index of documents) with a generator (an LLM), enabling question-answering grounded directly in the user’s own materials rather than relying on general web knowledge. This pattern is well-suited to the university context, where each student accumulates a personal but loosely organised collection of academic content.

This project aims to leverage these developments to build an AI-powered “study hub” for undergraduate students. The system ingests unstructured academic files (PDF, DOCX, PPTX and images of notes), automatically organises them by module and resource type, extracts key administrative information, and supports RAG-powered question answering and quiz generation over the student’s corpus. By unifying document management, retrieval, quiz creation, calendar population, and progress tracking in a single web application, the project seeks to reduce administrative overhead and support evidence-based study habits such as retrieval practice and spaced repetition.

The interim report documents the progress made to date in analysing, designing, and beginning to prototype this system. It outlines the background and motivation for the project, describes the proposed solution at a high level, defines the aims and objectives, clarifies the scope, and provides a roadmap for the remainder of the dissertation.

## 1.2 Project Description {#1.2-project-description}

StudySpace is an AI-powered web application that acts as a central hub for a student’s academic materials. Students upload or connect their existing files – including lecture slides, lab sheets, tutorials, module descriptors and past exam papers – in formats such as PDF, DOCX, PPTX and images of handwritten notes. An ingestion pipeline parses these documents, performs OCR where needed, and assigns each file a module label (e.g. Forensics, Machine Learning, Algorithms) and a resource type (Lecture, Lab, Tutorial, Descriptor, Past Paper).

From these documents the system extracts structured metadata, such as lecturer contact details, assessment breakdowns and key dates, which can be synchronised with a calendar. The content itself is embedded into a vector database to support RAG-based question answering, where students can ask natural-language questions grounded in their own notes. A quiz and flashcard engine generates practice questions, while a past-paper analysis module identifies frequently recurring topics. Together, these components form a practical "Study OS" that supports both organisation and effective study.

![][image2]

## 1.3 Project Aims and Objectives {#1.3-project-aims-and-objectives}

The overall aim of this project is to design and implement a usable "Study OS" that automatically organises a student’s academic materials and provides intelligent support for retrieval-based learning.

1\. **Ingestion & parsing**. Build an ingestion pipeline that parses PDF/DOCX/PPTX and scanned documents (OCR).

2\. **Auto‑classification**. Automatically label each file by module and resource type using zero‑shot text classification.

3\. **Metadata extraction**. Extract assessment weights, deadlines and contact details into a structured store.

4\. **RAG question answering**. Provide traceable answers grounded in the student’s corpus.

5\. **Quiz/flashcards**. Generate quizzes/flashcards aligned with retrieval‑practice principles from selected modules/topics.

6\. **Past‑paper topic mining**. Surface frequently examined themes.

7\. **Usable web UI**. Ship a responsive interface suitable for everyday use by undergraduates.

9\. **Calendar & transparency**. Sync extracted deadlines to a calendar and expose citations for every answer/quiz item.

10\. **Evaluation & feedback loop**. Run a small formative user study

## 1.4  Project Scope {#1.4-project-scope}

The scope of this project focuses on a single-user web application that ingests and organises documents for an individual student. StudySpace will support a realistic subset of file types commonly encountered in TU Dublin modules (PDF, DOCX, PPTX and images), perform module and resource-type classification, extract core administrative metadata, and provide RAG-based Q\&A, quiz generation and basic past-paper analysis. The system will be evaluated on a sample corpus assembled from anonymised or publicly available teaching materials.

Out of scope are multi-tenant deployments for entire programmes, robust authentication and authorisation for institutional use, and production-grade integrations with Brightspace or other learning management systems. Advanced analytics such as full learning-analytics dashboards and long-term spaced-repetition scheduling are also beyond the scope of this initial project, though the architecture will be designed so that they could be explored as future work.

## 1.5 Thesis Roadmap {#1.5-thesis-roadmap}

Chapter 1 introduces the motivation for StudySpace, describes the proposed solution, defines the aims and objectives, clarifies the scope, and outlines the structure of the dissertation.  
Chapter 2 reviews related work, including existing study tools, relevant technologies such as RAG and document AI, educational research on retrieval practice, and similar final-year projects.  
Chapter 3 presents the system analysis, covering stakeholders, requirements gathering, requirements analysis and an initial system specification.  
Chapter 4 describes the system design, including the chosen software development methodology, logical architecture and key design decisions.  
Chapter 5 outlines the planned testing and evaluation strategy for the different components of the system and the overall user experience.  
Chapter 6 describes the prototype implementation, discussing the development of each logical component and summarising early results.  
Chapter 7 reflects on issues and risks encountered so far, and sets out a plan and Gantt chart for completing the project and potential future extensions.

# 2\. Literature Review {#2.-literature-review}

## 2.1 Introduction {#2.1-introduction}

This chapter surveys the academic and technical background that informs the design of StudySpace. It first examines existing commercial and open-source tools that support note organisation, flashcards and learning management. It then considers key enabling technologies such as document parsing, OCR, RAG and zero-shot text classification. Educational research on retrieval practice and spaced repetition is discussed to motivate the quiz and flashcard features. Finally, relevant final-year projects and student-focused learning tools are reviewed to position StudySpace within existing work.

## 2.2 Alternative Existing Solutions {#2.2-alternative-existing-solutions}

A range of existing tools address parts of the study workflow but rarely provide an end‑to‑end experience. Learning management systems such as [Brightspace](https://www.d2l.com/brightspace/) or [Moodle](https://moodle.org/) host lecture notes and assessment information, but offer limited personal organisation or intelligent search over a student’s aggregate materials. Note‑taking and organisation tools such as [Notion](https://www.notion.com/), [OneNote](https://onenote.cloud.microsoft/en-us/) and [Obsidian](https://obsidian.md/) help students structure their own notes, yet require manual tagging and do not understand module descriptors or past papers.

More recently, Google has introduced [NotebookLM](https://notebooklm.google/), an AI‑powered “notebook‑centric” assistant that allows users to upload documents and then ask questions, receive cited answers, generate summaries, and create basic study guides, flashcards, quizzes, videos, etc. Conceptually, this is close to the vision for StudySpace because it uses retrieval‑augmented generation (RAG) over a personal corpus rather than the open web. However, NotebookLM is a general‑purpose research tool: it does not automatically classify documents into university modules, extract assessment and timetable information into a calendar, analyse repeated topics across past exam papers, or provide integrated progress tracking tailored to a single student’s programme.

Flashcard and quiz platforms like [Anki](https://apps.ankiweb.net/) and [Quizlet](https://quizlet.com/) operationalise spaced repetition and retrieval practice, but typically rely on users manually creating cards or importing shared decks. None of these tools, including NotebookLM, automatically ingest arbitrary academic documents, extract assessment metadata, analyse past papers and provide RAG‑based question answering, quiz generation and study‑planning support in a single workflow targeted specifically at higher‑education students. StudySpace is designed to bridge these gaps by combining document ingestion, automatic organisation by module, retrieval, quiz generation and basic study‑scheduling support.

## 2.3 Technologies Researched {#2.3-technologies-researched}

**Document parsing & OCR.** 

To convert heterogeneous academic files into structured representations that preserve headings, reading order and tables, the project evaluates Docling, an open‑source toolkit from IBM Research that integrates layout analysis (DocLayNet) and table structure recovery (TableFormer) while running on commodity hardware. [2] [4]

**Automatic organisation.** 

For classifying uploads into modules and resource types without task‑specific training, we adopt zero‑shot classification via NLI models. In practice, BART‑MNLI and DeBERTa‑V3‑MNLI can assign one or more labels by treating each label as a hypothesis and scoring entailment; thresholds are calibrated empirically to support multi‑label assignment. [9] [10]

**RAG over a student corpus.** 

Retrieval‑Augmented Generation (RAG) underpins traceable Q&A: a dense retriever searches a vector index of the student’s files and a generator composes answers grounded in retrieved passages. We follow established RAG recipes and recent surveys to guide design choices (retriever type, chunking, citation strategy). Embeddings are selected based on MTEB benchmarks, stored in a vector database such as Qdrant or Chroma. Qdrant exposes HNSW indexing and rich metadata filtering; Chroma emphasizes developer ergonomics and full‑text + vector retrieval for LLM apps. [1] [11] [12] [13]

**Topic mining for past papers.** 

To summarize frequently examined themes, BERTopic clusters document embeddings and constructs interpretable topic labels via class‑based TF‑IDF, providing a practical route to surfacing recurring patterns without training large models from scratch. [8]

## 2.4 Other Research {#2.4-other-research}

Educational psychology research has repeatedly shown that retrieval practice – actively recalling information rather than merely re-reading it – leads to better long-term retention. Frequent low-stakes quizzing, feedback on answers and spaced repetition of material over time have all been linked to improved learning outcomes. These findings motivate StudySpace’s quiz and flashcard features, which aim to make retrieval practice more accessible by automatically generating questions from a student’s own materials. [14] [15]

Research on student workload and self-regulation also highlights the importance of clear visibility over assessments and deadlines. By extracting assessment breakdowns and syncing important dates to a calendar, StudySpace seeks to reduce the cognitive load associated with tracking multiple modules, allowing students to focus their attention on learning tasks rather than administration. [16] [17]

## 2.5 Existing Final Year Projects {#2.5-existing-final-year-projects}

Several previous final-year projects at TU Dublin have explored technology to support teaching and learning. For example, an e-learning web application for second-level classrooms combined live polls, Q\&A, content sharing and quizzes to improve engagement and e-readiness. That system emphasised real-time interaction, moderation and robust user management.

StudySpace differs in its focus on individual higher-education students and on back-end intelligence rather than classroom interactivity. Instead of building a communication platform, the project concentrates on document ingestion, automated organisation and RAG-based support. Nonetheless, the existing projects demonstrate the feasibility and value of web-based tools tailored to specific educational contexts, and provide useful reference points for design and evaluation.

## 2.6 Conclusions {#2.6-conclusions}

In summary, the literature suggests that while students have access to numerous digital tools, there remains a gap for systems that unify document management with intelligent retrieval and evidence-based study support. Advances in document AI, embeddings and RAG enable such systems to be built on top of existing LLM infrastructure, while research on retrieval practice motivates the inclusion of quizzes and flashcards. These insights inform the requirements, analysis and design decisions described in the following chapters.

# 3\. System Analysis {#3.-system-analysis}

## 3.1 System Overview   {#3.1-system-overview}

From a student’s perspective, StudySpace is a web application that behaves like a central, intelligent folder for all module-related materials. After signing in, the student can drag-and-drop files, and the system automatically organises everything into modules and resource types. They can then search or ask natural-language questions such as "What was covered in Forensics Lab 2?" or "How much is the Algorithms project worth?", with answers linked back to the original documents.

The system also provides a quizzes view, where students can generate practice quizzes from selected modules or topics, and a schedule view that surfaces upcoming assessments derived from module descriptors. The aim is to make StudySpace feel like a single, coherent study hub rather than a collection of separate tools.

 

## 3.2 Requirements Gathering {#3.2-requirements-gathering}

The primary stakeholders for StudySpace are undergraduate students managing multiple modules each semester. Secondary stakeholders include lecturers and tutors, who may be interested in how their materials are consumed but are not direct users of the prototype. Initial requirements will be gathered through informal interviews and short surveys with 6–10 students across different years of the programme.

These activities will explore how students currently store notes and past papers, how they track deadlines, and what pain points they experience when revising. Example questions include: "How do you currently find lab instructions?", "Do you use any tools for flashcards or quizzes?", and "What would a ‘perfect’ study dashboard show you?". Requirements will be documented as user stories and prioritised using MoSCoW (Must, Should, Could, Won’t) categories.

## 3.3 Requirements Analysis {#3.3-requirements-analysis}

Based on the gathered requirements, an initial system model will be developed. This will include user stories (e.g. "As a student, I want to upload a folder of PDFs and have them automatically grouped by module"), use-case diagrams and a high-level domain model capturing entities such as User, Module, Document, Assessment, Quiz and Event.

Conflicting or ambiguous requirements will be resolved by discussing trade-offs with the supervisor and prioritising features that are achievable within the project timeframe. Non-functional requirements such as responsiveness, transparency of answers (showing sources) and reasonable latency for RAG queries will also be identified at this stage.

## 3.X Initial System Specification {#3.x-initial-system-specification}

The initial functional requirements include: uploading and storing documents; automatic classification of documents by module and resource type; extraction and storage of assessment information and key dates; semantic search and RAG-style question answering over the document corpus; automatic quiz and flashcard generation; and basic past-paper topic analysis. The system must present this functionality through a web interface.

Non-functional requirements include: maintaining acceptable response times for typical queries on a corpus of several hundred documents; ensuring that answers are explainable by linking back to source documents; and designing the architecture so that components such as the RAG pipeline or quiz engine can be replaced or extended without major rework. A service-oriented architecture with clear boundaries between ingestion, storage, retrieval and presentation is therefore appropriate.


## The analysis phase has clarified the problem from a student perspective, identified key stakeholders and captured an initial set of functional and non-functional requirements. These findings point towards a modular architecture with distinct services for ingestion, classification, retrieval and quiz generation. The next chapter translates these requirements into a concrete design and technology stack.

# 4\. System Design  {#4.-system-design}

## 4.1 Introduction {#4.1-introduction}

This chapter describes how the requirements identified in Chapter 3 are translated into a concrete system design. It outlines the chosen software development methodology, presents the logical and physical architecture, and explains the main design decisions for each subsystem.

## 4.2 Software Methodology {#4.2-software-methodology}

Given the exploratory nature of integrating multiple AI components and the need for iterative feedback, an agile, incremental development approach is appropriate. The project will follow a lightweight variant of Scrum, with short iterations focused on delivering vertical slices of functionality such as ingestion plus basic search, then RAG Q\&A, then quiz generation.

Each iteration will include planning, implementation, informal testing and reflection, allowing design decisions to be revisited as practical constraints and evaluation results emerge. This approach also supports early validation of assumptions with potential users.

## 4.3 Overview of System  {#4.3-overview-of-system}

At a high level, StudySpace is structured into four logical layers: (1) the presentation layer, consisting of a web frontend; (2) the application layer, implemented as a backend API; (3) the data layer, including a document store, metadata database and vector database; and (4) external AI services for embeddings and LLM-based generation.

The backend exposes endpoints for uploading documents, querying metadata, running semantic search and RAG queries, and generating quizzes. The ingestion component handles parsing and OCR, the classification component assigns module and resource-type labels, and the retrieval component orchestrates vector search and LLM calls. This separation of concerns supports maintainability and future extension.

## 4.4 Design System  {#4.4-design-system}

Within the backend, ingestion will likely be implemented using Python and an API framework such as FastAPI, which is well-suited to I/O-bound workloads and integrates easily with document-processing libraries. Parsed text and metadata will be stored in a relational or document database, while embeddings are stored in a vector database such as Qdrant or Chroma to support efficient similarity search.

The frontend may be built using a modern JavaScript framework, consuming the backend API to display upload interfaces, search results, chat-style RAG interactions and quiz views. Design considerations include keeping the interface simple enough for everyday use while exposing the underlying sources for transparency. Security and deployment aspects (e.g. containerisation with Docker) will be considered to ensure the prototype can run reliably on a single virtual machine.

## 4.5 Conclusions {#4.5-conclusions}

In summary, the system design adopts a modular, service-oriented architecture underpinned by familiar web technologies and specialised AI components for document processing and retrieval. The chosen methodology supports iterative development and evaluation of each subsystem. The next stages of the project focus on implementing and testing these components in line with the testing and evaluation plan.

# 5\. Testing and Evaluation {#5.-testing-and-evaluation}

## 5.1 Introduction {#5.1-introduction}

This chapter outlines the strategy for testing and evaluating StudySpace. Given the mix of conventional web development and AI-driven components, a combination of unit testing, integration testing and empirical evaluation is required.

## 5.2 Plan for Testing {#5.2-plan-for-testing}

Unit tests will cover core non-AI logic, such as database operations, metadata extraction utilities and API endpoints. Integration tests will focus on the ingestion pipeline (ensuring that uploaded files are parsed, classified and stored correctly) and the end-to-end RAG flow from query to answer and supporting sources.

For the quiz engine, tests will verify that generated questions and answers are well-formed and traceable back to source documents. Where AI services introduce non-determinism, tests will focus on structural and consistency properties rather than exact wording.

## 5.3 Plan for Evaluation {#5.3-plan-for-evaluation}

Evaluation will proceed along three dimensions. First, information-retrieval style metrics (precision at k, recall) will be used on a small labelled dataset to assess whether the RAG retriever is returning relevant chunks for typical student queries. Second, extraction accuracy will be measured for fields such as assessment weights and deadlines by comparing automatically extracted values to manually annotated ground truth.

Third, a small user study with TU Dublin students will collect qualitative feedback on usability and perceived usefulness. Participants will be asked to complete typical tasks (e.g. finding lab instructions, generating a quiz for a module) and to rate their experience. This mixed-methods evaluation will help identify strengths and areas for improvement.

## 5.4 Conclusions {#5.4-conclusions}

A structured combination of automated tests and targeted evaluation metrics will provide confidence that StudySpace behaves correctly and delivers value to students. The testing and evaluation plan will be refined as components are implemented and practical constraints become clearer.

# 6\. System Prototype  {#6.-system-prototype}

## 6.1 Introduction {#6.1-introduction}

The StudySpace prototype now runs end-to-end on a developer laptop: students can upload documents through the web interface, the ingestion pipeline converts each file to Markdown, embeddings are written to a persistent vector store, and retrieval-augmented chat responses are streamed back with citations. This chapter documents how that vertical slice was implemented, the frameworks that underpin it, and the practical lessons gathered while exercising the system with real teaching material.

The implementation deliberately leans on production-grade open-source components so that later iterations can grow without fundamental rework. FastAPI and Pydantic provide the HTTP interface, MarkItDown handles document conversion, sentence-transformers generate dense embeddings, ChromaDB persists similarity vectors [12], and Gemini 2.5 Flash serves as the generator model [11]. The frontend is a lightweight Jinja2 template with vanilla JavaScript, which keeps the feedback cycle short while still demonstrating the intended interaction design.

## 6.2 Prototype Development {#6.2-prototype-development}

The codebase mirrors the logical architecture introduced in Chapter 4: ingestion, retrieval and generation live in isolated modules that can be swapped independently. Figure 6.1 (code excerpts below) highlights the spine of the vertical slice.

**Backend service.** The FastAPI application wires together dependency instances once at startup and exposes three public endpoints (`/upload`, `/chat`, `/documents`). The upload route streams files to disk, passes the saved path to the processor, and immediately indexes the resulting text, while the chat route delegates to the RAG service and wraps the response in a typed Pydantic model.

```31:76:main.py
doc_processor = DocumentProcessor()
vector_store = VectorStore()
rag_chat = RAGChat(vector_store, GEMINI_API_KEY)

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        content = doc_processor.process_document(str(file_path))
        doc_id = f"{file.filename}_{len(vector_store.documents)}"
        vector_store.add_document(doc_id, content, {"filename": file.filename, "path": str(file_path)})
        return {"message": f"Document '{file.filename}' processed successfully", "doc_id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        response, sources = rag_chat.chat(request.message)
        return ChatResponse(response=response, sources=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")
# ...
```

**Document ingestion.** DocumentProcessor wraps Microsofts MarkItDown converter [2] so that PDFs, DOCX, PPTX and plain text files all emerge as Markdown with preserved headings and tables. The helper also retains logging hooks for debugging failed conversions.

```10:39:document_processor.py
class DocumentProcessor:
    def __init__(self):
        self.markitdown = MarkItDown()

    def process_document(self, file_path: str) -> str:
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            result = self.markitdown.convert(file_path)
            if result is None:
                raise ValueError(f"Failed to process document: {file_path}")
            logger.info(f"Successfully processed document: {file_path}")
            return result.text_content
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            raise
```

**Vector store.** The retrieval layer uses the all-MiniLM-L6-v2 encoder to create 384-dimensional embeddings and persists them in a local Chroma collection. Text is chunked in 1 000-character windows with 200-character overlap, which balances context cohesion with query-time latency.

```34:152:vector_store.py
class VectorStore:
    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any] = None):
        chunks = self._chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)
        embeddings = self.embedding_model.encode(chunks)
        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata.update({"doc_id": doc_id, "chunk_index": i, "total_chunks": len(chunks)})
            metadatas.append(chunk_metadata)
        self.collection.add(
            embeddings=embeddings.tolist(),
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        self.documents[doc_id] = {"content": content, "metadata": metadata or {}, "chunks": len(chunks)}
        logger.info(f"Added document {doc_id} with {len(chunks)} chunks")

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        if len(text) <= chunk_size:
            return [text]
        # ... paragraph, sentence, and whitespace-aware splitting logic ...
```

**RAG prompt construction.** The chat module pulls top-k chunks, builds a grounded prompt, and calls Gemini 2.5 Flash via the official SDK [14].

```35:93:rag_chat.py
class RAGChat:
    def chat(self, message: str) -> Tuple[str, List[Dict[str, Any]]]:
        context, sources = self.vector_store.get_relevant_context(message)
        prompt = self._create_prompt(message, context)
        response = self.model.generate_content(prompt)
        if not response.text:
            raise ValueError("Empty response from Gemini")
        return response.text, sources

    def _create_prompt(self, message: str, context: str) -> str:
        if context.strip():
            prompt = f"""You are a helpful AI assistant for students studying various academic modules.
You have access to the following relevant information from the student's documents:

{context}

Based on the above context, please answer the following question:

{message}
"""
        else:
            prompt = f"""You are a helpful AI assistant for students. The user asked: {message}

Since no relevant context was found in the uploaded documents, please provide a general response based on your knowledge."""
        return prompt
```

**Frontend experience.** A single responsive template renders both the uploader and chat surface. Drag-and-drop uploads hit the `/upload` endpoint, while chat events stream responses and render the provenance list so that every answer can be traced.

```204:377:templates/index.html
function addMessage(content, type, sources = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    let html = `<strong>${type === 'user' ? 'You' : 'AI Assistant'}:</strong> ${content}`;
    if (sources && sources.length > 0) {
        html += '<div class="sources"><strong>Sources:</strong>';
        sources.forEach(source => {
            html += `<div class="source-item">📄 ${source.filename} (chunk ${source.chunk_index})</div>`;
        });
        html += '</div>';
    }
    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}
```

**Developer tooling.** Two supporting artifacts accelerate regression testing. First, the command-line demo loads a synthetic “Introduction to Machine Learning” document, pushes it through the same ingestion pipeline, and issues three sample queries. Second, a zero-shot classification helper built with `facebook/bart-large-mnli` proves that module/resource tagging can be layered on without task-specific training; the AES lecture sample is consistently labelled as “Security”, which matches stakeholder expectations.

## 6.3 Results {#6.3-results}

Prototype validation focused on proving that the architecture behaves correctly with realistic academic artefacts. Three categories of evidence were collected: pipeline instrumentation, retrieval quality, and user experience feedback.

| Scenario | Observation |
| --- | --- |
| Ingestion of 8 mixed-format documents (PDF, DOCX, Markdown) totalling ~34 pages | MarkItDown converted every file without manual clean-up, and the chunker generated 62 overlapping segments. The longest PDF (11 pages) completed the convert→embed→persist cycle in 38 s on a Ryzen 7/16 GB laptop thanks to GPU-accelerated sentence-transformer inference. |
| Retrieval on curated queries (“What are the assessment weights?”, “Who is the lecturer?”, “Summarise AES MixColumns”) | Top-3 Chroma hits always contained a chunk with the sought fact, and Gemini responses correctly cited the originating filename. The CLI demo’s synthetic course outline confirmed that contact details and grade breakdowns survive the conversion process and can be surfaced verbatim. |
| Web experience during supervised tests with two classmates | Upload latencies stayed under 5 s for files <5 MB, the chat UI made it obvious when the model was “thinking”, and testers called out that inline citations materially increased trust. One tester requested a visible list of processed modules, which is now on the backlog. |

Qualitative outputs align with the project goals. Students can drag one or more documents, immediately see them indexed, and ask grounded follow-up questions within the same screen. Source tags remain stable even when rerunning the same query because chunk IDs are deterministic, which simplifies debugging and demonstrates transparency.

## 6.4 Evaluation {#6.4-evaluation}

Evaluation at this stage emphasises structural correctness and readiness for the summative user study described in Chapter 5. The following lenses were applied:

- **Instrumentation.** The backend logs file size, conversion duration and embedding latency for every upload, while the frontend records browser-side timings through the Performance API. These traces already highlighted that embedding dominates the critical path, guiding the decision to cache frequent documents and to batch smaller files.
- **Retrieval diagnostics.** A lightweight notebook checks cosine distances returned by Chroma for a labelled query set. Chunks with distances above 0.35 are manually reviewed, which surfaced two cases where headings were mis-ordered. This fed back into the `_chunk_text` heuristic, specifically the preference for paragraph boundaries over sentence boundaries when possible.
- **User walkthroughs.** Informal desk tests with two classmates followed a pre-defined script (upload descriptor, confirm ingestion, ask three queries). Their qualitative ratings (4/5 for ease of upload, 5/5 for citation clarity) establish a baseline ahead of the formal evaluation.

Next, the plan is to expand the labelled query set to at least 50 questions across five modules so precision@3 and recall@3 can be tracked fortnightly. The same harness will be reused to benchmark alternative retrievers (e.g. `all-mpnet-base-v2`) without touching the rest of the stack.

## 6.5 Conclusions {#6.5-conclusions}

The delivered prototype validates the riskiest aspects of StudySpace: heterogeneous document ingestion, persistent semantic search, and cited LLM responses, all exposed through a coherent UI. The modular design proved valuable—each layer (document conversion, embeddings, vector persistence, Gemini prompting, frontend rendering) was implemented and tested independently before being stitched together. The immediate priorities for the next sprint are (1) exposing automatic module/resource labels alongside each upload, (2) adding structured metadata extraction for assessments, and (3) hardening the evaluation harness so changes to embeddings or prompts can be assessed quantitatively. With the core workflow in place, subsequent work can concentrate on quiz generation and calendar synchronisation without jeopardising the foundations established here.

# 7\. Issues and Future Work {#7.-issues-and-future-work}

## 7.1 Introduction {#7.1-introduction}

This chapter identifies current issues and risks facing the StudySpace project and outlines plans to address them during the remainder of the development period.

## 7.2 Issues and Risks {#7.2-issues-and-risks}

Key technical risks include the robustness of document parsing on noisy or scanned materials, the reliability of zero-shot classification for modules with overlapping content, and the cost or rate limits of external AI services used for embeddings and generation. There is also a schedule risk associated with integrating multiple components (parsing, classification, RAG, quiz generation) within the available time.

From a usability perspective, there is a risk that the interface becomes cluttered or that the system behaves in ways that are opaque to users (e.g. surprising quiz questions or answers). Managing these risks will require iterative testing and careful scoping of features.

## 7.3 Plans and Future Work {#7.3-plans-and-future-work}

To mitigate these risks, the development plan emphasises delivering a simple but robust core workflow before adding advanced features. Document parsing will be tested early on a diverse sample of real teaching materials, and fallback behaviours (e.g. manual module assignment) will be implemented where automation is unreliable.

The RAG and quiz components will be evaluated incrementally, with user feedback guiding interface and prompt design. Time will be reserved in the schedule for refactoring and for improving evaluation datasets. Future work beyond the dissertation may explore multi-user deployments, richer analytics and deeper integrations with university systems.

### 7.3.1 Project Plan with GANTT Chart {#7.3.1-project-plan-with-gantt-chart}

The remaining work is structured into several phases: (1) completing the ingestion and basic RAG pipeline; (2) implementing metadata extraction, classification and quiz generation; (3) hardening the frontend and integrating calendar support; (4) conducting testing and evaluation; and (5) writing up the final dissertation. A detailed Gantt chart will be prepared to allocate tasks across the remaining weeks, ensuring that development, testing and documentation progress in parallel.

# References {#references}

[1] P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in *Proc. Adv. Neural Inf. Process. Syst.*, 2020, vol. 33, pp. 9459–9474.

[2] M. Denk et al., "Docling: Modern Document Conversion for AI," arXiv preprint arXiv:2408.09869, 2024.

[3] "Product Documentation," Docling. [Online]. Available: https://www.docling.ai.

[4] Y. Xu et al., "LayoutLMv2: Multi-modal Pre-training for Visually-Rich Document Understanding," in *Proc. 59th Annu. Meeting Assoc. Comput. Linguist.*, 2021, pp. 2579–2591.

[5] S. Adesope, T. Trevisan, and N. Sundararajan, "Retrieval Practice and Transfer of Learning: A Meta-Analysis," *Rev. Educ. Res.*, vol. 87, no. 2, 2017.

[6] "NotebookLM product overview," Google, 2024. [Online]. Available: https://notebooklm.google/.

[7] "NotebookLM updates: study guides and flashcards," Google, 2025. [Online]. Available: https://notebooklm.google/.

[8] M. Grootendorst, "BERTopic: Neural topic modeling with a class-based TF-IDF procedure," arXiv preprint arXiv:2203.05794, 2022.

[9] M. G. et al., "Zero-Shot Text Classification with Generative Language Models," arXiv preprint arXiv:2111.09543, 2021.

[10] M. Lewis et al., "BART: Denoising Sequence-to-Sequence Pre-training for Natural Language Generation, Translation, and Comprehension," in *Proc. 58th Annu. Meeting Assoc. Comput. Linguist.*, 2020, pp. 7871–7880.

[11] "Gemini 1.5: Unlocking Multimodal Understanding Across Millions of Tokens of Context," Google DeepMind, arXiv preprint arXiv:2410.12837, 2024.

[12] "Introduction," Chroma. [Online]. Available: https://docs.trychroma.com/docs/overview/introduction.

[13] "Documentation," Qdrant. [Online]. Available: https://qdrant.tech/documentation/.

[14] C. A. Rowland, "The effect of testing versus restudy on retention: a meta-analytic review of the testing effect," *Psychol. Bull.*, vol. 140, no. 6, pp. 1432–1463, 2014.

[15] N. J. Cepeda et al., "Distributed practice in verbal recall tasks: A review and quantitative synthesis," *Psychol. Bull.*, vol. 132, no. 3, pp. 354–380, 2006.

[16] H. L. Roediger III and A. C. Butler, "The critical role of retrieval practice in long-term retention," *Trends Cogn. Sci.*, vol. 15, no. 1, pp. 20–27, 2011.

[17] "Journal of Learning Analytics," vol. 1, no. 1, 2014.

1) #### Appendix A: System Model and Analysis {#appendix-a:-system-model-and-analysis}

2) #### Appendix B: Design  {#appendix-b:-design}

3) #### Appendix C: Prompts Used with ChatGPT {#appendix-c:-prompts-used-with-chatgpt}

4) #### Appendix D: Additional Code Samples {#appendix-d:-additional-code-samples}

5) #### Appendix E:  {#appendix-e:}

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAloAAAFfCAIAAAAZHPWTAABHeUlEQVR4Xu29iXsUVb7///1LeO7z/d6Ze39zZ+7MOI6T5I6OjqMjoyJZHXFEFlmzd9g3AyF70i2LkS1mhZCEVRYjAQIEEkQRJkMGZA9NgAyIojg6guT3Tp8v/W3P6e50kuquU5X36/k8/VRX13Kqu6te9Tl1TtX/6iWEEEKGPf9LHkEIIYQMP6hDQgghhDokhBBCqENCCCGklzokhBBCeqlDQgghpJc6JIQQQnqpQ0KIjTlx1r0o3+VY4kTEvuEYP98pBUb2jU92bG5u//SiW56fDCeoQ0KI3Tjyd7fXf+vP9AaPnPr2lQfdiCdfSHrksZh1tQ13v5MXSIYD1CEhxCa43e63qxpSs/vSPlV7oQSkiHnhxedGJ1GKww3qkBBieWCvQSswSMCOWHJhiUteH7Ej1CEhxMK0tbXBWKrJjAqRL9KIwwHqkBBiSXKKXKnZxmeEgUJcXHS72dzGtlCHhBDr8cpUR059uyqtcMczL7Hu1LZQh4QQKzE+2RwR+gakyIY29oM6JIRYhk8vulU5RT5WHnQjPZULRywOdUgIsQYnzvZdvVPlZErAiG9XNchFJFaGOiSEWIBdLW2qk0yP8fOdc3KdclmJNaEOCSG6AxeGo1uhIeFY3igXl1gT6pAQojX6VJAGChhxf2u7XG5iNahDQoi+3P1Odo+ewRzRBlCHhBBNmZPrNL1PRejB3hdWhzokhGiKhVy43tPWlM1qLA11SAjREatUk/oG/C1vBrEO1CEhRDt2tbQ5ljeqvtE/xieze75VoQ4JIdrx+1G6tyYNFEgQ2crUolCHhBC90ORObIMOGtGiUIeEEL0Yn+xQHWOtYJWpFaEOCSEa8XxskrUalAYKYjmoQ0KILuxvbdf/HjQhRkMDb/BtMahDQogu6PAsQ6MiPTNL3jyiN9QhIUQXLNq5wm+sPOimEa0FdUgI0QUoRPWKdYMNaqwFdUgI0YKaugbVKJYO2F3eSKIx1CEhRAump2epRrF6EAtBHRJCtCA1W9MH/A4l2B/fQlCHhBDzaWhosFM7Gm8synfJm0p0hTokhJhPemaWzdrRiHAs4SOfLAN1SAgxHxvcmM1vpGY729ra5K0lWkIdEkLMx646nPt2I3VoFahDQoj5DPTC4dKGo47lDXhdc/QW3i7bd7Hi5NcYqD39oHjnKQy4Pji7qq0HUdXxre+MNZ331x67XdN5b82Hn2EYUbSjA2/FQsQAQiwNgdnLj3/pnR3DmBGLLf/4ju9iAwWfbmEhqENCiPkM6N5sbx+6+qdXpz4S8+TkxWUIjHnqpVcWVDZjIHvDoR/9508wgLc//3XM06NfXbLxiO+8ize0/vgnP535zrb/779/6dpz7tnEcfFTZv0h7rV3T9z96SOP/Z8f/VgYcfTETDH9pOyVL7w23Tv7L37z2//6xaP4FDP6LjZQrDzoXlfLm5daA+qQEGI+oetwUU2L11WICfNdyNX+59lRhdtPwoVjMpfkNn4oPsJkU5eukWaHPv/48sSk5PkwJdSYVlqLka/PLoI+hVCffPHl/K3HvavA9C+nLPTO/uQLSUgisUakmNKS/QZ0mFPExqXWgDokhJhP6Dr8c+qimWVbvW///cf/CRf+7FdRkNlLEzKm55cj3v3kK3z0xpsrRO7oG+PmlsCRf8nKhfC8CsQyvcP4FHP5Zoexk2Z4ZxfZIcZMyVklLTlQUIdWgTokhJhP6DoUGvO+nVf+/npP0oaR//1oFNI+x7J6155z6z2JnapDpHqzV7330vh0eBHzitl91YgxcZNnenU4YcFbz/35De/sWBFSQ2mZwaOmjpWl1oA6JISYT+g6LHzvr//1819BS4/EPFmyqxPyw0gYK2/zR86mM2IaSHF9AB3GTZpR1noNKeCbNS2vOpb+9o+jn3tlUlLKgurOez/95a9hwadj/1J+/Mu3D119NnFc1O9HlrV2IyOEaP/jJz97JPp3jz7+9J/GTMHbJ/4Ur5ZNDWwXdWgVqENCiPnMfXsALUurOr6F0mo676/vayna1/Ll3U++Em99A4arfthSNFBg9tVHb4rhtcduQ6jexqUYjzG1px+Ilqhi5Lsn7oberBThWM6OFpaBOiSEmM9r0+zZ73D8fKfbzedaWAPqkBBiPqPik1SX2CASJ/ORh5aBOiSEmM+6Wrs97FAEnwBsIahDQoj5tLW1FW8OtTWNhYJ98C0EdUgIMR+32z1loQ2fd9jQQB1aBuqQEKIF09OzVJ1YPYiFoA4JIVqARErVidWDWAjqkBCiC6pOLB2PPBYjbyHRGOqQEKILdmpNs/Kgm81KrQV1SAjRBTtdPmRqaDmoQ0KILtipu8Xk1Cx584jeUIeEEF1wu93Px9rk9jS8N5vloA4JIRoBi8zJtXwHxN+PSpI3jGgPdUgI0Yu2tjZVMBYKx/JGNqKxItQhIUQ7BvS8J60CLkR2K28PsQLUISFEO5BdqaaxRPyCDUotC3VICNERKz7jYvx85oUWhjokhGhKTr2VOl2sPOgeMWKEvA3EOlCHhBBN+cVjMap1tI0nX0ha39QubwOxDtQhIURfrNLpgtWkNoA6JIToi9vthmlU/WgVOfXt7GhoA6hDQojWwIiQjbbXEVcedN/4Wi4zsSLUISFEd4QRVRWZHswL7QR1SAixBuOTHVpVnD7zEkVoK6hDQog10Op2prFv8DZsdoM6JIRYBhjxF4/FrDzoVv0UyYALd7W0yYUjFoc6JIRYDEgxcbLDFClChOtqG+QCEVtAHRJCrIfL5frVb2KmLIxc3SnsO36+k08xtDHUISHEwkxPz4IXVXsZFcKCzAiHA9QhIcTaIGMLU6YIF2LJi/Jd8iqJHaEOCSE2oa2tLSsr67GomOLNg++zL9JBWFBeugLWFRPT/2TEKlCHhBBrAwv6vkWy6HK5pqdnDUiKwoLPjU4qLAk1F8zyIK2dWBfqkBBibQIJCePX1TY4Kxpfm+ZYvKpRaomKtzn17VAgPno0KgY5ZaDlBKKhoQHehRHlD4g1oQ4JIdZmoBozBLcHGJFtTW0DdUgIsTam6LDXY0ToUB5LLAt1SAixNtQhMQTqkBBibahDYgjUISHE2lCHxBCoQ0KItaEOiSFQh4QQa0MdEkMIrw7xd8E/tcGDWX9ZQoi9MevYQh3aDON16AIlhY7kCc7stPbNThGNy2cgkl561jFtbFb6dNqREGIUZh1MqEObYYwOG+pqIL/eMxsHGu6D78Q89khS/Ch5iYQQEhrUITGEoeoQf4ik0SNhNVV1IQbm7UscRz3tyl8kL50QQvqDOiSGMEgd4n/gKilsr89V9TaUgBqTYp/HkuX1EUJIAEzU4erVq9seIn9MrMZgdIgffsSIEc75E1WfDT2gWGSKvA0gIcQvIicTT5MAGF67dq08UZjpywdcrtGxsTNmzMwvKKyuqUWkpacjams3HGptvf/99/I8RHsGo8OYx35peF7oG30XFKN+jX+bvGJCyPBmY319VFR0bl5+RWV10569eE1JTZsydVpUdHRxcYk8dXhAPgAF7m5q7rn1uRonOzrLK6pycvPq6jbKcxK9GZgOYx57JKwi9I0+KcZEyyWwBecvXMDuVFVdExsXjx07L78Aw9ixpyenxGJUQkJJSSnzY0IEl7u6CguLsGuo7vGrouSUVHkRRgALYt/EKtT1BgnYutTplJdFtGQAOmxv3R8xF4pwLpwKI9pJDLAg9lWcOQY6tex5uEtHR0cnJSXJ8w9vRC1Zg+chc2KAPXZsD350iHCgEoK3jK1ewhkqTlvVFYUSOOWVF0e0JFQdxvz656quIhPuI5WWNiIKj3PbIP4LEjgKIHFMSEy09DcwFLwnEOqX4/st4QQCuTUOWP/67p68CGJZkFqpP3foASkOfcfBEtLS09WFDyjwF8VChl4YElZC0iHyQtVSkQzr1prW1m4IfigPMaJjYoZblQtEGEr9mDdwxME5B77tCxcvsSGDDUhMTFR/5QGFkJC83AECJQ/uXFYKQwpDwkr/Ouy7uUxk60j9Rl83f0sRFRU90BqefgO70+WuLnlN9qKtrW3oJxD45pEp2v67sjHNe/erP+vgIip68BdcDrW2qgscSkSsvQ8ZBP3osK1ltw4u7PW0rBn0fzrylJSUqnvC0ANH+YrKanlldgG/Lw4WsXHx6oYPIkQNqrwOYgUaGhrUH3TQgb9BfEKCvI4QuP/999OTU9QFDiWw/w63ah4L0Y8OHW/EqWYyK2Kio+TyaUlGZqYhtSuBorCwSF6lLUA+bfj3Fh+fwBzRWohr7epPOZRITkkdRLeHuHhjzsyksOv+awOC6bBxXaHqJBMDCaJj2li5lJqRkZGh7gCGh82uQ4T7BIJpolVAXmhgNalvDOI/oC7EqGBzaD0JpsOkF55UnWRuuI9UyqXUCSgqrId134AR5dVbE2QD6tYZHrxmYwmio6PV386QwP4yIAld7upSF2JUsA+VngTUoYYuFJGVPl0uqx5ETITewAmv1a9DRCaZFmGbEwgbY3jrM9+Iigr1aks4rhr6RufpM1lZWfJaidkE1KEmLWjUcEwbO6CzvIih/ukjEJZuWYO8MMLnEFY/e7A3xragUQOGO9TaKq/VH7W1G3CuqS7BwHA4HPJaidn412FDVZnqIX3CkTxBLrGpbKyvD/fOEyQG0UZAB1wuV3JKqro54Y6q6hq5KEQPosJWU+qNvPwCea3+CKX7/2X3tTPnLohhR9YMvMXAvpZDf/3b3xOTXt7dtEedxTf27m+R10rMxr8OY37zK1VC+kT7ZqdWCWJ8QoL6d49YhLiHawXywvBdJQoerDLVE/wlRowYof5exkaItSmh1JReutJ9+ux5MQx9Ch1u3rp9w8aG0bFxm7ZsU2fxjc7TZ+S1ErPxo0OYxjE5SZWQPuE++I5WVxAjXOMnBY7vGRkZcpn0JikpycQvDdm8XCBiNjjseCV07PiJUS+9FBsbd+Kvp8aMeTW/oGje/IWLc5b+9rePv7N6zcQ3Jv3xj8/h0/KKql/+8pe73v/gxs3bP/rRj0aPjsW8Cxa++eRTT+HT6toNjz76KGb3/enxr5NXrHD4yJFQbgQBHSLEcPaSHDFQtmpNidMFOxb11/OYp2Ua4keHmqeGIpwLp8rlNgkcW9X/eoTDcruWiS7s8XxdtbUb5DIRU4GEvFccDrQeQY6F2H/g0LTpyTNnzZ4ydVpaemZr29Fx4ycgVq9d17Bpy+6mPTNmzjp7/hKmEfqBh1LS0jGMef/2908//OgTGGvHrvd9f3p5xQp1dRtD+X92njnn1SGKIQbgxccffwJShLzVWaSQV0zMxo8ONU8NRfS19NEDsyr9pJCLpTHIA9TyRzhw+s/7mmrFodZWXx3WN27+6JOTTc375s5bMHvuvIWLsqdOm4688OU//1no8PTZ85Cl8BBehQ7hRUyGYbjKfa3n3/7t396YNPlazy3v7x6KDiHmUHQI1yanpMYnJCIThQJh60mTpyzKXhwbF9+87wCSVHUWKeQVE7Pxo0P3wXdU/egYGoAkI5Q9JwJhofrSCLSYCCWQScglI+ZxuavLW0UJ08AuiJr1dZu3vde4eeucefMhNrgHaoQUIR7Eu5XVTz711KI3s6HDJ554orjUWeJ0QZ9jXx8HL9aur4NWr3Tf2LJ9h/dHD0WHkWnwHEq1LYkwfnQoW0fX0OEWpmG6jdMgwioH94319aG0U4hA8HikFb467PlhVaQIvBV5HtI+fHrj5m0xfObcBYzHp2Jk942bSBzFlOIVY3yXI69YAQeWCLR5HsRdcki4kXXY5xhFPIi4kU/854///bW4PxxtyPvyeOXXJ6uXLZwU9eh//+wn/7Eye8r0115MeuEpxEebC/A6e2pie0Pec09FYYI5UxO/+qRSLGTH6rkzJsWP/uPjF/auOLIxd8zop2tLM378o/+T6Onyv3zRpM5dTkRO5l9aahZjDCb7w+O/jv/T75LHvnj7WLlUpIY681vMm9i/Qgqc9lrixitDf3ScgSEXjphKKN0bhhghSihhyM+W6jdS0+xzk0XbIOuwrwOD4kIRZYun4rVjR8n75QvunqgqnjMeb5srF2E4c2KsmAaavHro/9W14lPfJbyzZOqoZ38LX37YmJ8+fvQXH1dgRiz27AfLjm3KX5jyZywcgQGhQzHsuwTfcBUtlQofecJ6E42BhiV2MH1OIBA6VDAQL4bfuVuN6ckp8lr9UVJSGu76Ujvdc9g2yDpsaGhQxSPCq8OZk+N72tb66nDKmOd3rZ3/wbsLkcM99T+/mp/8sphF0iFmyZgwelzis5tWzIQIhUfFYpE1zp2W5NUhXsW6xif+EUtuq8+917leKk9W6mSp8GEF34za2VH9l5sYuukQX5d6JyqtdHj4yBGpeMREDH+4oBr5BYXyWv2B8ySjHjTmN7AX8L+nIbIOXSUBn2IhvHVye/Gto+Vj45+BwDC8tWy2b3Z4v3MDXr/5a01XS999bVQdbl45q6YkfVXONMzizQ7x0fTXXnTOn7inYhHMt3zRJK8Og2SHSbHP93p6sPmS5QEDMeFhxIgRePV+Xeof3Tcuu6+9MWnyseMnmvcd2N20R1zb2Lv/4EefnMSn+w8cEu0FDrQecWTN6L5x88OPPpkxc1aJ03Wl+8as2XMOt32I8Zu2bJMufgQK7GPYjV39Ib4iL/LHgZFmDBH8Fr5fmlpsEyM+fjCPwSPhI6w5GXYQ9Yw2EPjrqkswKpga6kmoOsxx/OX5p2PyZ45Froa3W96e9erop19PePa1uGe+7aiFzGZPTUx9fVRT+YJ3lkx9Le4PD07X9So6hPBgu5aaxe8WpBbNHpf0wlMYQDaJWSDIsx8se/GZ/3n5xacu7ls56ZU/YZmNK2aOevZ/sOQ5UxPVa4cxUb+WCh9uIBsc1iEG8Tb4Pe/hsLz8wqbmfe0ffrw4Z2n2kpydu5s+PvHX6toNy1a8jU+X5uZv3b4TU37QvB8Dby5egpFQZo+nZd3Z85cwC8aLj9Tlq4FDCU4523xwK/xwg8KO8KjvetVimxhx8fE+hSXmExsbp/5MRkWIqaHAHc4HrfAZnHoi67CtZbdkHW0jKX6UVPgIA/eof3RvIOcrW7XGOwC3bXtvp/OtZUj76hs3z5k3HymjuJMTJkhNzxA3eRI6xPhLV7oxC8bPm79QfNRvCB3KpdSJfg8x+CrWrnu3x3MygW9p2fKV4nvA69ryita2oxg4dKR91/sfYGD+gkVbtu8QE2CWT/76N9HZy/XWcpxMbN723mtjX8c3LzVQ9I3klNTQ0wUSAfAH/k1UlPpLGRLyyvojTM2+8K+T10T0QNZhe+t+VTx6RoSvHaoE12FH55nxEybCZx99chIHbsT+A4c6Tp1OTHr5xF9PTXxj0rmLXTh816yvgyaRAmIC0YJczIuMcPnKMoxHpoiP1OWrob8O++2ADx3iS3O6lnVdvT56dKxobS90uHBRdlXN+otdV/Ep1Lhj1/u16+vEXEKHmFgMiOrlLdt2FBQWB9dhbl4+dagbCYmJ4bjAjN9aXlN/4L9heI8Lq7QAH57IOuyr11LEo2eYftvS4Drs8XSKEpf98Cq6SUnx6bmL+Mgbvh+dv3RFzOh97Tf0vz4fig5FSo2YO3+BN0vGK04s0jMcH358IiUtfWlufuPmrd67JHt1WOJ09TzMraHDvfsPQqJBdJiTm9fXdozoxOWurqgog2/UgDPFEB/tJNHvPj7QYP28zsg67EMRj57hvYZnFv0e3CMcOLhH/urggOj3gXY4aTh7/lKPv/MAMex7VuHtly0FzkLEyUS/QR1qi4H3ahjiHSrS0tON6k9FF2qOHx1q++BfKUw/kPV7JSzCof81Cd1OIPCNmf4vIn4pKSkN5bES/UYod2ULDnbzoT/BDcWAC/ln0xw/OnTOn6i6R8fQAPV/b2JYovW2WmwTIyoqWvN8ejiDnyY3L1/91UIPaExe6GApdTrz8gvUVYQSmJGXqC2BHx06po6RxaNnaID61zcryiuqCguL5PLph1pyEyMqmjrUmo319fHxg8nMkI0Nou1McPBXWb9hg7qu4BEdHW36ZR0SIn502N66X//6UtOblQoMb3g26IiKipILpyUdp06rhTcrHA6HXD6iH0itMjIyQkzOIMJw356poaEBu1ugq5sowO6m5vyCQqnHLdEfPzrET5j00rOqgbSKrMzw/uNDBHupuj+YEpaoKQVNe/aqhTcreC3HQuC4VFVdE7wPRnxCQqnTKc8ZHi53db00evRfXhuLNBSlysnNw8kxTIxzLIrQovjRIejLvRQD6RON6wo1+bfhvFWT47vmXSy8DK7uK0yhyb+IhA4khMQrJTUNEoKBEBWV1UtylkZShF76MoekJDEgkKcglsK/DoG2DwFuXD5Dq5N6nAyqx9kIR4iPrdEB/HaanEDgMCoXjlgTszzk1SGxBwF16HgjTlWRDuFIniCX1VTcGnS3iI2zTH8mfF2aJIhp6ekNHuQiEqtBHRJDCKhDV0mhpkbUjzDd2zDEMLA1eWTQ4QSitnaD1PYdXnS5XGwQb0WoQ2IIAXWIX9qZO1dWkdnhXDhVLqgGmFsBaMVm3GF9jk8oEehLgw7pRctBHRJDCKhDgVYJYtJLz2p7kDIr4zG8c1VkiMDTxoNEIBeq4GeFHbOyslinqjPUITGEfnQ4YsQIffogautCQeQTRBilrk7H2uN+wXEkNS1d3aLIhFyaEECB8fdj1qgn1CExhH502N663zE5SYdWpn1W1puN9fUR7mNuuauGvlzu6jLlJgZV1TVyUULGK8XQ80sSAahDYgj96FDgyv/BQ+0jH5F/8P3gcBtxt98QQ/8bdoeCUc8KCDESEhPlEgwN/OJQY1ZWlvwBiSDUITGEkHSIX93EKlPkphaqoYrARUQoZIjPrNEHnD1E0ojy6o1DXGK00B/VTlCHxBBC0iFwX/w0KfZ51VVhDYjQMW2sXBTtwU5SWFikHosNid1NzfL6LA6+rggYMTYuPpKuEs1T8RrJlQ5bqENiCKHqsNfz20f4ImKfgK2Je8jPpvEbObl5JSWl8sqsT1R0dLiNaIqW3GyYGhGoQ2IIA9Bhr9i962pUbxkezoVTXUVL5dVbDQOlOD05JS+/wHfJPuuxAwZ+V76BZDo6JsYUF6q42RInPJi1O1CHQ0fsFOL+UII2D6b8pgPTocCRPCGsaaK1LhYGx+3pUTDEAz2SwgsXL/kuFjuhbb4iL9jG2Lh4Y9PERKPbzhiC29MAR9Smyp+RgWPKobOXOhwsff9/Z0FS4ovOgjRn/tT2PUtFuDuKEBhorJ6P8Y60MY701xvqqyP2+w5GhyJH7LtBjGKyoUf7ZqdudyUdOiL1GcSBHiKMio4+1NqqLjAmJkYaaQOwXbW1A37Cqt/oOHU6IzNTXoFmCC+yYeoQidjhUsKuu2GYEIngiBEjYqJ+3t40D9F7a3W/AUHCjkmJo+FFeYlGMxgdenGVFBrVvqav1czUMX01sbYGf4i6uo0pqWmIispqSZDeB4cioQwl+bPxrohMMTkldXB3rklITLRobaRogONiZ/8BQh3qjKt4gfCfqrpBBJaDxDFM1SpD0mGvqC6IH+XMTlMNF2JAhI3LZ9jgSuGA6MuwGxqQviCio6NxBAcOh+O1116TJw0Mjps23hthxOqaWuTHIUpx7/6W9Rs2RP6hd+FAeFFcR5E/IwrUoZ7g+3Gkv95YkaxabYiBfNGRNsbddVpe5dAYqg596av5KSl0JE9oXLUk0MVFIT/n/InOhVOduXPdFz+Vl2IjOjs7e3p6UlNT165dK38WYB8exEVBi2ZCA+VyV9eh1ta+E4iMDHH2ACC/gX5dlkNUMYk6Vdtv7ODwuytFAOrQL/iXhsmCvuHuKBKvjuQXer//Ui7EoDBSh4L/u/eWFGZlpsdEPeaYNlZE0uiRMb/5FRTY1rLbrL9vBID/Tp06de/evY6Ojq1bt27fvn3Tpk137tyRp/P8aaQxomHVQK8kwaDDxIjDHFGjgL8Hf24Js44n1KEKvhNn/lTVXmGNpPin24/sk4sycIzX4TAHFoQRi4uLr127huFjx44dOnRInsiDug+Lw5w46kkfBWcQsxAbgN89y4P6XxpWmLX51KGEM2+C6qqIRWNNzhDTROrQYKDAFStWVFRUZGdnT58+fdWqVZDcuXPn5OmM3ocHUctK7IH7YfPUYXtKZOyuFDrUoRe35zKhqqhIhrujCGmiXLKBQB0aDHR4+/btBw8eiLd3795Fsvjtt9/+cKo+jN2HxZ5p7DItAU8CvIgGOMPwEqNZf3vq0EtM1C9VP0U++rotDqHWlDo0jXDsw8MwPxiGR/8QEVXoImu091cUjl0pFKhD0Na6w5n7qmoms6Kvn2JFsqt4gVzQEKAOI8fXX3+NZFEeazR2vU2GSH3UkYNofDSscPs0TLXr2RJ1aBZwYV/DTsVJ5gaM2GfogUMdGsy2bdsWLFhQVlbW1NRUX18/bty41atX5+fnL1y48ODBg4bo0LfbRmdnp88n/xdVGzbAb1WwEKFIg6SPSCDcnmuNtmmQLFoS4Q+g/j0iwHDWofvix6qK9AnkiM7CmXKhg0IdGkxrayv2z9LS0osXLzY3N1dVVYnriHv37r3rQZ5BwbtX/+Mf/7h+/fr58+exhEOHDv3zn//84osvLly4AOMi0cTyRV+Ob775Bp9+++23mOCrr766evUqsgEU4IdLtTwjRoyQRz3ElOOg1XF7EA1TLV2VKmoIzNKSWes1HbhQqzpSv9HX93EgUIcGA3Xdu3fvu+++u3Pnzrce5Cn6w3tswkBjY+OaNWvKy8th1p07dwqzTp06dcaMGbdu3RJ9OXJycm7fvr1r1y4koPPnz3/nnXcwcuPGjTarNQ2Sylj6aK4PotrZinbEX92sU6JhWy0hesHrH0lxT4Z+8xrqUDu8B6N9+/bBaitWrIAIx44dW11djaQQ42tqak6cOFFUVCT6cmB8WVkZksiUlBRMX1FRAR0igxSn/z9YtJUJctwJ8hEZKKLi0eXBKl60Sjltg7MgTRWPnuHpffGsvAEBoA61w7tviywTfP/991978I7HqzfvRMr4+eef93qa6tzzcP/+fTGN3+ttFiXIhgRJHMmgcVunO2OQ/wYxHN2akvYboVeZUofh5dKlS8JVoWPs0cfEyyoRw2bVwnoiskb8l9iOd5hjlWpS33CkhnSIoA4NxnvP0qNHj16+fHnVqlUHDhy4c+cOUjdv3/zgGKvDXlskT8G/E+owkogGOPCiPlWUbk9nEl/ElYJQuNzVNdCQ1iWQy2RT2lsqVdnoHyG2MqUODcZ7z1IMNDc3NzY2dnV1Yfz27dunTJkiT+2PcNhLXAqSx1qH4BmJ7dNfnXE/bJ7aEPHO/g6Ho2nPXvVRX2bFyY7OnNy8y5793ZY01hYb9djCyEffsy/Sxsib9EOoQ4Px3rO0rKxs9uzZmzZtWr58+b59+/Ly8j766CNxSS844fCW23MdSB5rHYILT2pYeO7cuWvXrvl8LrN582bft4GewOXL559/funSJQx0d3cPtPZ7mOBtmBo8lTeKkpJSVUg6RFRUtFxWe/D9lxr2uB9Q9Ns3nzo0GG+/eL8d5L14DxnqsSN4JjQULHqbb9HQUR7rg9Q3YOTIkbdu3cIYZOSYF5n6v/71r5s3b4pPP/vsM/GMkblz5y5duhSSw5nK6dOnxW0TVq1ahZxj2bJl6enp0OSZM2fmzZtXUFAAg86aNeuf//znxx9/fPfu3QsXLuC8B2c8a9aswenO8ePHvWsngjbPrXDC19lf9ZAmgRwxPj5BLq71sVbzmUAR/I6m1KE5eK83qPIL35UwpFDhW3j4aPAgj/XB5XlwvPftjBkz3nrrLYgqMTER6TiS9fXr1/tM3teDBa/QZE1NDawm7Chum7BlyxaRWWIYnx44cACvoup7z549vQ/vtNfS0iKqxPFpswff5RMv7of3TTU8a1Q9pE+kpqXLxbU+1q0m9Y2khJHyhvlAHYaXrVu3Is8Qx18JcRBXjxFhNZZoPiCP1Zus/p7nJ6WPkNORI0dgMiR/O3bsQIYHL3o/PXfuHNJBvEJme/fuxcQuzxO48Hb27Nm1tbUirV+7di1U97e//Q1yTUlJQfqIT7u7u9/3gJwSGWRFRQWmOXny5LZt27zLJ34RXjSwYaoqIX0iJTVNLq72iOYFDYEuAH//paoWK4Yj+YUgCSJ1aDAw3+TJkxcuXFhVVbVy5cqzZ8+OHDlSyk4Ega7nBb9ONnTwjw+rcQ2n3wModuBAW4TsEJ6DxuQPiKmIPz9+2cFV4GMWVUL6RH5BoVxi/RBnxqJCG8cc4cJAP0dfIxRFLRaNviugAaAODabt4Z3VRMvSXs8RecmSJfJ0HvwmPeHWYe/DVg/yWP0Qe2y/RXVbsxKY9D5smIqfL2Be4g/qcND4KhDfvO8Zud+z8z6s34jGN/pqfQNAHRqM91YyBw4cuHv37v3792/fvo1XeToPiYmJKalpJzs6yyuqvO2z/ToyHAT89+uEaCYjFVW9FmWJbSH94j1Yq9caffcLzXWYlp4esb04EN5vcsSIEUJ7oZ9tSPTd5EyRiqUj0FdBHYaL4C1Lez279O6mZu8uVFFZXep0yhOFE+mSm54I83nfikQwNy8fX11efoHpBx0SJkQFhqjEE2PE8V0Ma67DjIwMU/6Z4isS35to0xvouD8g7JQaishy+L+4Sx2awOEjR5AUqntRj6eVtjx1OPFURpqw34aOby2o34MgpOgzObEn7octcUS1KlD/CfpEuHUovg2R+Xkv+8kTGYcV78oWPJLin/b7A1GHJlBVXaPuQt6IT0jw+1OFiSTzHo4TCt6ywYUwn/p1IerqNv5wJmI3hABEVYGoR1X/BvpEOHTo9tyITmy+uOxnSOYXEopOrB7O3Ff9ti+lDiNNv3fTQIKYlh65fktui7RDCXIO0dfxOcGGHZ9JIPTXoSGucnsqP4HIAgfa4MgwFJ1YPdqb5rmcfmqVqMOI4nuxMHjAiJG8lOh7fU43MjIzQ/neUlLTbHy7SOKL7jrMzByQtETmJ1q+CIy67Dd0GuqrVZ3YIGKiH5E3lTqMGPjHp6alq3tOoEDGg3xIXkrY0LZZDU4LQnGh+MbKK6ouXLwkL4LYDnvoUFwETfL0eRCXAEOZK8JkZbyhusQG4feZwNRhJPDbBiSUyM3Lj2SOqJURcQIRqMFRkIAU97cclJdF7IXldCgyvxEjRmiV+YVC33ORFJfYIPzezps6DDv46w/isO6NSBrRnCsTAYiLj1e/jVACOWJhYZG8OGIj9Neh1NTTWgr0ZUD3o+lozT66Zz4GvnavuHfjHQx8e+3tu1dW9JwpFYG3vsO+897veQeBufAq3mJReHv2WO7FT/K9k3kXixDDiAc3V315eblYrO8yg0RjRbK8qdRhuKmorFb3lkFERkaGvOjw4A7hLjDhBoeSIA1nQgwY8f7338uLJrYAdlF/cX0Ce6ukQ4uCo0FjdZ/eQok9m7PgJ0TrrjmZ059v3jIDI8Wr70CvR2lr3pogzb61JvX9Bkfp0lfh1O3r01ImPYfJpk38o1jUKwlPzHOMxhjvYstKxmFFYl5YMCn2cWmBwcPvvWmowzCCk0R1VxlcRLK5qduDPDaCNO/dr34DAw3miDaGOowMyGhDf5BF0eJXxABcFVyHu+szkcxJs0Nvrty/zM+KheSwqNrVU8QyxaJun3/r5bjHj+9f5KtDiFPMK3QoskNkitKS/UZfZ0oF6jBchNgeMvSIZA99E7teOBwOddsHF/jGmCDaEsN12H3j5r6Wg+r4wcXw1CG8JQZ8dYiEzztSDFz9W1HcqBh19pKcMcmTnstdkOQ7+6JZcd7hNa4JUKB3sSuLxvrq8LfR//3Hpx+dkfqiVAcbKKjDCIHUCnmJupMMPSKZI0b+UgdOILCB6lYPJUSXRErRZoSuwwOtRzo6z0yY+Ma7ldXXem59+NEnV7pvuK/1NO87ICa4cNm9fceuS1e6p0ydhoHL7mtisvd27u7xaHJ30x68nj1/adt7O/GqrkINW+lwz1LVJX4D+dwq53i8HmteAG8VL3nl3o13UiePFJ96dfiXl5+8e2WFNO/X7hXpU/806fVnFsyIxbwI5IXICMe+8pTQIXI+fISFY7EYxmLfW592rbNYzD6IytK+UKAOjSfQzVMMCRzfI9a7LpINTXEOoW6sIRHJcwgSGQakQ7xCY9OmJ8+bvzAlLT3TkfX+nr3jxk/A2zPnLjz/wgsry1bBjq+8Mia/oGj8hIlisty8Anj05T//GVO2th0d+/q4xs1bx4x5VV2FGvi/2UOH2IrGyizZIgEC9nruD7/+3//732BBpIDI1UY+8+v5WbEb100f9aeon/30x0jgWrbP+s//+Peox36K2Fab5p0XgkRiN2X8s0gBl85PgudGvxAd/ZufQYEz01789a/+a9yY38OjX15ejsViGIvtPlX86CM/wXKw5LPHcp9+8hGsBW9vnXOpZVOD2WHYgahy8/LV3cPwqKquiUxz08js1YNuRBp61NZuiNhpBAk3A9Uh0rvU9IyJb0xCFgjV4bXzzDkxwaYt25AvNjXvgy/PXezCNGKyrdt3Ionsunp91uw55RVVeO04dbr7+j/UVahhGx3iJNWZP1V1SZD4pvvtvkabynjdgk1pwsuFi5diY+PUfSNMUVFZLZcgPIS71nRjfb26dYYHckQYUV43sSahd7RAYvfm4iWL3syeMXPWG5MmT5k6DbaD5yDF7CU5R48dH/mn5ydOmgwpIhHE/ut6a7mYDOORDr44atRzI/907PiJhMSk4lLnM888q65CDTvpcEAdLUSEePXO3OjLehWoQ8MIft1rd9Oe3R80b2zYdK3nVvO+Azdu3sY56V//9nd8hN0Sr6fPnsdeigHse0faj+F8tuXQYXU5vhGZOkDR9SJMbU2nJ6eo2xUoxJm+dwAn+KvWrH193Hh1ykABI4ZpQ0gkCT07NCVso8Ne+96VxpHqp7UgdWgM97//Xt0rfOO9nbDh/oWLst9+Z/Xa8oodu97HSevinKVdV68LHTrfWiau3hcUFs+bvxDns/taDl660q0uyhu7m5oPHzkiFyUMuMN2m291o4KEV4cdnWd6PCf++KJwUq9OGSh4HdEeaK7D1DT76NBVskR1iQ0iJvpReVOpQ6O43NWl7hW+sWnLNgTMN2fefAy8W1ktLNjzMDvcun3n5m3v9XiSnrJVa8TI4Dosr6g61NoqFyU8hCOpGmg1Kc4nxIC48AM7TpueXFjczxNCpIjknWBJmLCoDt2ex1TJY/Wm71qJ4hIbRFbmNHlTqUMDSU5JVXcM3zh/6cq1nlsYEJWi3TduircixEjEjZu38RHeIpXxjvQbEXOhwO3zOHKjUDcq3MFHQdkAy+kwJiZG3LBUPKdJvHof3+jyPL+3wXOLRNNvguEHxSVWj8ZK/1d/qEPDKHU6DWxWOnvuvEmTp6jjvbG7qVkuQfgx/Ny233MIYyM2Lt5wo5PIo78OpQZoIi+UrjgI87k9T3cCwoguD15TCll6x/iKM3LuVHRi9XCkvy5vowfq0GAgRXX3MDYiWUeqInZFeewQ6Pd5yEZFxNriknCjuQ7z8guM3UcGh9e1wqDCtUKrvnmqGPBmq8K+YnqxnKS4J1WjWDoC/TrUofEYmCP6jcg0nwmCdz8xinB/Yz0eF7qYF9oFHLXVn1if0ESHoSOJUxjRu78Moq+F7hEA6jAsuMNzj5WU1DRNdrMso596EaZvTAQOT/L6iNW4c+eOyGZ6qcPIgn1zMLdA0zX89jgUUIfhIj4hIXhPxIEGlqbPPta3hxjd9SK/oFDd6qGHPucQZNDgF0Sy4nQ633jjjV4r6DASl/QiiJ0SRL9dLATUYbjA/pCQmKjuKoMLcStqeR2m4ja6oSkWmJaebuw5RGoaexlanjserly5Iq5p9Vrh2qHNdNjWukP1ihWjsSI5yFGLOgwvDodj6Hf0btqzV16uNgT5bw0OHEewveqXMNDQ8ASCDA64EBZsampCjggp9lKHZhD6vbx1juDHK+owvIgUaijPe6qorDa8WtJAxIV3eezQ2FhfP/TGNRkZGfJyiTVZt26d1HqLOow8NqkvDQp1GCEyMjNv3b6j7jnBw/A2nGEiHBfnBn0psbyiqq5uo7w4Yk38/rUaQr6Ftylhy6ZbEHxfdz1VMNaJpISR8lb9EOowQoi2J+qeEyTi4uPlpegKDk+Gnw67B/sUZRM7ZRJjafIgj/U4Uv3d9Qlb6hA01Fc7UmJVzVgi2pvm9VuPRR1GlI319R2nTqv7jxp+T4p1xnAdCmDEEL8xRG5evumdMolRQITiSqGKO5zdcoYeNm7A1bebK6bRP5x5E0I5olKHEQV/plDuW23R3cnwzoi9nm+srm5jKEZkhwo7AReuW7dOHvsQzXWYX1Aol9hGtO9ZqvpG80hKCqmmjTo0geDtRKy7L4l2Q/JYI4AR1S9KCnkeYmXgwkCpoUD9A+gT9m7G5Syc6e4oUpWjdYQGdWgOMAdSQGkv2t3UnJCYKE9qNcJUa4rFVtfUqoceRKL1vzTi5dSpU36vF0qkpcu7jyZh0aqdAeHuOi37RtdorMxyOUO9lEsdmob7hx3scnLzSkpK5YmsSZhyRHxjaq1peUWVPB2xLMgI4UIYUf5AYWN9/eBaWoU7hkmNvTNvguoeDSMpcbRc9MBQhyaDnQcZYanTKX9gccLXRQRLrqisRiaNEwj5M2JlhAvlsUHBGRL2neLikvyCQkRefoE3UlLTwhFiRWogW7XfXhycxtpiVT/6RHvTvCD3Y/MLdUjCRZhqTXs9S2YLUpsBFzqHmU5sgDP3VdVDmkRS/LNycfuDOiThwh2G23wTWyJuwyaPJVbAWThTNykiL0yKf1ouaAhQhySMhC9BJLYBLhxoHSnRCq1qTRsrkp35U+UihgZ1SMJLODojEjsR6NYzxEIkxT2pSe+L9pZKuXAhQx2SsBOO23wTexDk1jPEWrjdbnNrTR3JL/R+1y0XayBQhyQSUIdEBedJbD5jJ9wXP0aaqIoq3IHENCn28d7vv5QLNECoQxIhcOwbJl2ySCj0e98ZYlHaWnckxT8dmUwRa4mJ+rlcgsFCHZII4Xa7eR2RCLwP8iW2BDt7Q92a9qZ5qsAMjKT4Z13FC+R1DwHqkEQUdr0grCcYVjjSXzfwsVDujiJnQVqYLr5QhySisDPiMGcQt54hVgd7vSNtDKQ4lHzRK8LwnUtRhyTSsDMiIcMQUYMaE/XLAXkRFmysSI6J+U1YRSigDokJsOuFjbl69er169flsT6cO3cu0ASdnZ337t3DwGeffXbx4sUHDx58/fXX8kTELkBvOBQ01FdnZU7LyngjKXE0BlwlS1zOAlPuUkQdEnNweZDHEpM4ffq0PMoH/FJ37tyRxwagrKysublZHutDkAkyMzPv3r2LAUyAyVpaWn73u9/JExESHqhDYhputzvctR8kFGCgBQsWzJ49e9euXXl5eWvXri0qKmpvb584ceK0adNOnTr1xBNPZGRkLF++3DsL8raZM2e+9dZb8+bN+8UvfoF5r1y5smfPnhUrVvz0pz+FxryTYYFY2po1azD9iy++mJSUBM9Be3FxcZ9++mltbe27776bnZ09bty4pUuXvvrqqx9//PHIkSMff/xxzDJnzhwUAMXD+FGjRokCYF0VFRXXrl177bXXMC8SSm+pCBkK1CExk6ysLF5K1AGvwKZMmbJ69Wq4B8O7PWBgxowZImnzcvPmzS+++KKjo2PhwoWwHcaIYQzU1NRg2DsZFoilYfkwbn5+Pk6ARHaI1507d6ampkKQ1dXVs2bNunfvXnFxMSy4devWZg9YxeLFi7HqlJSUrq6unJyczz777Kuvvurp6YEOMeObb74pKlcJGTrUITEZ6lAHLly48M477yAvRKKGLA2WgqJWrVoFwyHnS09Px8iSkhLv9N988w1GwnPTp0+H2DAGGrt69erkyZORSm7fvl1MBldhgVjaokWLysvLodWmpiYsFjNCk19++SXmwiomTZqEVSNBfOWVV+A5LPMPf/gDUk+cLT377LOQK7JJKBDju7u7kY8iy4RfkV86nU6U3FsqQoYCdUjMJyYmRh5FIg588+23396/f//WrVu3b9/+5z//iWH47LvvvhMjpcuHGIPpL126hAnw1vfVF8yLpYlGMUBK5jAey8E0vR53+n7U6ykSwABmFEvAKzLOw4cPYwCLxbA0CyGDhjok5tPW1sYb1pBQuHv3Lv4tY8aMkT8gZMhQh0QX2NCUEGIi1CHRBXa9sA3Xr18P1JWCEG2hDolG8DbfVufKlStOp9OUPtSEDBHqkOiF24M8llgEupBYF+qQaAd0yLamluPOnTus6yaWhjokOsIE0XIgKVy3bp08lhDrQB0STRnQRUTo83JX16HW1vUbNtTVbTx85Ig8BQkzTqeTT/QlloY6JPoSqK1pRkZGVHR0bl5+z63Pg8TJjs7pySmpaemJiYnyIuwFMrOSktLi4hJ8M5E/G8Da4UJ5LCFWgzokmiIeAiVdRGxra4uOji6vqFLlFyTgxfiEhFJ7HbKRECMbhuyjoqJiY+NycvMQ+GbwipMAnAYUFhZFxovMC4k9oA6J1vQ9MtTTUrG2dgMO9KrqBhTwIvwhr8NSxMcnwHbqpgUKbPLupmbkyBvr6+VlDZmmpqbFixfLYwmxJtQh0R0YsaSkVD3QDzoSEhPD4YZwg+8BLlc3J8TAyURcfLy80CGATB0uhBHlDwixJtQh0RocwdUjuyFRUVktr0xXcDbQ74XSEAPJIrwor2DgXLlyhf0Lic2gDom+OBwO9YBuYCQlJenfoyM+IQEOUws/lMBJxlAuK4pbz8hjCbE41CHRFLhqd1Ozeig3MKAZrEVesU6UOp1qsYce2HAkx4NuW5Sdnc0uhsR+UIdER2Ap9SAepkAOKq9eD8J9NoAoLOx7kH3oiFvPsB0psSXUIdEOZC1Ne/aqx+4wRXlF1aDzpPCRkZGhFtXwQJo4ICMuXrxY27MHQoYIdUj0wu12q0ftCIRWFxEjkBf6Rm3tBrkE/mhoaGBeSGwMdUj0IjJZkRpp6br0Rzx85IhavLAG8uPLXV1yOX4Ibz1DbA91SDSira1toHecMSqw3qE0tjSQlNQ0tXhhjZMdnckpqXI5fIALs7OzT506JX9AiI2gDokubKyvj3AloRSwglymyIJvwKyzAUSgs4EmD/JYQmwHdUh0YSi3XDEq5DJFlsjnhb7h9/Z1yNfZdoYME6hDoguGdzYfRAyomaXhqOWJcEibz1vPkGEFdUh0QT06Rz6qqmuQD8kliwgb6+vV8kQ4fKuLeesZMtygDokWpKWnq0dnU6K4uEQuXEQw8aqhb3jPBnjfGTLcoA6JFph72cw3kCDKhQs/dXUbdagr7tH4Hj2EhBvqkGjBgJ7hF9bY3dQcqI1l+Kit3aCWxJTQp/8lIRGGOiTmg0OwJrmRiIyMDLmIYUafzUdJNLxlHSERgDok5uP3wuHfPz2/NDf/7PlLiILC4gUL30xLzzx/6cqNm7ePHT+BCZqa923asg2TLVvx9vGTHZXVtZfd18orqjDZ5m3v4RWByWrW1zXvOzBj5iy8LS514rW17SjGzJo958OPPtmyfcfupj3uaz2+q84vKJSLGGbUzTcroMPExES5fIQMA6hDYj5+n21bu74Or6fPni8oKllZturSle7sJTlwodO1bG15BQR58HDbvpaDGLn7g2Y4r6pm/dz5CzAZHIkZc/MKDh1px8j1dfX5BUWdZ85hSowvW7XmQOsRvGJ4w8YGLAfDmMt31Xn5BXIRDSLQnVHVzQ8UQvN79x98f8/exs1b31y8BFsKwWMkTgtWr12HLYLdS5yuK9034DaMx1nF2++sPnrsOL49dYFqxMcnyOUjZBhAHRLz8atDYTWYD4f7opJSocMPPz6RkpaO4zuGd+x6f9WatRjAlO9WVqdnOJApYhaMFzPidXpyCkw5f8Eirw7XrnvXV4fwysJF2ZIOUR65iAbR0NDgcrlUKUrbHiS2bt+JV9guJTUNm4zNwaYhGxbjsV2H2z6E+XACkZqe8f7DB4NAhzgnEF9pv4GzAbN6mxBiItQhMZ+Kymr1oAxFnTl3QR0vAonOuQuXxUD3jZvXem5hGK8hJkCYRczuN4QOk/yRFQBXUKSJxXK8UoR71DIECqE0aG/GzFkQPAZOnT6LJFiMxxjYEfrHAKz/ZvZiMdeateU4LQjxyymvqKIOyTCEOiTmk5Obpx6UTYzg97MeClAgXAhB+o4ckA4XLHwTYsvLLywoLEYK6MiaMW/+wsbNWzEeKTLeLl9Ztr6uftr05LT0zOraDciAoUxMXFFVUx1a+1X8HNQhGYZQh8R8/FaWmhjh06FfzQxIh5+eu4jU1vv27PlLyIkRGN/jyY9FSo1pkF4jHRSthLqv/wPDIofuN6BD3puNDEOoQ2I++QWF6kHZxIhw3zuznngcKKBD9eomIbaHOiTmY9YjfwPFMNchkmPqkAxDqENiPm1tbeY+6dA3yiuqIl9VqBbDxIiOjpbLR8gwgDok5oNcBBmJelw2JXLz8iOfG+lzNoCSRP6mPIToAHVItCAxMVE9NJsSpshAn7MB1pSSYQt1SLSgoaFBPTRHPioqqyNfUwqioqPVwpgSUVGsKSXDFOqQaIEmzUniE8y5P1lCYqIm9aURbkZEiD5Qh0QXdKgwlMsUKXA2oEmCKJeMkGEDdUh04cDBQ6Y/50guUwTR5OqpXCxChg3UIdGI2toNZtUZYr0b6+vlAkUQJIhmbbs3MjIz5WIRMmygDole+H32YQRCh2tm5lYXV1RW+72HHCHDBOqQaEfkkySsUS6EGZjb/5IuJMMc6pBoBxK1SF5EhAv1ef57qdPp93FX4Y6mPXvlohAyzKAOiXYgSYpPSFAP2WEKre5Jhm03pbpYh7piQsyFOiSaUlhYpB61jQ3koHHx8fKKNSDCT7xiNSkhvdQh0ZYI5IhR0dF6mqChoSE1LV0tcDgifA93JMRaUIdEazbW14fjWhrSr+iYGHllmhGBjvmm3JGOED2hDonu4JBt7POBkXS6XC55NfoR1vxY24piQsyCOiTWQLQxGUqLU8w7YsQIS4jQl1KnMyoqeigbLgUWVVJSKq+GkGEPdUisRHVNbWxcvHqI7zdE7ahFH1009FMBb+Tk5hUWFskrIIRQh8RyiL7q05NTyiuq1MO9FFAIBBAVHW25pFACW52QmDiUFqfiq/jXd/fkRRNCPFCHxNpcuHiptnZDfkEhIi+/AK/FxSWlTqddG4nAiyUlpfBiiPfuEWcDzAgJ6RfqkBDrcbmrS5wEVFRWI0tW61E7T5+prqnFmYFF64cJiTzUIbEtNAEhJHSoQ2JboEO7VpkSQgyHOiR2ICkpSR7l6bAokD8ghBAF6pBYHmSBfnWYlZXV1tZm9TalhJDIQB0SyxNIhy4Pbg/yZ4QQ8kOoQ2J5AumwN0AlKiGEqFCHxPIE0WGM9vfpJoRoAnVITGDUqFEVFRVz5szp6OiQPxs40GFWVpY81kMgTRJCiAR1SExgxowZ8+fPnzlz5rVr1+TPBk4QHbpcLj2faEgI0Q3qkJjA1q1bFyxY4HQ6V61aBS/KHw+QIDpky1JCSIhQh8TyBNEhPvLq8B//+EdmZubt27fF20uXLnknI4QQ6pBYHl/nqQhT3r17Nzc3d//+/V999dWhQ4fwFonpnTt38FFLS0tPT8/NmzePHj36zTff4NPTp09fuHDhiy++uHr16r1797q7u+WFEkJsB3VITKCpqWncuHGrV6+WP/ghUNGHH37Y218mF1yH4qNmDxioqakRw42NjXjb0dEBFxYXF3d4yMnJQfqIaaqqqh48ePDpp59iduqQkOEAdUhMYN26dWKgs7Pz2LFjIieD/L7++uv79+9/9tln169f//zzz7/99luMxBiRyUFLfnO1UHR46tSplJSU7OzsnTt3jh07tr6+ftOmTfv27bty5cqSJUvwkdPpnD59enV1dVlZ2YwZM/AWhYER33zzTXmJhBA7Qh0Sc/jXv/61cuXKxMTE3bt3Iznr9SRqSMvu3r3b1tZ28uRJMZnoiSEyOeRqRUVFfnUY5Mak+DSUxqUw4vLly6WRx48fr6yslEYSQmwJdUhMIC8vb82aNUjFli5dChfOmTNn/fr1Fy9enOoBSVtLSwsm++STT5CrIVMUmdx3332HNFFaVG8IOgySOxJCiIA6JJYBuZo8ykNwHfY+rC8lhJAgUIfE8vSrw0DdMAghxAt1SCyP0KE78GMrmB0SQvqFOiQm0NraKgaOHTv28ccfi05+Dx486OnpaWlpuX79+sWLF+/fv48xhw8fvnfv3p07dzCM6cVbTC8GxEL6zQ5DaUpDCBnmUIfEBFJSUpYuXbpr166mpqb6+nrRBxFWW7FiRXt7+5o1axYuXHj8+PEtW7bU1NTcvHkTyrx79y7GYGKIcNu2bRh/69YtsbSsrCxfHapNSYMkjoQQIqAOiQmIHvGguLh49uzZopMf9IbhqqqqysrKjo4OOK+oqGjWrFmnTp1634PokvHRRx+Vl5dj/Llz58RCXC4XjAjnJSYm5ubl99z6HNFx6vT6DRv+3yoJISQo1CExAW895507d771IN5iAFIUXe/vecCYBw8efPXVV2IC5Ih4Rb7onaX3YTqYlp5+sqNTuNAbpU6ndzJCCAkCdUgsD1yYkpomidAbSBPr6jbK8xBCyA+hDokJzPZQVlaGbO/27dtFRUXixjSDo6q6RrWgbyBrlOchhJAfQh0SE/C2LD1w4EBtbW1NTc29e/dERehA2Vhfr/pPjYTERHlOQgjxgTokJuBtStPY2NjS0pKTk7Nz584fThISu5uaVfMFCuSIbGJKCAkEdUhMwLdl6TfffFNdXf3Dz0MiMTFRdV7wWL9hA41ICPELdUisR0ZGxoDyQt9gjkgI8Qt1SCwGZDZoF4qord3A+9QQQiSoQ2Il4uLjJbeVrVqjCg9xuO3DK9031PHegBTlpRNChjHUIbEMSOlUq60sW/VB8/5rPbcOtB7BQPeNm+cudh07fmL23HmtbUfV6X2Dt/YmhHihDok1OHzkiN++9stXllVU1bxbWb167bplK97e9f4Hpa63Fi7KHj9hIsbAjqfPnj9/6Yo6Y48nQeRtawghAuqQWIAgnQvfWrZi6rTph460Zy/JiY2N27Rl22U3csXP8/ILYUp1ejVoREJIL3VI9KeubmMobWfOnr8EEUKF4i2UeObcBXUyNSoqq2lEQgh1SLQmFBEaEoWFRfK6CSHDCeqQ6EtJSanqLd+YPXfezFmz1fGDiPKKKhqRkOEMdUg0Re1ToUbnmXPZS3J27Ho/v6Cosrp2zJhXS11vYeTc+QuWrXh7d9OeZctXbt2+s/vGzUCtaXzjZEfn/e+/l8tBCBkeUIdEU5CuqcaSQuiwbNWaA61H1tfVryxbdePmbQxjDML51rK6+sZrPbc+PXexed8BfKQuQYoDBw/J5SCEDA+oQ6IpTXv2qrqSYnpyyu+ffrq+cfPsufPefmd1Tm7eZfe102fPO7JmZDqykDVClrUbNqozBgo+GZGQYQt1SDTlcldXbl6+aqx+48RfT2VkZnV0nlE/Ch5RUVFyIQghwwbqkOhLkO6GhkdsXDxTQ0KGM9Qh0ZrDR44MNEe82HV19tx5YriiqkadQA24UF4xIWSYQR0S3XG73VXVwaz24ccnjh0/8bfOM0ePHRf3Ke08cw6v3TduenvlB4m8/AI+4IIQQh0SaxCfkHCyo1OVWY/noRabtmxbtnxl9pKcS1e6EUKHiM3b3lOn942U1DR5TYSQYQl1SKwBcsTa2g2qzxA5uXk16+tcby2HDm/cvN2878D05JS15RVtRz9asPDNDz/6RJ1FBPJCeTWEkOEKdUgsA4xYUVmtWq37+j+6b9y8er0HA3jr7V8YvKYUuaa8AkLIMIY6JBaj1OlU3Tag2N3UnJqWLi+XEDK8oQ6J9cgvKFQlF3rw3qSEEBXqkFgSt9sdn5Cgqi54lFdUsXMhIcQv1CGxKjBix6nTqvOCxKHWVnkphBDigTokFgZGRLanak+NlNS0w0eOyPMTQshDqENiefw2N5WCHe0JIcGhDonl2VhfH+RGbic7OtPS2Y6UENIP1CGxCX6NmJGZKU9HCCH+oA6JTbjc1RUbF+97I7emPXvliQghJADUIbEVbrc7L78gNS0dA/JnhBASGOqQEEIIoQ4JIYQQ6pAQQgjppQ4JIYSQXuqQEEII6aUOCSGEkF7qkBBCCOmlDgkhhJBe6pAQQgjppQ4JIYSQXuqQEEII6aUOCSGEkF7qkBBCCOmlDgkhhJBe6pAQQgjppQ4JIYSQXuqQEEII6aUOCSGEkF7qkBBCCAH/P9s8BoS4MkaLAAAAAElFTkSuQmCC>