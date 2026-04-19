import {
  ACCESSIBILITY_STORAGE_KEY,
  DEFAULT_ACCESSIBILITY_SETTINGS,
  MOBILE_BREAKPOINT,
  STUDY_SET_TYPE_LABELS,
  STUDY_SET_TYPES,
} from "./constants";

export function getAccessibilitySettings() {
  if (typeof window === "undefined") {
    return DEFAULT_ACCESSIBILITY_SETTINGS;
  }

  try {
    const raw = window.localStorage.getItem(ACCESSIBILITY_STORAGE_KEY);
    if (!raw) {
      return DEFAULT_ACCESSIBILITY_SETTINGS;
    }

    return {
      ...DEFAULT_ACCESSIBILITY_SETTINGS,
      ...JSON.parse(raw),
    };
  } catch (_error) {
    return DEFAULT_ACCESSIBILITY_SETTINGS;
  }
}

export function getSpeechRecognitionConstructor() {
  if (typeof window === "undefined") {
    return null;
  }

  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

export function getVoiceInputAvailability() {
  const SpeechRecognition = getSpeechRecognitionConstructor();

  if (!SpeechRecognition) {
    return {
      supported: false,
      reason: "This browser does not provide built-in speech recognition.",
    };
  }

  if (typeof window !== "undefined" && !window.isSecureContext) {
    return {
      supported: false,
      reason: "Voice input requires a secure context such as localhost or HTTPS.",
    };
  }

  if (typeof navigator !== "undefined" && navigator.onLine === false) {
    return {
      supported: false,
      reason: "Voice input needs an internet connection for browser speech recognition.",
    };
  }

  return {
    supported: true,
    reason: "",
  };
}

export function getSpeechErrorMessage(errorCode) {
  switch (errorCode) {
    case "network":
      return "Voice input could not reach the browser speech service. Check your internet connection, microphone permission, and try Chrome or Edge.";
    case "not-allowed":
    case "service-not-allowed":
      return "Microphone access was blocked. Allow microphone permission in the browser and try again.";
    case "audio-capture":
      return "No working microphone was found. Check your input device and browser microphone selection.";
    case "no-speech":
      return "No speech was detected. Try again and speak after the microphone indicator turns on.";
    case "aborted":
      return "Voice input was interrupted before transcription finished.";
    default:
      return `Voice input failed: ${errorCode}.`;
  }
}

export function normalizeDocument(doc) {
  if (typeof doc === "string") {
    return { filename: doc, tag: null };
  }

  return {
    filename: doc.filename,
    tag: doc.tag ?? null,
  };
}

export function formatDate(dateString) {
  try {
    return new Date(dateString).toLocaleDateString();
  } catch (_error) {
    return dateString;
  }
}

export function getStudySetLabel(type) {
  return STUDY_SET_TYPE_LABELS[type] || "Study Set";
}

export function getStudySetCount(type) {
  return STUDY_SET_TYPES.find((item) => item.value === type)?.count || 10;
}

export function autoResize(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
}

export function getViewportState() {
  if (typeof window === "undefined") {
    return { isMobile: false };
  }

  return {
    isMobile: window.innerWidth <= MOBILE_BREAKPOINT,
  };
}

export function isUnauthorizedError(error) {
  return error?.status === 401;
}

export function dedupeSources(sources = []) {
  const seen = new Set();

  return sources.filter((source) => {
    const label = (source?.filename || source?.source || "Unknown source").trim();
    const kind = source?.source_type || "chunk";
    const sourceId = source?.source_id || "";
    const key = `${sourceId}|${kind}|${label.toLowerCase()}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

export function formatDistance(distance) {
  if (typeof distance !== "number" || Number.isNaN(distance)) {
    return null;
  }

  return `Distance ${distance.toFixed(3)}`;
}

export function formatTraceTiming(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return null;
  }

  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}s`;
  }

  return `${Math.round(value)}ms`;
}

export function formatSearchModeLabel(mode) {
  switch (mode) {
    case "unfocused":
      return "Broad search";
    case "focused":
      return "Focused search";
    case "full_document":
      return "Direct document read";
    case "fallback_full_document":
      return "Fallback document read";
    default:
      return "Search";
  }
}

export function getSearchModeClass(mode) {
  switch (mode) {
    case "unfocused":
      return "mode-unfocused";
    case "focused":
      return "mode-focused";
    case "full_document":
      return "mode-full-document";
    case "fallback_full_document":
      return "mode-fallback-document";
    default:
      return "mode-unfocused";
  }
}
