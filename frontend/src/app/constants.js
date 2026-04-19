export const COMPLETED_UPLOAD_VISIBLE_MS = 4000;
export const MOBILE_BREAKPOINT = 900;
export const ACCESSIBILITY_STORAGE_KEY = "studyspace-accessibility-settings";

export const DEFAULT_ACCESSIBILITY_SETTINGS = {
  voiceInput: false,
  enhancedFocus: false,
  largerText: false,
  highContrast: false,
  reducedMotion: false,
  announceUpdates: true,
};

export const initialMessages = [];

export const starterQuestions = [
  "Give me a quick summary.",
  "Create an exam prep checklist.",
  "Explain the difficult concepts.",
];

export const PRIVACY_CONTACT_EMAIL = "gdpr@studyspace.ie";

export const STUDY_SET_TYPES = [
  { value: "flashcards", label: "Flashcards", count: 10 },
  { value: "mcq_quiz", label: "MCQ Quiz", count: 5 },
  { value: "written_quiz", label: "Written Quiz", count: 5 },
  { value: "mixed_practice", label: "Mixed Practice", count: 9 },
];

export const STUDY_SET_TYPE_LABELS = STUDY_SET_TYPES.reduce((acc, item) => {
  acc[item.value] = item.label;
  return acc;
}, {});

export const STUDY_SET_DIFFICULTIES = ["Easy", "Medium", "Hard"];
