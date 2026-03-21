import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Calendar from "./Calendar";
import {
  createNote,
  createTag,
  deleteDocument,
  generateFlashcards,
  generateQuiz,
  getCurrentUser,
  getDocuments,
  getMetadata,
  getNotes,
  getTags,
  getUploadJobs,
  signIn,
  signOut,
  signUp,
  removeNote,
  removeTag,
  sendChatMessage,
  uploadDocument,
  updateDocumentTag
} from "./api";

const COMPLETED_UPLOAD_VISIBLE_MS = 4000;
const MOBILE_BREAKPOINT = 900;

const initialMessages = [];

const starterQuestions = [
  "Give me a quick summary.",
  "Create an exam prep checklist.",
  "Explain the difficult concepts."
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

function isUnauthorizedError(error) {
  return error?.status === 401;
}

function dedupeSources(sources = []) {
  const seen = new Set();

  return sources.filter((source) => {
    const label = (source?.filename || source?.source || "Unknown source").trim();
    const key = label.toLowerCase();
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function formatDistance(distance) {
  if (typeof distance !== "number" || Number.isNaN(distance)) {
    return null;
  }

  return `Distance ${distance.toFixed(3)}`;
}

function formatTraceTiming(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return null;
  }

  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}s`;
  }

  return `${Math.round(value)}ms`;
}

function MessageContent({ message }) {
  if (message.type === "user") {
    return <div className="message-body">{message.content}</div>;
  }

  return (
    <div className="message-body message-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node: _node, ...props }) => <a {...props} target="_blank" rel="noreferrer" />
        }}
      >
        {message.content}
      </ReactMarkdown>
    </div>
  );
}

function RetrievalTrace({ message }) {
  const trace = message.trace;
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    if (message.status !== "running") {
      setActiveStep(0);
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      setActiveStep((current) => (current + 1) % 3);
    }, 1200);

    return () => window.clearInterval(intervalId);
  }, [message.status]);

  if (message.status === "running") {
    const pendingSteps = [
      "Generating 3 search angles",
      "Retrieving across your study material",
      "Fusing evidence into one answer"
    ];

    return (
      <div className="retrieval-trace pending">
        <div className="source-list-label">Search plan</div>
        <div className="trace-progress">
          {pendingSteps.map((step, index) => (
            <div
              key={step}
              className={`trace-progress-step ${index === activeStep ? "active" : ""}`}
            >
              {step}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!trace) {
    return null;
  }

  const queryCount = trace.generated_queries?.length || 0;
  const fusedResults = Array.isArray(trace.fused_results) ? trace.fused_results : [];
  const retrievalRuns = Array.isArray(trace.retrieval_runs) ? trace.retrieval_runs : [];
  const summary = trace.summary || {};
  const timings = trace.timings_ms || {};

  return (
    <div className="retrieval-trace">
      <div className="trace-head">
        <div className="source-list-label">Search breakdown</div>
        <div className="trace-pill-row">
          <span className="chat-status-pill">{queryCount} queries</span>
          <span className="chat-status-pill">{summary.passages_used || fusedResults.length} passages</span>
          <span className="chat-status-pill">{summary.documents_considered || 0} docs</span>
          {formatTraceTiming(timings.total) ? (
            <span className="chat-status-pill">{formatTraceTiming(timings.total)}</span>
          ) : null}
        </div>
      </div>

      <details className="trace-details">
        <summary>How I searched</summary>
        <div className="trace-section">
          <div className="trace-query-grid">
            {(trace.generated_queries || []).map((query) => (
              <article key={query.id} className="trace-query-card">
                <div className="trace-query-top">
                  <div className="trace-query-id">{query.id?.toUpperCase() || "Q"}</div>
                  {query.module_tag ? (
                    <span className="micro-pill">Module {query.module_tag}</span>
                  ) : null}
                </div>
                <div className="trace-query-text">{query.text}</div>
                {query.goal ? <div className="meta-text">{query.goal}</div> : null}
              </article>
            ))}
          </div>
        </div>

        <div className="trace-section">
          <div className="trace-section-title">Retrieved by query</div>
          <div className="trace-run-list">
            {retrievalRuns.map((run) => (
              <section key={run.query_id} className="trace-run-card">
                <div className="trace-run-head">
                  <div>
                    <div className="trace-run-label">{run.query_id?.toUpperCase() || "Query"}</div>
                    <div className="trace-run-query">{run.query}</div>
                  </div>
                  {run.module_tag ? <span className="micro-pill">{run.module_tag}</span> : null}
                </div>
                {Array.isArray(run.results) && run.results.length ? (
                  <div className="trace-result-list">
                    {run.results.map((result) => (
                      <article key={result.id} className={`trace-result-card ${result.kept_in_fusion ? "kept" : ""}`}>
                        <div className="trace-result-top">
                          <div className="trace-result-file">{result.filename}</div>
                          <div className="trace-result-meta">
                            <span>Chunk {typeof result.chunk_index === "number" ? result.chunk_index + 1 : "?"}</span>
                            {formatDistance(result.distance) ? <span>{formatDistance(result.distance)}</span> : null}
                            {result.kept_in_fusion ? <span>Used</span> : <span>Reviewed</span>}
                          </div>
                        </div>
                        {result.snippet ? <div className="trace-result-snippet">{result.snippet}</div> : null}
                      </article>
                    ))}
                  </div>
                ) : (
                  <div className="empty-card compact">No passages retrieved for this query.</div>
                )}
              </section>
            ))}
          </div>
        </div>

        {fusedResults.length ? (
          <div className="trace-section">
            <div className="trace-section-title">Evidence used in the final answer</div>
            <div className="trace-result-list">
              {fusedResults.map((result) => (
                <article key={result.id} className="trace-result-card kept">
                  <div className="trace-result-top">
                    <div className="trace-result-file">
                      {result.source_id ? `${result.source_id} • ` : ""}
                      {result.filename}
                    </div>
                    <div className="trace-result-meta">
                      <span>Chunk {typeof result.chunk_index === "number" ? result.chunk_index + 1 : "?"}</span>
                      {result.tag ? <span>{result.tag}</span> : null}
                      {Array.isArray(result.query_ids) && result.query_ids.length ? (
                        <span>{result.query_ids.map((queryId) => queryId.toUpperCase()).join(", ")}</span>
                      ) : null}
                    </div>
                  </div>
                  {result.snippet ? <div className="trace-result-snippet">{result.snippet}</div> : null}
                </article>
              ))}
            </div>
          </div>
        ) : null}
      </details>
    </div>
  );
}

function ChatMessageCard({ message }) {
  const hasSources = dedupeSources(message.sources).length > 0;
  const showTrace = message.type === "bot";
  const displayContent =
    message.type === "bot" && message.status === "running" && !message.content
      ? "Working through your material..."
      : message.content;

  return (
    <article className={`message ${message.type} ${message.status === "running" ? "pending" : ""}`}>
      <div className="message-sender">{message.type === "user" ? "You" : "Study Space"}</div>
      <MessageContent message={{ ...message, content: displayContent }} />
      {showTrace ? <RetrievalTrace message={message} /> : null}
      {hasSources ? (
        <div className="sources">
          <div className="source-list-label">Evidence used</div>
          <div className="source-pills">
            {dedupeSources(message.sources).map((source, index) => (
              <span
                key={`${message.id}-${source.filename || source.source || index}`}
                className="source-pill"
              >
                {source.source_id ? `${source.source_id} • ` : ""}
                {source.filename || source.source || "Unknown source"}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </article>
  );
}

function AuthScreen({
  mode,
  form,
  busy,
  error,
  onChange,
  onSubmit,
  onToggleMode
}) {
  const isSignUp = mode === "signup";

  return (
    <div className="auth-shell">
      <div className="app-noise" />
      <div className="orb orb-one" />
      <div className="orb orb-two" />
      <div className="orb orb-three" />
      <section className="auth-panel glass-panel">
        <div className="auth-kicker">Private workspace</div>
        <h1>{isSignUp ? "Create your study space" : "Sign in to Study Space"}</h1>
        <p className="auth-copy">
          Notes, documents, quizzes, flashcards, and chat context stay scoped to your account.
        </p>
        <form
          className="auth-form"
          onSubmit={(event) => {
            event.preventDefault();
            onSubmit();
          }}
        >
          <label className="auth-field">
            <span>Username</span>
            <input
              className="input"
              autoComplete="username"
              value={form.username}
              onChange={(event) => onChange("username", event.currentTarget.value)}
              placeholder="your-name"
            />
          </label>
          <label className="auth-field">
            <span>Password</span>
            <input
              className="input"
              type="password"
              autoComplete={isSignUp ? "new-password" : "current-password"}
              value={form.password}
              onChange={(event) => onChange("password", event.currentTarget.value)}
              placeholder="At least 8 characters"
            />
          </label>
          {error ? <div className="banner error-text">{error}</div> : null}
          <div className="auth-actions">
            <button className="small-button primary auth-submit" type="submit" disabled={busy}>
              {busy ? "Working..." : isSignUp ? "Create account" : "Sign in"}
            </button>
            <button className="small-button" type="button" onClick={onToggleMode} disabled={busy}>
              {isSignUp ? "Have an account?" : "Need an account?"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
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

function SettingsModal({
  onClose,
  tags,
  tagDraft,
  onTagDraftChange,
  onAddTag,
  onDeleteTag
}) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(event) => event.stopPropagation()} style={{ maxWidth: '600px' }}>
        <div className="modal-head">
          <div>
            <div className="chat-title">Settings</div>
            <div className="header-subtitle">
              Manage topics, sections, and global workspace preferences.
            </div>
          </div>
          <button className="modal-close" type="button" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="modal-body">
          <section className="section">
            <div className="section-head">
              <div className="section-title">Topics</div>
              <div className="helper-text">{tags.length} active lens{tags.length === 1 ? '' : 'es'}</div>
            </div>
            <p className="meta-text" style={{ marginBottom: '16px' }}>
              Topics act as academic filters for your documents and insights.
            </p>
            <div className="tags-wrap" style={{ marginBottom: '20px' }}>
              {tags.length ? (
                tags.map((tag) => (
                  <div key={tag} className="tag-chip">
                    <span>{tag}</span>
                    <button
                      type="button"
                      aria-label={`Delete ${tag}`}
                      onClick={() => void onDeleteTag(tag)}
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
                placeholder="Add a topic lens (e.g. AI, CS101)..."
                onChange={(event) => onTagDraftChange(event.currentTarget.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    void onAddTag();
                  }
                }}
              />
              <button
                className="small-button primary"
                type="button"
                onClick={() => void onAddTag()}
              >
                Add
              </button>
            </div>
          </section>

          <section className="section" style={{ marginTop: '32px', opacity: 0.6 }}>
            <div className="section-head">
              <div className="section-title">Workspace Sections</div>
              <div className="micro-pill">Coming soon</div>
            </div>
            <p className="meta-text">
              Custom layout sections for your sidebar.
            </p>
          </section>
        </div>
        <div className="modal-footer" style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end' }}>
          <button className="small-button primary" onClick={onClose}>Done</button>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [theme, setTheme] = useState(
    localStorage.getItem("theme") === "dark" ? "dark" : "light"
  );
  const [authStatus, setAuthStatus] = useState("loading");
  const [currentUser, setCurrentUser] = useState(null);
  const [authMode, setAuthMode] = useState("signin");
  const [authForm, setAuthForm] = useState({ username: "", password: "" });
  const [authError, setAuthError] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  const [expandedAssessments, setExpandedAssessments] = useState(new Set());
  const [tags, setTags] = useState([]);
  const [notes, setNotes] = useState([]);
  const [metadata, setMetadata] = useState({});
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
  const [mobileTab, setMobileTab] = useState("chat");
  const [viewMode, setViewMode] = useState("workspace");
  const [showSettings, setShowSettings] = useState(false);

  const fileInputRef = useRef(null);
  const chatBodyRef = useRef(null);
  const seenCompletedJobsRef = useRef(new Set());
  const wasMobileRef = useRef(getViewportState().isMobile);

  function showError(message) {
    setErrorBanner(message);
  }

  function resetWorkspaceState() {
    setDocuments([]);
    setSelectedFiles(new Set());
    setTags([]);
    setNotes([]);
    setMetadata({});
    setChatMessages(initialMessages);
    setChatInput("");
    setIsSending(false);
    setUploadJobs([]);
    setSelectedDocument("");
    setTagDraft("");
    setNoteDraft("");
    setErrorBanner("");
    setFlashcardState({
      open: false,
      loading: false,
      error: "",
      data: null,
      side: "front",
      index: 0
    });
    setQuizState({
      open: false,
      loading: false,
      error: "",
      data: null,
      answers: {}
    });
    seenCompletedJobsRef.current = new Set();
  }

  function handleUnauthorized() {
    resetWorkspaceState();
    setCurrentUser(null);
    setAuthError("Your session has ended. Sign in again.");
    setAuthStatus("anonymous");
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
          setMobileTab("chat");
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
    let active = true;

    async function bootstrapSession() {
      try {
        const payload = await getCurrentUser();
        if (!active) {
          return;
        }
        if (payload.user) {
          setCurrentUser(payload.user);
          setAuthStatus("authenticated");
          setAuthError("");
        } else {
          resetWorkspaceState();
          setCurrentUser(null);
          setAuthStatus("anonymous");
        }
      } catch (_error) {
        if (!active) {
          return;
        }
        resetWorkspaceState();
        setCurrentUser(null);
        setAuthError("");
        setAuthStatus("anonymous");
      }
    }

    void bootstrapSession();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (authStatus !== "authenticated") {
      return undefined;
    }

    void loadTagsAndNotes();
    void loadDocumentsList();
    void loadUploadJobsList();
    void loadMetadata();

    const timerId = window.setInterval(() => {
      void loadUploadJobsList();
      // Only refresh metadata frequently while there are active upload jobs.
      if (uploadJobs.length > 0) {
        void loadMetadata();
      }
    }, 2000);

    return () => window.clearInterval(timerId);
  }, [authStatus, uploadJobs.length]);

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
    if (chatMessages.length <= 1) {
      return;
    }

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
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
      showError(error.message);
    }
  }

  async function loadMetadata() {
    try {
      const payload = await getMetadata();
      setMetadata(payload || {});
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
      console.error("Failed to load metadata:", error);
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
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
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
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
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
        if (isUnauthorizedError(error)) {
          handleUnauthorized();
          return;
        }
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
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
      showError(error.message);
    }
  }

  async function handleDeleteTag(tag) {
    try {
      await removeTag(tag);
      setTags((prev) => prev.filter((item) => item !== tag));
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
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
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
      showError(error.message);
    }
  }

  async function handleDeleteNote(noteId) {
    try {
      await removeNote(noteId);
      setNotes((prev) => prev.filter((note) => note.id !== noteId));
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
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
      await loadMetadata();
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
      showError(error.message);
    }
  }

  async function handleUpdateTag(filename, newTag) {
    try {
      await updateDocumentTag(filename, newTag);
      await loadDocumentsList();
      await loadTagsAndNotes(); // since adding a tag can create a new one
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
      showError(error.message);
    }
  }


  async function handleSendMessage() {
    const message = chatInput.trim();
    if (!message || isSending) {
      return;
    }

    const selected = Array.from(selectedFiles);
    const pendingAssistantId = crypto.randomUUID();

    setChatMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        type: "user",
        content: message,
        sources: []
      },
      {
        id: pendingAssistantId,
        type: "bot",
        content: "",
        sources: [],
        trace: null,
        status: "running"
      }
    ]);
    setChatInput("");
    setIsSending(true);
    setErrorBanner("");

    try {
      const payload = await sendChatMessage(message, selected);
      setChatMessages((prev) => [
        ...prev.map((entry) =>
          entry.id === pendingAssistantId
            ? {
                ...entry,
                content: payload.response,
                sources: dedupeSources(payload.sources),
                trace: payload.trace || null,
                status: "completed"
              }
            : entry
        )
      ]);
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
      setChatMessages((prev) => [
        ...prev.map((entry) =>
          entry.id === pendingAssistantId
            ? {
                ...entry,
                content: `Error: ${error.message}`,
                sources: [],
                trace: null,
                status: "failed"
              }
            : entry
        )
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
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
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
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
      setQuizState({
        open: true,
        loading: false,
        error: error.message,
        data: null,
        answers: {}
      });
    }
  }

  async function handleAuthSubmit() {
    const username = authForm.username.trim();
    const password = authForm.password;
    if (!username || !password || authBusy) {
      return;
    }

    setAuthBusy(true);
    setAuthError("");

    try {
      const payload =
        authMode === "signup"
          ? await signUp(username, password)
          : await signIn(username, password);

      resetWorkspaceState();
      setCurrentUser(payload.user || null);
      setAuthForm({ username: "", password: "" });
      setAuthStatus("authenticated");
    } catch (error) {
      setAuthError(error.message);
    } finally {
      setAuthBusy(false);
    }
  }

  async function handleLogout() {
    try {
      await signOut();
    } catch (_error) {
      // The local reset is still required if the server has already dropped the session.
    }

    resetWorkspaceState();
    setCurrentUser(null);
    setAuthForm({ username: "", password: "" });
    setAuthError("");
    setAuthStatus("anonymous");
  }

  const visibleUploadJobs = uploadJobs.filter((job) => {
    const isFinished = job.status === "completed" || job.status === "failed";
    if (!isFinished) {
      return true;
    }

    const completedAt = Date.parse(job.completed_at || job.updated_at || "");
    if (Number.isNaN(completedAt)) {
      // If we don't know when it finished, keep it for a bit based on current time
      return false; // Safest to hide if we don't have a valid time, or we could track local entry time
    }

    return Date.now() - completedAt < COMPLETED_UPLOAD_VISIBLE_MS;
  });

  const selectedDocumentNames = documents
    .filter((doc) => selectedFiles.has(doc.filename))
    .map((doc) => doc.filename);
  const hasStudioSelection = Boolean(selectedDocument);
  const isMobile = viewport.isMobile;
  const documentStatusLabel = isMobile
    ? `${documents.length} doc${documents.length === 1 ? "" : "s"}`
    : `${documents.length} doc${documents.length === 1 ? "" : "s"} loaded`;
  const frameStyle = isMobile
    ? undefined
    : {
      gridTemplateColumns: [
        leftSidebarOpen ? "minmax(280px, 320px)" : "86px",
        "minmax(0, 1fr)",
        rightSidebarOpen ? "minmax(280px, 320px)" : "86px"
      ].join(" ")
    };
  const mobileTabTitle =
    mobileTab === "sources" ? "Sources" : mobileTab === "studio" ? "Studio" : "Chat";

  function renderWorkspaceSections() {
    const groupedDocuments = {};
    groupedDocuments["Uncategorized"] = [];
    tags.forEach(tag => { groupedDocuments[tag] = []; });

    documents.forEach(doc => {
      const tag = doc.tag && tags.includes(doc.tag) ? doc.tag : "Uncategorized";
      if (!groupedDocuments[tag]) {
        groupedDocuments[tag] = [];
      }
      groupedDocuments[tag].push(doc);
    });

    const tagMetadata = {};
    Object.keys(groupedDocuments).forEach(tag => {
      tagMetadata[tag] = { assessments: [], deadlines: [], contacts: [] };
      groupedDocuments[tag].forEach(doc => {
        const docMeta = metadata[doc.filename];
        if (docMeta) {
          if (docMeta.assessments) tagMetadata[tag].assessments.push(...docMeta.assessments);
          if (docMeta.deadlines) tagMetadata[tag].deadlines.push(...docMeta.deadlines);
          if (docMeta.contacts) tagMetadata[tag].contacts.push(...docMeta.contacts);
        }
      });
    });

    return (
      <div className="sidebar-stack">
        <section className="section">
          <div className="section-head">
            <div className="section-title">Upload</div>
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

        {visibleUploadJobs.length > 0 && (
          <section className="section" style={{ marginTop: '16px' }}>
            <div className="section-head">
              <div className="section-title">Pipeline</div>
              <div className="helper-text">{visibleUploadJobs.length} live</div>
            </div>
            <div className="stack">
              {visibleUploadJobs.map((job) => (
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
              ))}
            </div>
          </section>
        )}

        <section className="section">
          <div className="section-head">
            <div className="section-title">Documents & Insights</div>
            <div className="helper-text">{documents.length} indexed</div>
          </div>
          <div className="stack">
            {documents.length ? (
              Object.entries(groupedDocuments)
                .filter(([tag, docs]) => docs.length > 0)
                .sort(([tagA], [tagB]) => {
                  if (tagA === "Uncategorized") return 1;
                  if (tagB === "Uncategorized") return -1;
                  return tagA.localeCompare(tagB);
                })
                .map(([tag, docs]) => {
                  const meta = tagMetadata[tag];
                  const hasInsights = meta && (meta.assessments.length > 0 || meta.contacts.length > 0);
                  const isAssessmentsExpanded = expandedAssessments.has(tag);

                  return (
                    <div key={tag} className="tag-group" style={{ marginBottom: '16px', background: 'var(--surface)', padding: '16px', borderRadius: '22px', border: '1px solid var(--border)' }}>
                      <div className="tag-group-header" style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <h3 style={{ margin: 0, fontSize: '1.05rem', color: 'var(--text)' }}>{tag}</h3>
                        <div className="micro-pill">{docs.length} file{docs.length === 1 ? '' : 's'}</div>
                      </div>

                      {hasInsights && (
                        <div className="tag-insights" style={{ marginBottom: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                          {meta.assessments.length > 0 && (
                            <div className="insight-group">
                              <div
                                className="insight-label"
                                style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                                onClick={() => {
                                  setExpandedAssessments(prev => {
                                    const next = new Set(prev);
                                    if (next.has(tag)) next.delete(tag);
                                    else next.add(tag);
                                    return next;
                                  });
                                }}
                              >
                                Assessments
                                <span style={{ fontSize: '0.8rem' }}>{isAssessmentsExpanded ? '▲' : '▼'}</span>
                              </div>
                              {isAssessmentsExpanded && (
                                <div className="stack">
                                  {meta.assessments.map((a, i) => (
                                    <div key={i} className="insight-item">
                                      <div className="insight-text">{a.item}</div>
                                      <div className="pill">{a.weight}</div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}

                          {meta.contacts.length > 0 && (
                            <div className="insight-group">
                              <div className="insight-label">Contacts</div>
                              <div className="stack">
                                {meta.contacts.map((c, i) => (
                                  <div key={i} className="insight-item">
                                    <div className="insight-text"><strong>{c.name}</strong> ({c.role})</div>
                                    <div className="meta-text">{c.email}</div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      <div className="stack">
                        {docs.map((doc) => (
                          <div key={doc.filename} className="document-item" style={{ background: 'var(--surface-strong)' }}>
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
                                  <select
                                    className="micro-pill"
                                    style={{ border: 'none', appearance: 'none', cursor: 'pointer', outline: 'none', paddingRight: '20px', background: 'rgba(255, 255, 255, 0.2) url("data:image/svg+xml;utf8,<svg fill=%27black%27 height=%2724%27 viewBox=%270 0 24 24%27 width=%2724%27 xmlns=%27http://www.w3.org/2000/svg%27><path d=%27M7 10l5 5 5-5z%27/><path d=%27M0 0h24v24H0z%27 fill=%27none%27/></svg>") no-repeat right 4px center/14px 14px', color: 'inherit' }}
                                    value={doc.tag && tags.includes(doc.tag) ? doc.tag : ""}
                                    onChange={(e) => {
                                      if (e.target.value !== (doc.tag || "")) {
                                        void handleUpdateTag(doc.filename, e.target.value);
                                      }
                                    }}
                                  >
                                    <option value="">Uncategorized</option>
                                    {tags.map(t => (
                                      <option key={t} value={t}>{t}</option>
                                    ))}
                                  </select>
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
                        ))}
                      </div>
                    </div>
                  );
                })
            ) : (
              <div className="empty-card">No documents yet. Start by dropping a file.</div>
            )}
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
    );
  }

  function renderStudioSections() {
    return (
      <div className="studio-stack">
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
        </section>

        <section className="section">
          <div className="section-title">Tools</div>
          <button className="studio-card audio-card" type="button" disabled>
            <div className="studio-card-icon">🎧</div>
            <div>
              <div className="studio-card-title">Audio recap</div>
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
            </div>
          </button>
        </section>
      </div>
    );
  }

  if (authStatus === "loading") {
    return (
      <div className="auth-shell auth-loading-shell">
        <div className="app-noise" />
        <div className="orb orb-one" />
        <div className="orb orb-two" />
        <div className="orb orb-three" />
        <div className="auth-loading">Loading your workspace...</div>
      </div>
    );
  }

  if (authStatus !== "authenticated") {
    return (
      <AuthScreen
        mode={authMode}
        form={authForm}
        busy={authBusy}
        error={authError}
        onChange={(field, value) => {
          setAuthForm((prev) => ({ ...prev, [field]: value }));
        }}
        onSubmit={() => void handleAuthSubmit()}
        onToggleMode={() => {
          setAuthError("");
          setAuthMode((prev) => (prev === "signin" ? "signup" : "signin"));
        }}
      />
    );
  }

  // Prepare calendar events
  const allTopics = Array.from(new Set([...tags, "Uncategorized"]));
  const calendarEvents = [];
  documents.forEach(doc => {
    const docMeta = metadata[doc.filename];
    const topic = doc.tag && tags.includes(doc.tag) ? doc.tag : "Uncategorized";
    if (docMeta && docMeta.deadlines) {
      docMeta.deadlines.forEach(d => {
        if (d.date && d.event) {
          calendarEvents.push({
            title: d.event,
            date: d.date,
            topic: topic
          });
        }
      });
    }
  });

  return (
    <div className="app-shell">
      <div className="app-noise" />
      <div className="orb orb-one" />
      <div className="orb orb-two" />
      <div className="orb orb-three" />

      <div className="app-topbar">
        <div className="topbar-brand">
          <div className="brand-mark" style={{ background: 'transparent', color: 'var(--accent)', padding: 0, width: 'auto', height: 'auto', display: 'flex', alignItems: 'center' }}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
            </svg>
          </div>
          <div className="topbar-copy">
            <span className="eyebrow" style={{ fontSize: '1.15rem', fontWeight: 600, letterSpacing: '-0.02em', color: 'var(--text)' }}>Study Space</span>
            {isMobile ? <span className="topbar-mobile-context">{mobileTabTitle}</span> : null}
          </div>
        </div>
        <div className="topbar-actions">
          {isMobile ? null : (
            <>
              <div className="status-chip docs-chip pulse">
                {documentStatusLabel}
              </div>
              <div className="status-chip user-chip">
                @{currentUser?.username}
              </div>
            </>
          )}
          <button className="small-button" type="button" onClick={() => setViewMode(viewMode === "workspace" ? "calendar" : "workspace")}>
            {viewMode === "workspace" ? "Calendar" : "Workspace"}
          </button>
          <button className="small-button" type="button" onClick={() => setShowSettings(true)}>
            Settings
          </button>
          <button className="small-button" type="button" onClick={() => void handleLogout()}>
            {isMobile ? "Exit" : "Log out"}
          </button>
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

      {viewMode === "workspace" ? (
        <div className="app-frame" style={frameStyle}>
          {isMobile ? (
            <main
              className={`panel glass-panel mobile-main-shell mobile-tab-${mobileTab} ${mobileTab === "chat" ? "mobile-chat-shell" : "mobile-panel-screen"}`}
            >
              {mobileTab === "sources" ? (
                <>
                  <div className="panel-header mobile-panel-header">
                    <div className="panel-heading">
                      <div className="panel-title">Sources</div>
                      <div className="header-subtitle">
                        Upload material, scope documents, and capture notes.
                      </div>
                    </div>
                  </div>
                  <div className="panel-body left-body mobile-panel-body">
                    {renderWorkspaceSections()}
                  </div>
                </>
              ) : null}

              {mobileTab === "chat" ? (
                <>
                  <div className="chat-body" ref={chatBodyRef}>
                    {errorBanner ? <div className="banner error-text">{errorBanner}</div> : null}
                    {chatMessages.map((message) => (
                      <ChatMessageCard key={message.id} message={message} />
                    ))}
                  </div>

                  <div className="chat-footer mobile-chat-footer">
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
                    </div>
                  </div>
                </>
              ) : null}

              {mobileTab === "studio" ? (
                <>
                  <div className="panel-header mobile-panel-header">
                    <div className="panel-heading">
                      <div className="panel-title">Studio</div>
                      <div className="header-subtitle">
                        Pick a source and launch active study tools.
                      </div>
                    </div>
                  </div>
                  <div className="panel-body right-body mobile-panel-body">
                    {renderStudioSections()}
                  </div>
                </>
              ) : null}
            </main>
          ) : (
            <>
              <aside
                className={`side-panel left-panel ${leftSidebarOpen ? "open" : "collapsed"}`}
              >
                <div className="panel glass-panel">
                  <div className="panel-header" style={{ display: 'flex', alignItems: 'center', justifyContent: leftSidebarOpen ? 'space-between' : 'center' }}>
                    {leftSidebarOpen && <div className="panel-title" style={{ margin: 0 }}>Workspace</div>}
                    <SidebarToggle
                      side="left"
                      open={leftSidebarOpen}
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
                    {renderWorkspaceSections()}
                  </div>
                </div>
              </aside>

              <main className="panel chat-panel glass-panel">
                <div className="chat-header">
                  <div className="chat-header-row">
                    <div className="panel-title" style={{ margin: 0 }}>Chat</div>
                  </div>
                  {errorBanner ? <div className="banner error-text">{errorBanner}</div> : null}
                </div>

                <div className="chat-body" ref={chatBodyRef}>
                  {chatMessages.length === 0 ? (
                    <section className="chat-hero">
                      <div className="chat-hero-copy">
                        <div className="chat-hero-badge">Hot desk</div>
                        <h2>Ask a question</h2>
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
                    <ChatMessageCard key={message.id} message={message} />
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
                  </div>
                </div>
              </main>

              <aside
                className={`side-panel right-panel ${rightSidebarOpen ? "open" : "collapsed"}`}
              >
                <div className="panel glass-panel">
                  <div className="panel-header" style={{ display: 'flex', alignItems: 'center', justifyContent: rightSidebarOpen ? 'space-between' : 'center' }}>
                    {rightSidebarOpen && <div className="panel-title" style={{ margin: 0 }}>Studio</div>}
                    <SidebarToggle
                      side="right"
                      open={rightSidebarOpen}
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
                    {renderStudioSections()}
                  </div>
                </div>
              </aside>
            </>
          )}
        </div>
      ) : (
        <div className="app-frame" style={{ display: 'flex', overflow: 'hidden', padding: 0 }}>
          <Calendar events={calendarEvents} topics={allTopics} />
        </div>
      )}

      {isMobile && viewMode === "workspace" ? (
        <div className="mobile-tabbar-wrap">
          <nav className="mobile-tabbar" aria-label="Mobile workspace">
            <button
              className={`mobile-tab ${mobileTab === "sources" ? "active" : ""}`}
              type="button"
              onClick={() => setMobileTab("sources")}
            >
              <span className="mobile-tab-icon">☰</span>
              <span>Sources</span>
            </button>
            <button
              className={`mobile-tab ${mobileTab === "chat" ? "active" : ""}`}
              type="button"
              onClick={() => setMobileTab("chat")}
            >
              <span className="mobile-tab-icon">✦</span>
              <span>Chat</span>
            </button>
            <button
              className={`mobile-tab ${mobileTab === "studio" ? "active" : ""}`}
              type="button"
              onClick={() => setMobileTab("studio")}
            >
              <span className="mobile-tab-icon">◌</span>
              <span>Studio</span>
            </button>
          </nav>
        </div>
      ) : null}

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

      {showSettings ? (
        <SettingsModal
          onClose={() => setShowSettings(false)}
          tags={tags}
          tagDraft={tagDraft}
          onTagDraftChange={(val) => setTagDraft(val)}
          onAddTag={() => void handleAddTag()}
          onDeleteTag={(tag) => void handleDeleteTag(tag)}
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
