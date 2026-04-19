async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload && "detail" in payload
        ? payload.detail
        : "Request failed";
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }

  return payload;
}

function request(path, options = {}) {
  return fetch(path, {
    credentials: "same-origin",
    ...options
  }).then(parseResponse);
}

async function requestBlob(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...options
  });

  if (!response.ok) {
    await parseResponse(response);
  }

  return response.blob();
}

export function getCurrentUser() {
  return request("/auth/me");
}

export function signUp(username, password) {
  return request("/auth/signup", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ username, password })
  });
}

export function signIn(username, password) {
  return request("/auth/signin", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ username, password })
  });
}

export function signOut() {
  return request("/auth/logout", {
    method: "POST"
  });
}

export function exportAccountData() {
  return requestBlob("/account/export");
}

export function deleteAccount(username, password) {
  return request("/account", {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ username, password })
  });
}

export function getDocuments() {
  return request("/documents");
}

export function getFolders() {
  return request("/folders");
}

export function createFolder(name) {
  return request("/folders", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ name })
  });
}

export function getExamFolders() {
  return request("/exam-folders");
}

export function createExamFolder(name) {
  return request("/exam-folders", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ name })
  });
}

export function analyzeExamFolder(folderId) {
  return request(`/exam-folders/${encodeURIComponent(folderId)}/analyze`, {
    method: "POST"
  });
}

export function getExamFolderAnalysis(folderId) {
  return request(`/exam-folders/${encodeURIComponent(folderId)}/analysis`);
}

export function getExamPapers() {
  return request("/exam-papers");
}

export function deleteDocument(filename) {
  return request(`/documents/${encodeURIComponent(filename)}`, {
    method: "DELETE"
  });
}

export function removeMetadataEntry(filename, section, index) {
  return request(
    `/documents/${encodeURIComponent(filename)}/metadata/${encodeURIComponent(section)}/${index}`,
    {
      method: "DELETE"
    }
  );
}

export function updateDocumentTag(filename, tag) {
  return request(`/documents/${encodeURIComponent(filename)}/tag`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ tag })
  });
}

export function updateDocumentFolder(filename, folderId) {
  return request(`/documents/${encodeURIComponent(filename)}/folder`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ folder_id: folderId || null })
  });
}

export function moveExamPaper(documentId, folderId) {
  return request(`/exam-papers/${encodeURIComponent(documentId)}/folder`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ folder_id: folderId })
  });
}

export function getUploadJobs(limit = 50) {
  return request(`/upload-jobs?limit=${limit}`);
}

export function getUploadConfig() {
  return request("/upload-config");
}

export function uploadDocument(file, folderId = null) {
  const formData = new FormData();
  formData.append("file", file);
  if (folderId) {
    formData.append("folder_id", folderId);
  }

  return request("/upload", {
    method: "POST",
    body: formData
  });
}

export function getDocumentFileUrl(filename) {
  return `/documents/${encodeURIComponent(filename)}/file`;
}

export function uploadExamPaper(file, folderId) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("folder_id", folderId);

  return request("/exam-papers/upload", {
    method: "POST",
    body: formData
  });
}

export function getExamPaperFileUrl(documentId) {
  return `/exam-papers/${encodeURIComponent(documentId)}/file`;
}

export function sendChatMessage(message, selectedFiles) {
  return request("/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      message,
      selected_files: selectedFiles.length ? selectedFiles : null
    })
  });
}

export function getTags() {
  return request("/tags");
}

export function createTag(tag) {
  return request("/tags", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ tag })
  });
}

export function removeTag(tag) {
  return request(`/tags/${encodeURIComponent(tag)}`, {
    method: "DELETE"
  });
}

export function getNotes() {
  return request("/notes");
}

export function createNote(content) {
  return request("/notes", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ content })
  });
}

export function removeNote(noteId) {
  return request(`/notes/${encodeURIComponent(noteId)}`, {
    method: "DELETE"
  });
}

export function generateQuiz(filename) {
  return request("/quiz/generate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      filename,
      num_questions: 5,
      difficulty: "Medium"
    })
  });
}

export function generateFlashcards(filename) {
  return request("/flashcards/generate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      filename,
      num_cards: 10
    })
  });
}

export function generateStudySet({ filename, type, numItems = 10, difficulty = "Medium" }) {
  return request("/study-sets/generate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      filename,
      type,
      num_items: numItems,
      difficulty
    })
  });
}

export function getStudySets() {
  return request("/study-sets");
}

export function getStudySet(studySetId) {
  return request(`/study-sets/${encodeURIComponent(studySetId)}`);
}

export function removeStudySet(studySetId) {
  return request(`/study-sets/${encodeURIComponent(studySetId)}`, {
    method: "DELETE"
  });
}

export function getMetadata() {
  return request("/metadata");
}
