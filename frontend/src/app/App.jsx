import { useCallback, useEffect, useRef, useState } from "react";

import Calendar from "../Calendar";
import TopicMinerWorkspace from "../TopicMinerWorkspace";
import LandingPage from "../LandingPage";
import AuthScreen from "../AuthScreen";
import {
  createNote,
  createTag,
  deleteAccount,
  deleteDocument,
  exportAccountData,
  generateStudySet,
  getCurrentUser,
  getDocuments,
  getMetadata,
  getNotes,
  getStudySet,
  getStudySets,
  getTags,
  getUploadConfig,
  getUploadJobs,
  signIn,
  signOut,
  signUp,
  removeNote,
  removeMetadataEntry,
  removeStudySet,
  removeTag,
  sendChatMessage,
  uploadDocument,
  updateDocumentTag,
} from "../api";
import VisuallyHidden from "./components/VisuallyHidden";
import ChatMessageCard from "./components/chat/ChatMessageCard";
import SettingsModal from "./components/modals/SettingsModal";
import StudySetPracticeModal from "./components/modals/StudySetPracticeModal";
import SidebarToggle from "./components/layout/SidebarToggle";
import PrivacyNoticeScreen from "./screens/PrivacyNoticeScreen";
import StudioSections from "./sections/StudioSections";
import WorkspaceSections from "./sections/WorkspaceSections";
import {
  ACCESSIBILITY_STORAGE_KEY,
  COMPLETED_UPLOAD_VISIBLE_MS,
  initialMessages,
  starterQuestions,
} from "./constants";
import {
  autoResize,
  dedupeSources,
  getAccessibilitySettings,
  getSpeechErrorMessage,
  getSpeechRecognitionConstructor,
  getStudySetCount,
  getStudySetLabel,
  getViewportState,
  getVoiceInputAvailability,
  isUnauthorizedError,
  normalizeDocument,
} from "./utils";

