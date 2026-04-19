function jsonResponse(route, payload, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(payload),
  });
}

function unauthorized(route, detail = "Unauthorized") {
  return jsonResponse(route, { detail }, 401);
}

function extractMultipartFilename(request) {
  const body = request.postData() || "";
  const match = body.match(/filename="([^"]+)"/);
  return match ? match[1] : "uploaded-file.pdf";
}

function createDefaultStudySet({ id, filename, type }) {
  const normalizedType = type || "flashcards";
  const titleMap = {
    flashcards: "Security Flashcards",
    mcq_quiz: "Security Quiz",
    written_quiz: "Security Written Practice",
    mixed_practice: "Security Mixed Practice",
  };

  const itemMap = {
    flashcards: [
      { id: 1, type: "flashcard", front: "What is hashing?", back: "A one-way transformation for stored secrets." },
      { id: 2, type: "flashcard", front: "What is salting?", back: "Adding unique random data before hashing." },
    ],
    mcq_quiz: [
      {
        id: 1,
        type: "mcq",
        question: "Which control helps defend passwords at rest?",
        options: ["Salting", "Caching", "Minification", "Pagination"],
        correct_answer: "Salting",
        explanation: "Salting reduces the value of precomputed attacks.",
      },
    ],
    written_quiz: [
      {
        id: 1,
        type: "written",
        prompt: "Explain why password salting matters.",
        model_answer: "It prevents identical passwords from producing identical hashes and weakens rainbow-table attacks.",
        rubric: "Mention uniqueness per password and attack resistance.",
      },
    ],
    mixed_practice: [
      { id: 1, type: "flashcard", front: "CIA", back: "Confidentiality, Integrity, Availability." },
      {
        id: 2,
        type: "mcq",
        question: "Which pillar is availability?",
        options: ["Uptime", "Hashing", "Obfuscation", "Compression"],
        correct_answer: "Uptime",
        explanation: "Availability is about dependable access to systems and data.",
      },
      {
        id: 3,
        type: "written",
        prompt: "Describe one replay-attack mitigation.",
        model_answer: "Use nonces or timestamps to ensure message freshness.",
        rubric: "Mention freshness and anti-reuse controls.",
      },
    ],
  };

  const items = itemMap[normalizedType] || itemMap.flashcards;
  return {
    id,
    title: titleMap[normalizedType] || "Study Set",
    type: normalizedType,
    difficulty: "Medium",
    source_filename: filename,
    item_count: items.length,
    created_at: "2026-04-19T12:00:00Z",
    items,
  };
}

