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

export function getDocuments() {
  return request("/documents");
}

export function deleteDocument(filename) {
  return request(`/documents/${encodeURIComponent(filename)}`, {
    method: "DELETE"
  });
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

export function getUploadJobs(limit = 50) {
  return request(`/upload-jobs?limit=${limit}`);
}

export function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  return request("/upload", {
    method: "POST",
    body: formData
  });
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

export function getMetadata() {
  return request("/metadata");
}