export default function App() {
  const [showLanding, setShowLanding] = useState(!window.location.hash || window.location.hash === "#" ? true : false);
  const [theme, setTheme] = useState(
    localStorage.getItem("theme") ? localStorage.getItem("theme") : "dark"
  );
  const [authStatus, setAuthStatus] = useState("loading");
  const [currentUser, setCurrentUser] = useState(null);

  const initialHash = window.location.hash;
  const [currentHash, setCurrentHash] = useState(initialHash);
  const [authMode, setAuthMode] = useState(initialHash === "#signup" ? "signup" : "signin");

  const [authForm, setAuthForm] = useState({ username: "", password: "" });
  const [authError, setAuthError] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  const [tags, setTags] = useState([]);
  const [notes, setNotes] = useState([]);
  const [metadata, setMetadata] = useState({});
  const [chatMessages, setChatMessages] = useState(initialMessages);
  const [chatInput, setChatInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadJobs, setUploadJobs] = useState([]);
  const [uploadAccept, setUploadAccept] = useState("");
  const [selectedDocument, setSelectedDocument] = useState("");
  const [studySets, setStudySets] = useState([]);
  const [studySetType, setStudySetType] = useState("mcq_quiz");
  const [studySetDifficulty, setStudySetDifficulty] = useState("Medium");
  const [studySetState, setStudySetState] = useState({
    open: false,
    loading: false,
    error: "",
    data: null,
    index: 0,
    side: "front",
    answers: {},
    writtenDrafts: {},
    revealed: {},
  });
  const [flashcardState, setFlashcardState] = useState({
    open: false,
    loading: false,
    error: "",
    data: null,
    side: "front",
    index: 0,
  });
  const [quizState, setQuizState] = useState({
    open: false,
    loading: false,
    error: "",
    data: null,
    answers: {},
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
  const [accountExportBusy, setAccountExportBusy] = useState(false);
  const [accountDeleteBusy, setAccountDeleteBusy] = useState(false);
  const [accountDeleteForm, setAccountDeleteForm] = useState({ username: "", password: "" });
  const [accessibility, setAccessibility] = useState(getAccessibilitySettings);
  const [liveRegionMessage, setLiveRegionMessage] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [speechError, setSpeechError] = useState("");
  const fileInputRef = useRef(null);
  const chatBodyRef = useRef(null);
  const seenCompletedJobsRef = useRef(new Set());
  const wasMobileRef = useRef(getViewportState().isMobile);
  const speechRecognitionRef = useRef(null);
  const speechBaseInputRef = useRef("");
  const speechCommittedTextRef = useRef("");

  const showError = useCallback((message) => {
    setErrorBanner(message);
  }, []);

  function announce(message) {
    if (!message || !accessibility.announceUpdates) {
      return;
    }

    setLiveRegionMessage("");
    window.setTimeout(() => {
      setLiveRegionMessage(message);
    }, 40);
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
    setStudySets([]);
    setStudySetType("mcq_quiz");
    setStudySetDifficulty("Medium");
    setStudySetState({
      open: false,
      loading: false,
      error: "",
      data: null,
      index: 0,
      side: "front",
      answers: {},
      writtenDrafts: {},
      revealed: {},
    });
    setTagDraft("");
    setNoteDraft("");
    setErrorBanner("");
    setSpeechError("");
    setLiveRegionMessage("");
    setIsListening(false);
    speechRecognitionRef.current?.stop();
    setFlashcardState({
      open: false,
      loading: false,
      error: "",
      data: null,
      side: "front",
      index: 0,
    });
    setQuizState({
      open: false,
      loading: false,
      error: "",
      data: null,
      answers: {},
    });
    seenCompletedJobsRef.current = new Set();
    setShowSettings(false);
    setAccountDeleteBusy(false);
    setAccountExportBusy(false);
    setAccountDeleteForm({ username: "", password: "" });
  }

  function handleUnauthorized() {
    resetWorkspaceState();
    setCurrentUser(null);
    setAuthError("Your session has ended. Sign in again.");
    setAuthStatus("anonymous");
  }

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash;
      setCurrentHash(hash);
      if (hash === "#login") {
        setShowLanding(false);
        setAuthMode("signin");
        setAuthError("");
      } else if (hash === "#signup") {
        setShowLanding(false);
        setAuthMode("signup");
        setAuthError("");
      } else if (hash === "#privacy") {
        setShowLanding(false);
        setAuthError("");
      } else if (hash === "" || hash === "#") {
        setShowLanding(true);
        setAuthError("");
      }
    };

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  useEffect(() => {
    document.body.classList.toggle("dark-mode", theme === "dark");
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    document.body.classList.toggle("a11y-enhanced-focus", accessibility.enhancedFocus);
    document.body.classList.toggle("a11y-larger-text", accessibility.largerText);
    document.body.classList.toggle("a11y-high-contrast", accessibility.highContrast);
    document.body.classList.toggle("a11y-reduced-motion", accessibility.reducedMotion);
    window.localStorage.setItem(ACCESSIBILITY_STORAGE_KEY, JSON.stringify(accessibility));
  }, [accessibility]);

  useEffect(() => {
    return () => {
      if (speechRecognitionRef.current) {
        speechRecognitionRef.current.stop();
      }
    };
  }, []);

  useEffect(() => {
    if (!accessibility.voiceInput && speechRecognitionRef.current) {
      speechRecognitionRef.current.stop();
      setIsListening(false);
      setSpeechError("");
    }
  }, [accessibility.voiceInput]);

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
    void loadUploadConfig();
    void loadMetadata();
    void loadStudySets();

    const timerId = window.setInterval(() => {
      void loadUploadJobsList();
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

  async function loadStudySets() {
    try {
      const payload = await getStudySets();
      setStudySets(Array.isArray(payload.study_sets) ? payload.study_sets : []);
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
      showError(error.message);
    }
  }

  async function loadUploadConfig() {
    try {
      const payload = await getUploadConfig();
      setUploadAccept(typeof payload.accept === "string" ? payload.accept : "");
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
      console.error("Failed to load upload config:", error);
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
          announce(`Upload complete for ${job.filename}.`);
        } else if (job.status === "failed" && !seenCompletedJobsRef.current.has(job.job_id)) {
          seenCompletedJobsRef.current.add(job.job_id);
          announce(`Upload failed for ${job.filename}.`);
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

  async function handleUpload(files, folderId = null) {
    const fileList = Array.from(files || []);
    if (!fileList.length) {
      return;
    }

    setErrorBanner("");

    for (const file of fileList) {
      try {
        await uploadDocument(file, folderId);
        announce(`Started upload for ${file.name}.`);
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
      announce(`Added topic ${value}.`);
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
      announce(`Removed topic ${tag}.`);
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
      announce("Note saved.");
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
      announce("Note deleted.");
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
      announce(`Deleted ${filename}.`);
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
      showError(error.message);
    }
  }

  async function handleDeleteMetadataEntry(filename, section, index) {
    try {
      const payload = await removeMetadataEntry(filename, section, index);
      setMetadata((prev) => ({
        ...prev,
        [filename]: payload.metadata || {},
      }));
      announce(`Removed ${section.slice(0, -1)} metadata from ${filename}.`);
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
      await loadTagsAndNotes();
      announce(`Updated topic for ${filename}.`);
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

    if (speechRecognitionRef.current) {
      speechRecognitionRef.current.stop();
      setIsListening(false);
    }

    const selected = Array.from(selectedFiles);
    const pendingAssistantId = crypto.randomUUID();

    setChatMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        type: "user",
        content: message,
        sources: [],
      },
      {
        id: pendingAssistantId,
        type: "bot",
        content: "",
        sources: [],
        trace: null,
        status: "running",
      },
    ]);
    setChatInput("");
    setIsSending(true);
    setErrorBanner("");
    announce("Sending question to Study Space.");

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
                status: "completed",
              }
            : entry
        ),
      ]);
      announce("Answer ready.");
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
                status: "failed",
              }
            : entry
        ),
      ]);
      announce("Chat request failed.");
    } finally {
      setIsSending(false);
    }
  }

  function handleToggleAccessibility(key) {
    setAccessibility((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  }

  function toggleVoiceInput() {
    if (isListening) {
      speechRecognitionRef.current?.stop();
      setIsListening(false);
      announce("Voice input stopped.");
      return;
    }

    const availability = getVoiceInputAvailability();
    if (!availability.supported) {
      const message = availability.reason;
      setSpeechError(message);
      announce(message);
      return;
    }

    try {
      const SpeechRecognition = getSpeechRecognitionConstructor();
      const recognition = new SpeechRecognition();
      recognition.lang = "en-US";
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        setSpeechError("");
        setIsListening(true);
        speechBaseInputRef.current = chatInput.trim();
        speechCommittedTextRef.current = "";
        announce("Voice input started.");
      };

      recognition.onerror = (event) => {
        const message = getSpeechErrorMessage(event.error);
        setSpeechError(message);
        setIsListening(false);
        announce(message);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognition.onresult = (event) => {
        let interimTranscript = "";
        let committedText = speechCommittedTextRef.current;

        for (let index = event.resultIndex; index < event.results.length; index += 1) {
          const result = event.results[index];
          const transcript = result[0]?.transcript?.trim() || "";

          if (!transcript) {
            continue;
          }

          if (result.isFinal) {
            committedText = [committedText, transcript].filter(Boolean).join(" ").trim();
          } else {
            interimTranscript = [interimTranscript, transcript].filter(Boolean).join(" ").trim();
          }
        }

        speechCommittedTextRef.current = committedText;
        setChatInput(
          [speechBaseInputRef.current, committedText, interimTranscript].filter(Boolean).join(" ").trim()
        );
      };

      speechRecognitionRef.current = recognition;
      recognition.start();
    } catch (error) {
      speechRecognitionRef.current = null;
      setIsListening(false);
      const message = error?.name
        ? getSpeechErrorMessage(error.name)
        : "Voice input could not be started in this browser.";
      setSpeechError(message);
      announce(message);
    }
  }

  async function handleGenerateStudySet() {
    if (!selectedDocument) {
      return;
    }

    const label = getStudySetLabel(studySetType);
    announce(`Generating ${label} for ${selectedDocument}.`);

    setStudySetState({
      open: true,
      loading: true,
      error: "",
      data: null,
      index: 0,
      side: "front",
      answers: {},
      writtenDrafts: {},
      revealed: {},
    });

    try {
      const payload = await generateStudySet({
        filename: selectedDocument,
        type: studySetType,
        numItems: getStudySetCount(studySetType),
        difficulty: studySetDifficulty,
      });
      setStudySets((prev) => [payload, ...prev.filter((item) => item.id !== payload.id)]);
      setStudySetState({
        open: true,
        loading: false,
        error: "",
        data: payload,
        index: 0,
        side: "front",
        answers: {},
        writtenDrafts: {},
        revealed: {},
      });
      announce(`${label} saved and ready.`);
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
      setStudySetState({
        open: true,
        loading: false,
        error: error.message,
        data: null,
        index: 0,
        side: "front",
        answers: {},
        writtenDrafts: {},
        revealed: {},
      });
      announce("Study set generation failed.");
    }
  }

  async function handleOpenStudySet(studySetId) {
    try {
      const payload = await getStudySet(studySetId);
      setStudySetState({
        open: true,
        loading: false,
        error: "",
        data: payload,
        index: 0,
        side: "front",
        answers: {},
        writtenDrafts: {},
        revealed: {},
      });
      announce(`${payload.title || "Study set"} opened.`);
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
      showError(error.message);
    }
  }

  async function handleDeleteStudySet(studySetId) {
    const target = studySets.find((item) => item.id === studySetId);
    const title = target?.title || "this study set";
    if (!window.confirm(`Delete ${title}?`)) {
      return;
    }

    try {
      await removeStudySet(studySetId);
      setStudySets((prev) => prev.filter((item) => item.id !== studySetId));
      if (studySetState.data?.id === studySetId) {
        setStudySetState({
          open: false,
          loading: false,
          error: "",
          data: null,
          index: 0,
          side: "front",
          answers: {},
          writtenDrafts: {},
          revealed: {},
        });
      }
      announce("Study set deleted.");
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
      showError(error.message);
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

  async function handleExportAccount() {
    if (accountExportBusy) {
      return;
    }

    try {
      setAccountExportBusy(true);
      const blob = await exportAccountData();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `studyspace-export-${currentUser?.username || "account"}.zip`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => window.URL.revokeObjectURL(url), 1000);
      announce("Your account export has started downloading.");
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
      showError(error.message);
    } finally {
      setAccountExportBusy(false);
    }
  }

  async function handleDeleteAccount() {
    const username = accountDeleteForm.username.trim();
    const password = accountDeleteForm.password;

    if (!username || !password || accountDeleteBusy) {
      return;
    }

    if (!window.confirm("Delete your account permanently? This removes your files, notes, and metadata immediately.")) {
      return;
    }

    try {
      setAccountDeleteBusy(true);
      await deleteAccount(username, password);
      resetWorkspaceState();
      setCurrentUser(null);
      setAuthForm({ username: "", password: "" });
      setAuthError("");
      setAuthStatus("anonymous");
      window.location.hash = "login";
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleUnauthorized();
        return;
      }
      showError(error.message);
    } finally {
      setAccountDeleteBusy(false);
    }
  }

  function openPrivacyNotice() {
    setShowSettings(false);
    window.location.hash = "privacy";
  }

  function closePrivacyNotice() {
    if (authStatus === "authenticated") {
      window.location.hash = "";
      return;
    }
    window.location.hash = authMode === "signup" ? "signup" : "login";
  }

  const visibleUploadJobs = uploadJobs.filter((job) => {
    const isFinished = job.status === "completed" || job.status === "failed";
    if (!isFinished) {
      return true;
    }

    const completedAt = Date.parse(job.completed_at || job.updated_at || "");
    if (Number.isNaN(completedAt)) {
      return false;
    }

    return Date.now() - completedAt < COMPLETED_UPLOAD_VISIBLE_MS;
  });

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
          rightSidebarOpen ? "minmax(280px, 320px)" : "86px",
        ].join(" "),
      };
  const mobileTabTitle =
    viewMode === "topic-miner"
      ? "Topic Miner"
      : mobileTab === "sources"
        ? "Sources"
        : mobileTab === "studio"
          ? "Studio"
          : "Chat";
  const voiceInputStatus = getVoiceInputAvailability();

  if (currentHash === "#privacy") {
    return (
      <PrivacyNoticeScreen
        authenticated={authStatus === "authenticated"}
        username={currentUser?.username}
        onClose={closePrivacyNotice}
      />
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
    if (showLanding) {
      return (
        <LandingPage
          onLogin={() => {
            window.location.hash = "login";
          }}
          onSignUp={() => {
            window.location.hash = "signup";
          }}
        />
      );
    }
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
          window.location.hash = authMode === "signin" ? "signup" : "login";
        }}
        onOpenPrivacyNotice={openPrivacyNotice}
      />
    );
  }

  const allTopics = Array.from(new Set([...tags, "Uncategorized"]));
  const calendarEvents = [];
  documents.forEach((doc) => {
    const docMeta = metadata[doc.filename];
    const topic = doc.tag && tags.includes(doc.tag) ? doc.tag : "Uncategorized";
    if (docMeta && docMeta.deadlines) {
      docMeta.deadlines.forEach((deadline) => {
        if (deadline.date && deadline.event) {
          calendarEvents.push({
            title: deadline.event,
            date: deadline.date,
            topic,
          });
        }
      });
    }
  });

  return (
    <div className="app-shell">
      <a className="skip-link" href="#primary-content">Skip to main content</a>
      <VisuallyHidden as="div" aria-live="polite" aria-atomic="true">
        {liveRegionMessage}
      </VisuallyHidden>
      <div className="app-noise" />
      <div className="orb orb-one" />
      <div className="orb orb-two" />
      <div className="orb orb-three" />

      <header className="app-topbar">
        <div className="topbar-brand">
          <div className="topbar-copy">
            <span className="eyebrow" style={{ fontSize: "1.15rem", fontWeight: 600, letterSpacing: "-0.02em", color: "var(--text)" }}>Study Space</span>
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
          <button
            className="small-button"
            type="button"
            onClick={() => setViewMode(viewMode === "calendar" ? "workspace" : "calendar")}
          >
            {viewMode === "calendar" ? "Workspace" : "Calendar"}
          </button>
          <button
            className="small-button"
            type="button"
            onClick={() => setViewMode(viewMode === "topic-miner" ? "workspace" : "topic-miner")}
          >
            {viewMode === "topic-miner" ? "Workspace" : "Topic Miner"}
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
            aria-pressed={theme === "dark"}
          >
            {theme === "dark" ? "☀" : "☾"}
          </button>
        </div>
      </header>

      {viewMode === "workspace" ? (
        <div id="primary-content" className="app-frame" style={frameStyle}>
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
                    <WorkspaceSections
                      isDragOver={isDragOver}
                      setIsDragOver={setIsDragOver}
                      fileInputRef={fileInputRef}
                      uploadAccept={uploadAccept}
                      handleUpload={handleUpload}
                      visibleUploadJobs={visibleUploadJobs}
                      documents={documents}
                      tags={tags}
                      metadata={metadata}
                      selectedFiles={selectedFiles}
                      setSelectedFiles={setSelectedFiles}
                      handleUpdateTag={handleUpdateTag}
                      handleDeleteMetadataEntry={handleDeleteMetadataEntry}
                      handleDeleteDocument={handleDeleteDocument}
                      notes={notes}
                      noteDraft={noteDraft}
                      setNoteDraft={setNoteDraft}
                      handleAddNote={handleAddNote}
                      handleDeleteNote={handleDeleteNote}
                    />
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
                          aria-label="Ask a question about your study material"
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
                          aria-label="Send question"
                        >
                          ➜
                        </button>
                        {accessibility.voiceInput && voiceInputStatus.supported ? (
                          <button
                            className={`send-button voice-button ${isListening ? "listening" : ""}`}
                            type="button"
                            onClick={toggleVoiceInput}
                            aria-pressed={isListening}
                            aria-label={isListening ? "Stop voice input" : "Start voice input"}
                          >
                            {isListening ? "■" : "🎙"}
                          </button>
                        ) : null}
                      </div>
                    </div>
                    {speechError ? <div className="banner error-text">{speechError}</div> : null}
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
                    <StudioSections
                      selectedDocument={selectedDocument}
                      setSelectedDocument={setSelectedDocument}
                      documents={documents}
                      studySetType={studySetType}
                      setStudySetType={setStudySetType}
                      studySetDifficulty={studySetDifficulty}
                      setStudySetDifficulty={setStudySetDifficulty}
                      hasStudioSelection={hasStudioSelection}
                      handleGenerateStudySet={handleGenerateStudySet}
                      studySets={studySets}
                      handleOpenStudySet={handleOpenStudySet}
                      handleDeleteStudySet={handleDeleteStudySet}
                      onOpenTopicMiner={() => setViewMode("topic-miner")}
                    />
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
                  <div className="panel-header" style={{ display: "flex", alignItems: "center", justifyContent: leftSidebarOpen ? "space-between" : "center" }}>
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
                    <WorkspaceSections
                      isDragOver={isDragOver}
                      setIsDragOver={setIsDragOver}
                      fileInputRef={fileInputRef}
                      uploadAccept={uploadAccept}
                      handleUpload={handleUpload}
                      visibleUploadJobs={visibleUploadJobs}
                      documents={documents}
                      tags={tags}
                      metadata={metadata}
                      selectedFiles={selectedFiles}
                      setSelectedFiles={setSelectedFiles}
                      handleUpdateTag={handleUpdateTag}
                      handleDeleteMetadataEntry={handleDeleteMetadataEntry}
                      handleDeleteDocument={handleDeleteDocument}
                      notes={notes}
                      noteDraft={noteDraft}
                      setNoteDraft={setNoteDraft}
                      handleAddNote={handleAddNote}
                      handleDeleteNote={handleDeleteNote}
                    />
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
                        aria-label="Ask a question about your study material"
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
                        aria-label="Send question"
                      >
                        ➜
                      </button>
                      {accessibility.voiceInput && voiceInputStatus.supported ? (
                        <button
                          className={`send-button voice-button ${isListening ? "listening" : ""}`}
                          type="button"
                          onClick={toggleVoiceInput}
                          aria-pressed={isListening}
                          aria-label={isListening ? "Stop voice input" : "Start voice input"}
                        >
                          {isListening ? "■" : "🎙"}
                        </button>
                      ) : null}
                    </div>
                  </div>
                  {speechError ? <div className="banner error-text">{speechError}</div> : null}
                </div>
              </main>

              <aside
                className={`side-panel right-panel ${rightSidebarOpen ? "open" : "collapsed"}`}
              >
                <div className="panel glass-panel">
                  <div className="panel-header" style={{ display: "flex", alignItems: "center", justifyContent: rightSidebarOpen ? "space-between" : "center" }}>
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
                    <StudioSections
                      selectedDocument={selectedDocument}
                      setSelectedDocument={setSelectedDocument}
                      documents={documents}
                      studySetType={studySetType}
                      setStudySetType={setStudySetType}
                      studySetDifficulty={studySetDifficulty}
                      setStudySetDifficulty={setStudySetDifficulty}
                      hasStudioSelection={hasStudioSelection}
                      handleGenerateStudySet={handleGenerateStudySet}
                      studySets={studySets}
                      handleOpenStudySet={handleOpenStudySet}
                      handleDeleteStudySet={handleDeleteStudySet}
                      onOpenTopicMiner={() => setViewMode("topic-miner")}
                    />
                  </div>
                </div>
              </aside>
            </>
          )}
        </div>
      ) : viewMode === "calendar" ? (
        <div id="primary-content" className="app-frame" style={{ display: "flex", overflow: "hidden", padding: 0 }}>
          <Calendar events={calendarEvents} topics={allTopics} accessibility={accessibility} />
        </div>
      ) : (
        <div id="primary-content" className="app-frame workspace-view topic-miner-view">
          <TopicMinerWorkspace
            onError={showError}
            fullScreen
            onCloseWorkspace={() => setViewMode("workspace")}
          />
        </div>
      )}

      {isMobile && viewMode === "workspace" ? (
        <div className="mobile-tabbar-wrap">
          <nav className="mobile-tabbar" aria-label="Mobile workspace">
            <button
              className={`mobile-tab ${mobileTab === "sources" ? "active" : ""}`}
              type="button"
              onClick={() => setMobileTab("sources")}
              aria-pressed={mobileTab === "sources"}
            >
              <span className="mobile-tab-icon">☰</span>
              <span>Sources</span>
            </button>
            <button
              className={`mobile-tab ${mobileTab === "chat" ? "active" : ""}`}
              type="button"
              onClick={() => setMobileTab("chat")}
              aria-pressed={mobileTab === "chat"}
            >
              <span className="mobile-tab-icon">✦</span>
              <span>Chat</span>
            </button>
            <button
              className={`mobile-tab ${mobileTab === "studio" ? "active" : ""}`}
              type="button"
              onClick={() => setMobileTab("studio")}
              aria-pressed={mobileTab === "studio"}
            >
              <span className="mobile-tab-icon">◌</span>
              <span>Studio</span>
            </button>
          </nav>
        </div>
      ) : null}

      {studySetState.open ? (
        <StudySetPracticeModal
          state={studySetState}
          onClose={() =>
            setStudySetState({
              open: false,
              loading: false,
              error: "",
              data: null,
              index: 0,
              side: "front",
              answers: {},
              writtenDrafts: {},
              revealed: {},
            })
          }
          onFlip={() =>
            setStudySetState((prev) => ({
              ...prev,
              side: prev.side === "front" ? "back" : "front",
            }))
          }
          onPrev={() =>
            setStudySetState((prev) => ({
              ...prev,
              index: Math.max(0, prev.index - 1),
              side: "front",
            }))
          }
          onNext={() =>
            setStudySetState((prev) => ({
              ...prev,
              index: Math.min((prev.data?.items?.length || 1) - 1, prev.index + 1),
              side: "front",
            }))
          }
          onAnswer={(itemIndex, selectedOption) =>
            setStudySetState((prev) => ({
              ...prev,
              answers: {
                ...prev.answers,
                [itemIndex]: selectedOption,
              },
            }))
          }
          onWrittenChange={(itemIndex, value) =>
            setStudySetState((prev) => ({
              ...prev,
              writtenDrafts: {
                ...prev.writtenDrafts,
                [itemIndex]: value,
              },
            }))
          }
          onReveal={(itemIndex) =>
            setStudySetState((prev) => ({
              ...prev,
              revealed: {
                ...prev.revealed,
                [itemIndex]: !prev.revealed[itemIndex],
              },
            }))
          }
        />
      ) : null}

      {showSettings ? (
        <SettingsModal
          onClose={() => setShowSettings(false)}
          onOpenPrivacyNotice={openPrivacyNotice}
          onExportAccount={handleExportAccount}
          onDeleteAccount={handleDeleteAccount}
          tags={tags}
          tagDraft={tagDraft}
          onTagDraftChange={(val) => setTagDraft(val)}
          onAddTag={() => void handleAddTag()}
          onDeleteTag={(tag) => void handleDeleteTag(tag)}
          accessibility={accessibility}
          onToggleAccessibility={handleToggleAccessibility}
          voiceInputStatus={voiceInputStatus}
          currentUsername={currentUser?.username || ""}
          exportBusy={accountExportBusy}
          deleteBusy={accountDeleteBusy}
          deleteState={accountDeleteForm}
          onDeleteStateChange={(field, value) => {
            setAccountDeleteForm((prev) => ({ ...prev, [field]: value }));
          }}
        />
      ) : null}
    </div>
  );
}