export async function installMockStudySpaceApi(page, overrides = {}) {
  const state = {
    authenticated: false,
    user: { username: "ada" },
    documents: [],
    tags: [],
    notes: [],
    metadata: {},
    uploadJobs: [],
    uploadConfig: { accept: ".pdf,.doc,.docx" },
    studySets: [],
    chatRequests: [],
    ...overrides,
  };

  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (url.origin !== "http://127.0.0.1:4173") {
      await route.continue();
      return;
    }

    const { pathname } = url;

    if (!pathname.startsWith("/auth") &&
        !pathname.startsWith("/documents") &&
        !pathname.startsWith("/tags") &&
        !pathname.startsWith("/notes") &&
        !pathname.startsWith("/metadata") &&
        !pathname.startsWith("/upload-jobs") &&
        !pathname.startsWith("/upload-config") &&
        !pathname.startsWith("/upload") &&
        !pathname.startsWith("/study-sets") &&
        !pathname.startsWith("/chat")) {
      await route.continue();
      return;
    }

    const method = request.method();

    if (pathname === "/auth/me" && method === "GET") {
      if (!state.authenticated) {
        return unauthorized(route, "Not authenticated");
      }
      return jsonResponse(route, { user: state.user });
    }

    if (pathname === "/auth/signin" && method === "POST") {
      const payload = request.postDataJSON();
      state.authenticated = true;
      state.user = { username: payload.username };
      return jsonResponse(route, { user: state.user });
    }

    if (pathname === "/auth/signup" && method === "POST") {
      const payload = request.postDataJSON();
      state.authenticated = true;
      state.user = { username: payload.username };
      return jsonResponse(route, { user: state.user });
    }

    if (pathname === "/auth/logout" && method === "POST") {
      state.authenticated = false;
      return jsonResponse(route, { ok: true });
    }

    if (!state.authenticated) {
      return unauthorized(route, "Sign in required");
    }

    if (pathname === "/documents" && method === "GET") {
      return jsonResponse(route, { documents: state.documents });
    }

    if (pathname.startsWith("/documents/") && method === "DELETE") {
      const filename = decodeURIComponent(pathname.split("/").pop() || "");
      state.documents = state.documents.filter((item) => item.filename !== filename);
      delete state.metadata[filename];
      return jsonResponse(route, { ok: true });
    }

    if (pathname.includes("/documents/") && pathname.endsWith("/tag") && method === "PUT") {
      const filename = decodeURIComponent(pathname.split("/")[2] || "");
      const payload = request.postDataJSON();
      state.documents = state.documents.map((item) =>
        item.filename === filename ? { ...item, tag: payload.tag || null } : item
      );
      if (payload.tag && !state.tags.includes(payload.tag)) {
        state.tags = [...state.tags, payload.tag];
      }
      return jsonResponse(route, { ok: true });
    }

    if (pathname === "/tags" && method === "GET") {
      return jsonResponse(route, { tags: state.tags });
    }

    if (pathname === "/tags" && method === "POST") {
      const payload = request.postDataJSON();
      if (!state.tags.includes(payload.tag)) {
        state.tags = [...state.tags, payload.tag];
      }
      return jsonResponse(route, { tag: payload.tag });
    }

    if (pathname.startsWith("/tags/") && method === "DELETE") {
      const tag = decodeURIComponent(pathname.split("/").pop() || "");
      state.tags = state.tags.filter((item) => item !== tag);
      state.documents = state.documents.map((item) =>
        item.tag === tag ? { ...item, tag: null } : item
      );
      return jsonResponse(route, { ok: true });
    }

    if (pathname === "/notes" && method === "GET") {
      return jsonResponse(route, { notes: state.notes });
    }

    if (pathname === "/notes" && method === "POST") {
      const payload = request.postDataJSON();
      const note = {
        id: `note-${state.notes.length + 1}`,
        content: payload.content,
        created_at: "2026-04-19T12:00:00Z",
      };
      state.notes = [note, ...state.notes];
      return jsonResponse(route, { note });
    }

    if (pathname.startsWith("/notes/") && method === "DELETE") {
      const noteId = decodeURIComponent(pathname.split("/").pop() || "");
      state.notes = state.notes.filter((item) => item.id !== noteId);
      return jsonResponse(route, { ok: true });
    }

    if (pathname === "/metadata" && method === "GET") {
      return jsonResponse(route, state.metadata);
    }

    if (pathname === "/upload-jobs" && method === "GET") {
      return jsonResponse(route, { jobs: state.uploadJobs });
    }

    if (pathname === "/upload-config" && method === "GET") {
      return jsonResponse(route, state.uploadConfig);
    }

    if (pathname === "/upload" && method === "POST") {
      const filename = extractMultipartFilename(request);
      if (!state.documents.some((item) => item.filename === filename)) {
        state.documents = [...state.documents, { filename, tag: null }];
      }
      state.uploadJobs = [
        {
          job_id: `job-${state.uploadJobs.length + 1}`,
          filename,
          status: "completed",
          stage: "Indexed",
          progress: 100,
          completed_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ];
      return jsonResponse(route, { ok: true, filename });
    }

    if (pathname === "/study-sets" && method === "GET") {
      return jsonResponse(route, { study_sets: state.studySets });
    }

    if (pathname === "/study-sets/generate" && method === "POST") {
      const payload = request.postDataJSON();
      const studySet = createDefaultStudySet({
        id: `study-set-${state.studySets.length + 1}`,
        filename: payload.filename,
        type: payload.type,
      });
      state.studySets = [studySet, ...state.studySets];
      return jsonResponse(route, studySet);
    }

    if (pathname.startsWith("/study-sets/")) {
      const id = decodeURIComponent(pathname.split("/").pop() || "");
      const match = state.studySets.find((item) => item.id === id);
      if (!match) {
        return jsonResponse(route, { detail: "Not found" }, 404);
      }

      if (method === "GET") {
        return jsonResponse(route, match);
      }

      if (method === "DELETE") {
        state.studySets = state.studySets.filter((item) => item.id !== id);
        return jsonResponse(route, { ok: true });
      }
    }

    if (pathname === "/chat" && method === "POST") {
      const payload = request.postDataJSON();
      state.chatRequests.push(payload);

      const primaryFile =
        Array.isArray(payload.selected_files) && payload.selected_files.length
          ? payload.selected_files[0]
          : state.documents[0]?.filename || "Unknown source";

      return jsonResponse(route, {
        response: `Grounded answer for: ${payload.message}`,
        sources: [
          {
            source_id: "S1",
            doc_id: "doc-1",
            filename: primaryFile,
            chunk_index: 0,
            distance: 0.12,
            tag: state.documents[0]?.tag || "Uncategorized",
            source_type: "chunk",
          },
        ],
        trace: {
          generated_queries: [
            {
              id: "q1",
              text: payload.message,
              goal: "Summarize the selected material",
              search_mode: "focused",
              module_tag: state.documents[0]?.tag || null,
              target_files: payload.selected_files || [],
              results_found: 1,
            },
          ],
          retrieval_runs: [
            {
              query_id: "q1",
              query_text: payload.message,
              search_mode: "focused",
              module_tag: state.documents[0]?.tag || null,
              target_files: payload.selected_files || [],
              result_count: 1,
            },
          ],
          fused_results: [
            {
              source_id: "S1",
              filename: primaryFile,
              chunk_index: 0,
              tag: state.documents[0]?.tag || "Uncategorized",
              snippet: "Relevant chunk content",
              distance: 0.12,
            },
          ],
          full_document_fetches: [],
          timings_ms: {
            total: 184,
          },
          summary: {
            passages_used: 1,
            documents_considered: 1,
          },
        },
      });
    }

    return jsonResponse(route, { detail: `Unhandled mocked route: ${method} ${pathname}` }, 500);
  });

  return state;
}
