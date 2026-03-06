import { useEffect, useRef, useState } from "react";
import {
  createNote,
  createTag,
  deleteDocument,
  generateFlashcards,
  generateQuiz,
  getDocuments,
  getNotes,
  getTags,
  getUploadJobs,
  removeNote,
  removeTag,
  sendChatMessage,
  uploadDocument
} from "./api";

const COMPLETED_UPLOAD_VISIBLE_MS = 4000;
const MOBILE_BREAKPOINT = 900;

const initialMessages = [
  {
    id: crypto.randomUUID(),
    type: "bot",
    content:
      "Your study stack is live. Drop in source material, pick the docs you want active, and I’ll help you turn them into answers, drills, and revision prompts.",
    sources: []
  }
];

const starterQuestions = [
  "Give me the fastest revision rundown from the checked docs.",
  "Turn this material into a last-minute exam prep checklist.",
  "Explain the difficult bits like a smart tutor, not a textbook."
];

function normalizeDocument(doc) {
  if (typeof doc === "string") {
    return { filename: doc, tag: null };
  }

  return {
    filename: doc.filename,
    tag: doc.tag ?? null
  };
}

function formatDate(dateString) {
  try {
    return new Date(dateString).toLocaleDateString();
  } catch (_error) {
    return dateString;
  }
}

function autoResize(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
}

function getViewportState() {
  if (typeof window === "undefined") {
    return { isMobile: false };
  }

  return {
    isMobile: window.innerWidth <= MOBILE_BREAKPOINT
  };
}

