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

const initialMessages = [
  {
    id: crypto.randomUUID(),
    type: "bot",
    content:
      "Hello! I'm here to help you with your studies. Upload documents on the left and ask me anything about them.",
    sources: []
  }
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
                ? "Generating flashcards from the selected document."
                : state.error
                  ? "Flashcard generation failed."
                  : "Flip the card to switch between prompt and answer."}
            </div>
          </div>
          <button className="modal-close" type="button" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="modal-body">
          {state.loading ? (
            <div className="empty-state">
              Analyzing document and generating flashcards...
            </div>
          ) : state.error ? (
            <div className="empty-state error-text">{state.error}</div>
          ) : currentCard ? (
            <>
              <div className="flashcard" onClick={onFlip}>
                <div>
                  <div className="flashcard-label">
                    {state.side === "front" ? "Term" : "Definition"}
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
                  Prev
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
                ? "Generating questions from the selected document."
                : state.error
                  ? "Quiz generation failed."
                  : "Pick one answer per question to reveal feedback."}
            </div>
          </div>
          <button className="modal-close" type="button" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="modal-body">
          {state.loading ? (
            <div className="empty-state">
              Analyzing document and generating quiz questions...
            </div>
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
                          ? "Correct."
                          : `Selected: ${selected}`}
                      </div>
                      <strong>Explanation:</strong> {question.explanation}
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

  const fileInputRef = useRef(null);
  const chatBodyRef = useRef(null);
  const seenCompletedJobsRef = useRef(new Set());

  useEffect(() => {
    document.body.classList.toggle("dark-mode", theme === "dark");
    localStorage.setItem("theme", theme);
  }, [theme]);

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
      setErrorBanner(error.message);
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
      setErrorBanner(error.message);
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
      setErrorBanner(error.message);
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
        setErrorBanner(`Upload failed for ${file.name}: ${error.message}`);
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
      setErrorBanner(error.message);
    }
  }

  async function handleDeleteTag(tag) {
    try {
      await removeTag(tag);
      setTags((prev) => prev.filter((item) => item !== tag));
    } catch (error) {
      setErrorBanner(error.message);
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
      setErrorBanner(error.message);
    }
  }

  async function handleDeleteNote(noteId) {
    try {
      await removeNote(noteId);
      setNotes((prev) => prev.filter((note) => note.id !== noteId));
    } catch (error) {
      setErrorBanner(error.message);
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
      setErrorBanner(error.message);
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

  const hasStudioSelection = Boolean(selectedDocument);

  return (
    <div className="app-shell">
      <div className="app-frame">
        <aside className="panel sidebar">
          <div className="panel-header">
            <div className="brand">
              <div className="brand-mark">SH</div>
              <div className="brand-copy">
                <h1>Study Hub</h1>
                <p>React frontend with a Vite build served by FastAPI.</p>
              </div>
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
          <div className="panel-body">
            <div className="sidebar-stack">
              <section className="section">
                <div className="section-head">
                  <div className="section-title">Documents</div>
                  <div className="helper-text">{documents.length} indexed</div>
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
                  <strong>Drop files here or click to upload</strong>
                  <span>PDF, DOCX, TXT, and Markdown are supported.</span>
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
                    <div className="empty-state">No active uploads.</div>
                  )}
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
                            {doc.tag ? <span className="pill">{doc.tag}</span> : null}
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
                    <div className="empty-state">No documents uploaded yet.</div>
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
                    <div className="empty-state">No topics yet.</div>
                  )}
                </div>
                <div className="input-row">
                  <input
                    className="input"
                    value={tagDraft}
                    placeholder="New topic..."
                    onChange={(event) => setTagDraft(event.currentTarget.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        void handleAddTag();
                      }
                    }}
                  />
                  <button className="small-button primary" type="button" onClick={() => void handleAddTag()}>
                    Add
                  </button>
                </div>
              </section>

              <section className="section">
                <div className="section-head">
                  <div className="section-title">Notes</div>
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
                    <div className="empty-state">No notes yet.</div>
                  )}
                </div>
                <div className="stack">
                  <textarea
                    className="textarea"
                    placeholder="Take a note..."
                    value={noteDraft}
                    onChange={(event) => setNoteDraft(event.currentTarget.value)}
                  />
                  <button className="small-button primary" type="button" onClick={() => void handleAddNote()}>
                    Save note
                  </button>
                </div>
              </section>
            </div>
          </div>
        </aside>

        <main className="panel chat-panel">
          <div className="chat-header">
            <div className="chat-title">AI Assistant</div>
            <div className="header-subtitle">
              Ask questions against the currently selected document set.
            </div>
            {errorBanner ? (
              <div className="helper-text error-text top-gap">{errorBanner}</div>
            ) : null}
          </div>
          <div className="chat-body" ref={chatBodyRef}>
            {chatMessages.map((message) => (
              <article key={message.id} className={`message ${message.type}`}>
                <div className="message-sender">
                  {message.type === "user" ? "You" : "AI Assistant"}
                </div>
                <div className="message-body">{message.content}</div>
                {message.sources?.length ? (
                  <div className="sources">
                    <div className="source-list-label">Sources</div>
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
            {isSending ? <div className="loading-text">Thinking...</div> : null}
            <div className="composer">
              <textarea
                className="textarea"
                rows="1"
                placeholder="Ask a question about your documents..."
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
          </div>
        </main>

        <aside className="panel studio">
          <div className="panel-header">
            <div>
              <div className="studio-title">Studio</div>
              <div className="header-subtitle">
                Generate quiz and flashcard practice from one source document.
              </div>
            </div>
          </div>
          <div className="panel-body">
            <div className="studio-stack">
              <section className="section">
                <div className="section-title">Source Document</div>
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
              </section>

              <section className="section">
                <div className="section-title">Tools</div>
                <button className="studio-card" type="button" disabled>
                  <div className="studio-card-icon">🎧</div>
                  <div>
                    <div className="studio-card-title">Audio Overview</div>
                    <div className="helper-text">Reserved for a future iteration.</div>
                  </div>
                </button>
                <button
                  className="studio-card"
                  type="button"
                  disabled={!hasStudioSelection}
                  onClick={() => void handleGenerateQuiz()}
                >
                  <div className="studio-card-icon">📝</div>
                  <div>
                    <div className="studio-card-title">Quiz</div>
                    <div className="helper-text">Generate multiple-choice questions.</div>
                  </div>
                </button>
                <button
                  className="studio-card"
                  type="button"
                  disabled={!hasStudioSelection}
                  onClick={() => void handleGenerateFlashcards()}
                >
                  <div className="studio-card-icon">🗂</div>
                  <div>
                    <div className="studio-card-title">Flashcards</div>
                    <div className="helper-text">Practice key terms and definitions.</div>
                  </div>
                </button>
              </section>
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