function FlashcardModal({ state, onClose, onFlip, onPrev, onNext }) {
  const cards = state.data?.cards || [];
  const currentCard = cards[state.index];

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <div className="modal-head">
          <div>
            <div className="chat-title">{state.data?.title || "Flashcards"}</div>
            <div className="header-subtitle">
              {state.loading
                ? "Cooking up a fresh flashcard deck from the selected source."
                : state.error
                  ? "Flashcard generation failed."
                  : "Tap the card to flip between prompt and answer."}
            </div>
          </div>
          <button className="modal-close" type="button" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="modal-body">
          {state.loading ? (
            <div className="empty-state">Building the deck...</div>
          ) : state.error ? (
            <div className="empty-state error-text">{state.error}</div>
          ) : currentCard ? (
            <>
              <div className="flashcard" onClick={onFlip}>
                <div>
                  <div className="flashcard-label">
                    {state.side === "front" ? "Prompt" : "Answer"}
                  </div>
                  <div className="flashcard-text">
                    {state.side === "front" ? currentCard.front : currentCard.back}
                  </div>
                </div>
              </div>
              <div className="flashcard-controls">
                <button
                  className="modal-button"
                  type="button"
                  onClick={onPrev}
                  disabled={state.index === 0}
                >
                  Back
                </button>
                <div className="flashcard-meta">
                  {state.index + 1} / {cards.length}
                </div>
                <button className="modal-button" type="button" onClick={onFlip}>
                  Flip
                </button>
                <button
                  className="modal-button primary"
                  type="button"
                  onClick={onNext}
                  disabled={state.index >= cards.length - 1}
                >
                  Next
                </button>
              </div>
            </>
          ) : (
            <div className="empty-state">No flashcards returned.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function QuizModal({ state, onClose, onAnswer }) {
  const questions = state.data?.questions || [];

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <div className="modal-head">
          <div>
            <div className="chat-title">{state.data?.title || "Quiz"}</div>
            <div className="header-subtitle">
              {state.loading
                ? "Building a question set from the selected source."
                : state.error
                  ? "Quiz generation failed."
                  : "Lock in an answer to reveal the explanation."}
            </div>
          </div>
          <button className="modal-close" type="button" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="modal-body">
          {state.loading ? (
            <div className="empty-state">Generating quiz questions...</div>
          ) : state.error ? (
            <div className="empty-state error-text">{state.error}</div>
          ) : questions.length ? (
            questions.map((question, index) => {
              const selected = state.answers[index];

              return (
                <section key={`${question.question}-${index}`} className="quiz-question">
                  <h3>
                    {index + 1}. {question.question}
                  </h3>
                  <div className="quiz-options">
                    {(question.options || []).map((option) => {
                      const answered = selected !== undefined;
                      const classNames = ["quiz-option"];

                      if (selected === option) {
                        classNames.push("selected");
                      }
                      if (answered && option === question.correct_answer) {
                        classNames.push("correct");
                      } else if (
                        answered &&
                        selected === option &&
                        option !== question.correct_answer
                      ) {
                        classNames.push("incorrect");
                      }

                      return (
                        <button
                          key={option}
                          className={classNames.join(" ")}
                          type="button"
                          disabled={answered}
                          onClick={() => onAnswer(index, option)}
                        >
                          {option}
                        </button>
                      );
                    })}
                  </div>
                  {selected !== undefined ? (
                    <div className="quiz-explanation">
                      <div className="quiz-feedback">
                        {selected === question.correct_answer
                          ? "Locked in. Correct."
                          : `You picked: ${selected}`}
                      </div>
                      <strong>Why:</strong> {question.explanation}
                    </div>
                  ) : null}
                </section>
              );
            })
          ) : (
            <div className="empty-state">No quiz questions returned.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function SidebarToggle({ side, open, onClick, mobile = false, label }) {
  const buttonLabel = label || `${open ? "Hide" : "Open"} ${side} sidebar`;

  return (
    <button
      className={`sidebar-toggle ${mobile ? "mobile" : ""}`}
      type="button"
      onClick={onClick}
      aria-label={buttonLabel}
    >
      <span className="sidebar-toggle-icon">
        {side === "left" ? (open ? "←" : "→") : open ? "→" : "←"}
      </span>
      <span className="sidebar-toggle-label">{label || (open ? "Hide" : "Open")}</span>
    </button>
  );
}

export default function App() {
  const [theme, setTheme] = useState(
    localStorage.getItem("theme") === "dark" ? "dark" : "light"
  );
  const [documents, setDocuments] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  const [tags, setTags] = useState([]);
  const [notes, setNotes] = useState([]);
  const [chatMessages, setChatMessages] = useState(initialMessages);
  const [chatInput, setChatInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadJobs, setUploadJobs] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState("");
  const [flashcardState, setFlashcardState] = useState({
    open: false,
    loading: false,
    error: "",
    data: null,
    side: "front",
    index: 0
  });
  const [quizState, setQuizState] = useState({
    open: false,
    loading: false,
    error: "",
    data: null,
    answers: {}
  });
  const [tagDraft, setTagDraft] = useState("");
  const [noteDraft, setNoteDraft] = useState("");
  const [errorBanner, setErrorBanner] = useState("");
  const [viewport, setViewport] = useState(getViewportState);
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(() => !getViewportState().isMobile);
  const [rightSidebarOpen, setRightSidebarOpen] = useState(() => !getViewportState().isMobile);

  const fileInputRef = useRef(null);
  const chatBodyRef = useRef(null);
  const seenCompletedJobsRef = useRef(new Set());
  const wasMobileRef = useRef(getViewportState().isMobile);

  function showError(message) {
    setErrorBanner(message);
  }

  useEffect(() => {
    document.body.classList.toggle("dark-mode", theme === "dark");
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    if (!errorBanner) {
      return undefined;
    }

    const timerId = window.setTimeout(() => {
      setErrorBanner("");
    }, 4500);

    return () => window.clearTimeout(timerId);
  }, [errorBanner]);

  useEffect(() => {
    function handleResize() {
      const nextViewport = getViewportState();
      setViewport(nextViewport);

      if (nextViewport.isMobile !== wasMobileRef.current) {
        if (nextViewport.isMobile) {
          setLeftSidebarOpen(false);
          setRightSidebarOpen(false);
        } else {
          setLeftSidebarOpen(true);
          setRightSidebarOpen(true);
        }
        wasMobileRef.current = nextViewport.isMobile;
      }
    }

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    void loadTagsAndNotes();
    void loadDocumentsList();
    void loadUploadJobsList();

    const timerId = window.setInterval(() => {
      void loadUploadJobsList();
    }, 2000);

    return () => window.clearInterval(timerId);
  }, []);

  useEffect(() => {
    if (!selectedDocument) {
      return;
    }

    const stillExists = documents.some((doc) => doc.filename === selectedDocument);
    if (!stillExists) {
      setSelectedDocument("");
    }
  }, [documents, selectedDocument]);

  useEffect(() => {
    const container = chatBodyRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [chatMessages]);

  async function loadTagsAndNotes() {
    try {
      const [tagsPayload, notesPayload] = await Promise.all([getTags(), getNotes()]);
      setTags(Array.isArray(tagsPayload.tags) ? tagsPayload.tags : []);
      setNotes(
        Array.isArray(notesPayload.notes)
          ? [...notesPayload.notes].sort(
              (a, b) => new Date(b.created_at) - new Date(a.created_at)
            )
          : []
      );
    } catch (error) {
      showError(error.message);
    }
  }

  async function loadDocumentsList() {
    try {
      const payload = await getDocuments();
      const nextDocuments = Array.isArray(payload.documents)
        ? payload.documents.map(normalizeDocument)
        : [];

      setDocuments(nextDocuments);
      setSelectedFiles((prev) => {
        if (prev.size === 0) {
          return new Set(nextDocuments.map((doc) => doc.filename));
        }

        const next = new Set();
        nextDocuments.forEach((doc) => {
          if (prev.has(doc.filename)) {
            next.add(doc.filename);
          }
        });
        return next;
      });
    } catch (error) {
      showError(error.message);
    }
  }

  async function loadUploadJobsList() {
    try {
      const payload = await getUploadJobs(50);
      const nextJobs = Array.isArray(payload.jobs) ? payload.jobs : [];
      setUploadJobs(nextJobs);

      let refreshDocuments = false;
      nextJobs.forEach((job) => {
        if (job.status === "completed" && !seenCompletedJobsRef.current.has(job.job_id)) {
          seenCompletedJobsRef.current.add(job.job_id);
          refreshDocuments = true;
        }
      });

      if (refreshDocuments) {
        await loadDocumentsList();
      }
    } catch (error) {
      console.error("Upload polling failed:", error);
    }
  }

  async function handleUpload(files) {
    const fileList = Array.from(files || []);
    if (!fileList.length) {
      return;
    }

    setErrorBanner("");

    for (const file of fileList) {
      try {
        await uploadDocument(file);
      } catch (error) {
        showError(`Upload failed for ${file.name}: ${error.message}`);
      }
    }

    await loadUploadJobsList();
  }

  async function handleAddTag() {
    const value = tagDraft.trim();
    if (!value || tags.includes(value)) {
      return;
    }

    try {
      await createTag(value);
      setTags((prev) => [...prev, value]);
      setTagDraft("");
    } catch (error) {
      showError(error.message);
    }
  }

  async function handleDeleteTag(tag) {
    try {
      await removeTag(tag);
      setTags((prev) => prev.filter((item) => item !== tag));
    } catch (error) {
      showError(error.message);
    }
  }

  async function handleAddNote() {
    const value = noteDraft.trim();
    if (!value) {
      return;
    }

    try {
      const payload = await createNote(value);
      setNotes((prev) => [payload.note, ...prev]);
      setNoteDraft("");
    } catch (error) {
      showError(error.message);
    }
  }

  async function handleDeleteNote(noteId) {
    try {
      await removeNote(noteId);
      setNotes((prev) => prev.filter((note) => note.id !== noteId));
    } catch (error) {
      showError(error.message);
    }
  }

  async function handleDeleteDocument(filename) {
    if (!window.confirm(`Delete ${filename}?`)) {
      return;
    }

    try {
      await deleteDocument(filename);
      await loadDocumentsList();
    } catch (error) {
      showError(error.message);
    }
  }

  async function handleSendMessage() {
    const message = chatInput.trim();
    if (!message || isSending) {
      return;
    }

    const selected = Array.from(selectedFiles);

    setChatMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        type: "user",
        content: message,
        sources: []
      }
    ]);
    setChatInput("");
    setIsSending(true);
    setErrorBanner("");

    try {
      const payload = await sendChatMessage(message, selected);
      setChatMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          type: "bot",
          content: payload.response,
          sources: payload.sources || []
        }
      ]);
    } catch (error) {
      setChatMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          type: "bot",
          content: `Error: ${error.message}`,
          sources: []
        }
      ]);
    } finally {
      setIsSending(false);
    }
  }

  async function handleGenerateFlashcards() {
    if (!selectedDocument) {
      return;
    }

    setFlashcardState({
      open: true,
      loading: true,
      error: "",
      data: null,
      side: "front",
      index: 0
    });

    try {
      const payload = await generateFlashcards(selectedDocument);
      setFlashcardState({
        open: true,
        loading: false,
        error: "",
        data: payload,
        side: "front",
        index: 0
      });
    } catch (error) {
      setFlashcardState({
        open: true,
        loading: false,
        error: error.message,
        data: null,
        side: "front",
        index: 0
      });
    }
  }

  async function handleGenerateQuiz() {
    if (!selectedDocument) {
      return;
    }

    setQuizState({
      open: true,
      loading: true,
      error: "",
      data: null,
      answers: {}
    });

    try {
      const payload = await generateQuiz(selectedDocument);
      setQuizState({
        open: true,
        loading: false,
        error: "",
        data: payload,
        answers: {}
      });
    } catch (error) {
      setQuizState({
        open: true,
        loading: false,
        error: error.message,
        data: null,
        answers: {}
      });
    }
  }

  const visibleUploadJobs = uploadJobs.filter((job) => {
    if (job.status !== "completed") {
      return true;
    }

    const completedAt = Date.parse(job.completed_at || "");
    if (Number.isNaN(completedAt)) {
      return true;
    }

    return Date.now() - completedAt < COMPLETED_UPLOAD_VISIBLE_MS;
  });

  const selectedDocumentNames = documents
    .filter((doc) => selectedFiles.has(doc.filename))
    .map((doc) => doc.filename);
  const hasStudioSelection = Boolean(selectedDocument);
  const isMobile = viewport.isMobile;
  const frameStyle = isMobile
    ? undefined
    : {
        gridTemplateColumns: [
          leftSidebarOpen ? "minmax(280px, 320px)" : "86px",
          "minmax(0, 1fr)",
          rightSidebarOpen ? "minmax(280px, 320px)" : "86px"
        ].join(" ")
      };

  return (
    <div className="app-shell">
      <div className="app-noise" />
      <div className="orb orb-one" />
      <div className="orb orb-two" />
      <div className="orb orb-three" />

      {isMobile && (leftSidebarOpen || rightSidebarOpen) ? (
        <button
          className="drawer-overlay"
          type="button"
          aria-label="Close sidebar"
          onClick={() => {
            setLeftSidebarOpen(false);
            setRightSidebarOpen(false);
          }}
        />
      ) : null}

      <div className="app-topbar">
        <div className="topbar-brand">
          <div className="brand-mark">SS</div>
          <div className="topbar-copy">
            <span className="eyebrow">Study Space</span>
            <h1>Turn course chaos into something you can actually revise.</h1>
          </div>
        </div>
        <div className="topbar-actions">
          <div className="status-chip pulse">
            {documents.length} doc{documents.length === 1 ? "" : "s"} loaded
          </div>
          <button
            className="theme-toggle"
            type="button"
            onClick={() => setTheme((prev) => (prev === "dark" ? "light" : "dark"))}
            title="Toggle theme"
          >
            {theme === "dark" ? "☀" : "☾"}
          </button>
        </div>
      </div>

      <div className="app-frame" style={frameStyle}>
        <aside
          className={`side-panel left-panel ${leftSidebarOpen ? "open" : "collapsed"} ${
            isMobile ? "mobile" : ""
          }`}
        >
          <div className="panel glass-panel">
            <div className="panel-header">
              <div className="panel-heading">
                <div className="section-kicker">Workspace</div>
                <div>
                  <div className="panel-title">Source Stack</div>
                  <div className="header-subtitle">
                    Upload lecture notes, readings, and handouts in one place.
                  </div>
                </div>
              </div>
              <SidebarToggle
                side="left"
                open={leftSidebarOpen}
                mobile={isMobile}
                onClick={() => setLeftSidebarOpen((prev) => !prev)}
              />
            </div>

            <div className="side-rail">
              <button
                className="rail-badge"
                type="button"
                onClick={() => setLeftSidebarOpen((prev) => !prev)}
              >
                📚
              </button>
              <div className="rail-count">{documents.length}</div>
              <div className="rail-mini-label">Docs</div>
            </div>

            <div className="panel-body left-body">
              <div className="sidebar-stack">
                <section className="hero-card accent-card">
                  <div className="hero-card-top">
                    <div className="hero-badge">Ready to build</div>
                    <div className="helper-text">
                      {selectedFiles.size} active source{selectedFiles.size === 1 ? "" : "s"}
                    </div>
                  </div>
                  <h2>Keep the exact material you want in the room.</h2>
                  <p>
                    Check the documents that should shape the chat. Everything else stays out
                    of the answer stream.
                  </p>
                </section>

                <section className="section">
                  <div className="section-head">
                    <div className="section-title">Upload</div>
                    <div className="helper-text">drag, drop, done</div>
                  </div>
                  <div
                    className={`upload-zone ${isDragOver ? "drag-over" : ""}`}
                    onClick={() => fileInputRef.current?.click()}
                    onDragOver={(event) => {
                      event.preventDefault();
                      setIsDragOver(true);
                    }}
                    onDragLeave={() => setIsDragOver(false)}
                    onDrop={(event) => {
                      event.preventDefault();
                      setIsDragOver(false);
                      void handleUpload(event.dataTransfer.files);
                    }}
                  >
                    <strong>Drop files or tap to upload</strong>
                    <span>PDF, DOCX, TXT, and Markdown all work here.</span>
                    <input
                      ref={fileInputRef}
                      hidden
                      type="file"
                      accept=".pdf,.docx,.txt,.md"
                      multiple
                      onChange={async (event) => {
                        await handleUpload(event.currentTarget.files);
                        event.currentTarget.value = "";
                      }}
                    />
                  </div>
                </section>

                <section className="section">
                  <div className="section-head">
                    <div className="section-title">Pipeline</div>
                    <div className="helper-text">{visibleUploadJobs.length} live</div>
                  </div>
                  <div className="stack">
                    {visibleUploadJobs.length ? (
                      visibleUploadJobs.map((job) => (
                        <div key={job.job_id} className={`upload-job status-${job.status}`}>
                          <div className="upload-job-head">
                            <div className="upload-job-file" title={job.filename}>
                              {job.filename}
                            </div>
                            <div className="upload-job-status">{job.status}</div>
                          </div>
                          <div className="meta-text">{job.stage}</div>
                          <div className="progress-track">
                            <div
                              className="progress-bar"
                              style={{
                                width: `${Math.max(0, Math.min(100, job.progress || 0))}%`
                              }}
                            />
                          </div>
                          <div className="upload-job-meta">
                            {[
                              job.queue_position ? `Queue #${job.queue_position}` : null,
                              job.predicted_tag ? `Tag: ${job.predicted_tag}` : null,
                              typeof job.processing_time_seconds === "number"
                                ? `${job.processing_time_seconds.toFixed(2)}s`
                                : null,
                              job.error ? `Error: ${job.error}` : null
                            ]
                              .filter(Boolean)
                              .join(" • ")}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="empty-card">Nothing processing right now.</div>
                    )}
                  </div>
                </section>

                <section className="section">
                  <div className="section-head">
                    <div className="section-title">Documents</div>
                    <div className="helper-text">{documents.length} indexed</div>
                  </div>
                  <div className="stack">
                    {documents.length ? (
                      documents.map((doc) => (
                        <div key={doc.filename} className="document-item">
                          <label className="document-select">
                            <input
                              type="checkbox"
                              checked={selectedFiles.has(doc.filename)}
                              onChange={() =>
                                setSelectedFiles((prev) => {
                                  const next = new Set(prev);
                                  if (next.has(doc.filename)) {
                                    next.delete(doc.filename);
                                  } else {
                                    next.add(doc.filename);
                                  }
                                  return next;
                                })
                              }
                            />
                            <div className="document-meta">
                              <div className="document-name" title={doc.filename}>
                                {doc.filename}
                              </div>
                              <div className="document-line">
                                {doc.tag ? <span className="pill">{doc.tag}</span> : null}
                                {selectedFiles.has(doc.filename) ? (
                                  <span className="micro-pill active">Live</span>
                                ) : (
                                  <span className="micro-pill">Muted</span>
                                )}
                              </div>
                            </div>
                          </label>
                          <button
                            className="icon-button"
                            type="button"
                            title="Delete"
                            onClick={() => void handleDeleteDocument(doc.filename)}
                          >
                            ×
                          </button>
                        </div>
                      ))
                    ) : (
                      <div className="empty-card">No documents yet. Start by dropping a file.</div>
                    )}
                  </div>
                </section>

                <section className="section">
                  <div className="section-head">
                    <div className="section-title">Topics</div>
                  </div>
                  <div className="tags-wrap">
                    {tags.length ? (
                      tags.map((tag) => (
                        <div key={tag} className="tag-chip">
                          <span>{tag}</span>
                          <button
                            type="button"
                            aria-label={`Delete ${tag}`}
                            onClick={() => void handleDeleteTag(tag)}
                          >
                            ×
                          </button>
                        </div>
                      ))
                    ) : (
                      <div className="empty-card compact">No topics yet.</div>
                    )}
                  </div>
                  <div className="input-row">
                    <input
                      className="input"
                      value={tagDraft}
                      placeholder="Add a topic lens..."
                      onChange={(event) => setTagDraft(event.currentTarget.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          event.preventDefault();
                          void handleAddTag();
                        }
                      }}
                    />
                    <button
                      className="small-button primary"
                      type="button"
                      onClick={() => void handleAddTag()}
                    >
                      Add
                    </button>
                  </div>
                </section>

                <section className="section">
                  <div className="section-head">
                    <div className="section-title">Notes</div>
                    <div className="helper-text">{notes.length} saved</div>
                  </div>
                  <div className="notes-list">
                    {notes.length ? (
                      notes.map((note) => (
                        <div key={note.id} className="note-card">
                          <div className="note-content">{note.content}</div>
                          <div className="note-footer">
                            <div className="note-date">{formatDate(note.created_at)}</div>
                            <button
                              className="note-delete"
                              type="button"
                              onClick={() => void handleDeleteNote(note.id)}
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="empty-card">No notes yet. Capture the good bits here.</div>
                    )}
                  </div>
                  <div className="stack">
                    <textarea
                      className="textarea"
                      placeholder="Drop a quick takeaway, quote, or reminder..."
                      value={noteDraft}
                      onChange={(event) => setNoteDraft(event.currentTarget.value)}
                    />
                    <button
                      className="small-button primary"
                      type="button"
                      onClick={() => void handleAddNote()}
                    >
                      Save note
                    </button>
                  </div>
                </section>
              </div>
            </div>
          </div>
        </aside>

        <main className="panel chat-panel glass-panel">
          <div className="chat-header">
            <div className="chat-toolbar mobile-only">
              <SidebarToggle
                side="left"
                open={leftSidebarOpen}
                mobile
                label="Sources"
                onClick={() => {
                  setLeftSidebarOpen((prev) => !prev);
                  setRightSidebarOpen(false);
                }}
              />
              <SidebarToggle
                side="right"
                open={rightSidebarOpen}
                mobile
                label="Studio"
                onClick={() => {
                  setRightSidebarOpen((prev) => !prev);
                  setLeftSidebarOpen(false);
                }}
              />
            </div>
            <div className="chat-header-row">
              <div className="chat-heading">
                <div className="section-kicker">Tutor Mode</div>
                <div className="chat-title-row">
                  <div>
                    <div className="chat-title">Ask against your chosen stack</div>
                    <div className="header-subtitle">
                      Fast answers, summaries, and explanations grounded in the docs you have
                      checked in.
                    </div>
                  </div>
                  <div className="chat-status-pill">
                    {selectedFiles.size} source{selectedFiles.size === 1 ? "" : "s"} live
                  </div>
                </div>
              </div>
              <div className="desktop-sidebar-actions">
                <SidebarToggle
                  side="left"
                  open={leftSidebarOpen}
                  onClick={() => setLeftSidebarOpen((prev) => !prev)}
                />
                <SidebarToggle
                  side="right"
                  open={rightSidebarOpen}
                  onClick={() => setRightSidebarOpen((prev) => !prev)}
                />
              </div>
            </div>
            <div className="selected-stack">
              {selectedDocumentNames.length ? (
                selectedDocumentNames.slice(0, 4).map((name) => (
                  <span key={name} className="source-chip">
                    {name}
                  </span>
                ))
              ) : (
                <span className="source-chip muted">No sources selected</span>
              )}
              {selectedDocumentNames.length > 4 ? (
                <span className="source-chip muted">
                  +{selectedDocumentNames.length - 4} more
                </span>
              ) : null}
            </div>
            {errorBanner ? <div className="banner error-text">{errorBanner}</div> : null}
          </div>

          <div className="chat-body" ref={chatBodyRef}>
            {chatMessages.length === 1 ? (
              <section className="chat-hero">
                <div className="chat-hero-grid">
                  <div className="chat-hero-copy">
                    <div className="chat-hero-badge">Hot desk</div>
                    <h2>Make your notes hit harder than the original lecture.</h2>
                    <p>
                      Ask for concept maps, cram sheets, explainers, comparison tables, or
                      challenge questions. Keep the thread moving without losing your document
                      context.
                    </p>
                  </div>
                  <div className="hero-metrics">
                    <div className="metric-card">
                      <span className="metric-value">{documents.length}</span>
                      <span className="metric-label">loaded docs</span>
                    </div>
                    <div className="metric-card">
                      <span className="metric-value">{tags.length}</span>
                      <span className="metric-label">topics tracked</span>
                    </div>
                    <div className="metric-card">
                      <span className="metric-value">{notes.length}</span>
                      <span className="metric-label">notes saved</span>
                    </div>
                  </div>
                </div>
                <div className="starter-grid">
                  {starterQuestions.map((question) => (
                    <button
                      key={question}
                      className="starter-card"
                      type="button"
                      onClick={() => setChatInput(question)}
                    >
                      {question}
                    </button>
                  ))}
                </div>
              </section>
            ) : null}

            {chatMessages.map((message) => (
              <article key={message.id} className={`message ${message.type}`}>
                <div className="message-sender">
                  {message.type === "user" ? "You" : "Study Space"}
                </div>
                <div className="message-body">{message.content}</div>
                {message.sources?.length ? (
                  <div className="sources">
                    <div className="source-list-label">Pulled from</div>
                    <div className="source-pills">
                      {message.sources.map((source, index) => (
                        <span
                          key={`${message.id}-${source.filename || source.source || index}`}
                          className="source-pill"
                        >
                          {source.filename || source.source || "Unknown source"}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}
              </article>
            ))}
          </div>

          <div className="chat-footer">
            {isSending ? <div className="loading-text">Thinking through your material...</div> : null}
            <div className="composer-shell">
              <div className="composer">
                <textarea
                  className="textarea composer-input"
                  rows="1"
                  placeholder="Ask for a summary, breakdown, challenge question, or study guide..."
                  value={chatInput}
                  onChange={(event) => {
                    setChatInput(event.currentTarget.value);
                    autoResize(event.currentTarget);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      void handleSendMessage();
                    }
                  }}
                />
                <button
                  className="send-button"
                  type="button"
                  onClick={() => void handleSendMessage()}
                  disabled={isSending}
                >
                  ➜
                </button>
              </div>
              <div className="composer-meta">
                <span>Enter to send</span>
                <span>Shift + Enter for a new line</span>
              </div>
            </div>
          </div>
        </main>

        <aside
          className={`side-panel right-panel ${rightSidebarOpen ? "open" : "collapsed"} ${
            isMobile ? "mobile" : ""
          }`}
        >
          <div className="panel glass-panel">
            <div className="panel-header">
              <div className="panel-heading">
                <div className="section-kicker">Studio</div>
                <div>
                  <div className="panel-title">Practice Lab</div>
                  <div className="header-subtitle">
                    Turn one source into drills, recall loops, and quick revision tools.
                  </div>
                </div>
              </div>
              <SidebarToggle
                side="right"
                open={rightSidebarOpen}
                mobile={isMobile}
                onClick={() => setRightSidebarOpen((prev) => !prev)}
              />
            </div>

            <div className="side-rail">
              <button
                className="rail-badge neon"
                type="button"
                onClick={() => setRightSidebarOpen((prev) => !prev)}
              >
                ✦
              </button>
              <div className="rail-count">{hasStudioSelection ? 1 : 0}</div>
              <div className="rail-mini-label">Live</div>
            </div>

            <div className="panel-body right-body">
              <div className="studio-stack">
                <section className="hero-card studio-hero">
                  <div className="hero-badge">Practice loop</div>
                  <h2>Pick one source, then spin it into active recall.</h2>
                  <p>
                    Use flashcards for memory work and quiz mode when you want immediate feedback.
                  </p>
                </section>

                <section className="section">
                  <div className="section-title">Source document</div>
                  <select
                    className="select"
                    value={selectedDocument}
                    onChange={(event) => setSelectedDocument(event.currentTarget.value)}
                  >
                    <option value="">Select a document...</option>
                    {documents.map((doc) => (
                      <option key={doc.filename} value={doc.filename}>
                        {doc.filename}
                      </option>
                    ))}
                  </select>
                  <div className="helper-text">
                    {selectedDocument || "Choose a source to unlock the studio tools."}
                  </div>
                </section>

                <section className="section">
                  <div className="section-title">Tools</div>
                  <button className="studio-card audio-card" type="button" disabled>
                    <div className="studio-card-icon">🎧</div>
                    <div>
                      <div className="studio-card-title">Audio recap</div>
                      <div className="helper-text">Reserved for a future drop.</div>
                    </div>
                  </button>
                  <button
                    className="studio-card quiz-card"
                    type="button"
                    disabled={!hasStudioSelection}
                    onClick={() => void handleGenerateQuiz()}
                  >
                    <div className="studio-card-icon">📝</div>
                    <div>
                      <div className="studio-card-title">Quiz me</div>
                      <div className="helper-text">Generate multiple choice pressure checks.</div>
                    </div>
                  </button>
                  <button
                    className="studio-card flashcard-card"
                    type="button"
                    disabled={!hasStudioSelection}
                    onClick={() => void handleGenerateFlashcards()}
                  >
                    <div className="studio-card-icon">🗂</div>
                    <div>
                      <div className="studio-card-title">Flashcards</div>
                      <div className="helper-text">Practice terms, prompts, and definitions.</div>
                    </div>
                  </button>
                </section>
              </div>
            </div>
          </div>
        </aside>
      </div>

      {flashcardState.open ? (
        <FlashcardModal
          state={flashcardState}
          onClose={() =>
            setFlashcardState({
              open: false,
              loading: false,
              error: "",
              data: null,
              side: "front",
              index: 0
            })
          }
          onFlip={() =>
            setFlashcardState((prev) => ({
              ...prev,
              side: prev.side === "front" ? "back" : "front"
            }))
          }
          onPrev={() =>
            setFlashcardState((prev) => ({
              ...prev,
              index: Math.max(0, prev.index - 1),
              side: "front"
            }))
          }
          onNext={() =>
            setFlashcardState((prev) => ({
              ...prev,
              index: Math.min((prev.data?.cards?.length || 1) - 1, prev.index + 1),
              side: "front"
            }))
          }
        />
      ) : null}

      {quizState.open ? (
        <QuizModal
          state={quizState}
          onClose={() =>
            setQuizState({
              open: false,
              loading: false,
              error: "",
              data: null,
              answers: {}
            })
          }
          onAnswer={(questionIndex, selectedOption) =>
            setQuizState((prev) => ({
              ...prev,
              answers: {
                ...prev.answers,
                [questionIndex]: selectedOption
              }
            }))
          }
        />
      ) : null}
    </div>
  );
}
