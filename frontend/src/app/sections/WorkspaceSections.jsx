import { formatDate } from "../utils";

export default function WorkspaceSections({
  isDragOver,
  setIsDragOver,
  fileInputRef,
  uploadAccept,
  handleUpload,
  visibleUploadJobs,
  documents,
  tags,
  metadata,
  expandedAssessments,
  setExpandedAssessments,
  selectedFiles,
  setSelectedFiles,
  handleUpdateTag,
  handleDeleteDocument,
  notes,
  noteDraft,
  setNoteDraft,
  handleAddNote,
  handleDeleteNote,
}) {
  const groupedDocuments = { Uncategorized: [] };
  tags.forEach((tag) => {
    groupedDocuments[tag] = [];
  });

  documents.forEach((doc) => {
    const tag = doc.tag && tags.includes(doc.tag) ? doc.tag : "Uncategorized";
    if (!groupedDocuments[tag]) {
      groupedDocuments[tag] = [];
    }
    groupedDocuments[tag].push(doc);
  });

  const tagMetadata = {};
  Object.keys(groupedDocuments).forEach((tag) => {
    tagMetadata[tag] = { assessments: [], deadlines: [], contacts: [] };
    groupedDocuments[tag].forEach((doc) => {
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
          role="button"
          tabIndex={0}
          aria-label="Upload study material"
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              fileInputRef.current?.click();
            }
          }}
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
            accept={uploadAccept || undefined}
            multiple
            onChange={async (event) => {
              await handleUpload(event.currentTarget.files);
              event.currentTarget.value = "";
            }}
          />
        </div>
      </section>

      {visibleUploadJobs.length > 0 && (
        <section className="section" style={{ marginTop: "16px" }}>
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
                <div
                  className="progress-track"
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={Math.max(0, Math.min(100, job.progress || 0))}
                  aria-label={`${job.filename} upload progress`}
                >
                  <div
                    className="progress-bar"
                    style={{
                      width: `${Math.max(0, Math.min(100, job.progress || 0))}%`,
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
                    job.error ? `Error: ${job.error}` : null,
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
              .filter(([, docs]) => docs.length > 0)
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
                  <div
                    key={tag}
                    className="tag-group"
                    style={{ marginBottom: "16px", background: "var(--surface)", padding: "16px", borderRadius: "22px", border: "1px solid var(--border)" }}
                  >
                    <div className="tag-group-header" style={{ marginBottom: "16px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <h3 style={{ margin: 0, fontSize: "1.05rem", color: "var(--text)" }}>{tag}</h3>
                      <div className="micro-pill">{docs.length} file{docs.length === 1 ? "" : "s"}</div>
                    </div>

                    {hasInsights && (
                      <div className="tag-insights" style={{ marginBottom: "20px", display: "flex", flexDirection: "column", gap: "12px" }}>
                        {meta.assessments.length > 0 && (
                          <div className="insight-group">
                            <button
                              className="insight-label"
                              type="button"
                              aria-expanded={isAssessmentsExpanded}
                              aria-controls={`assessments-${tag}`}
                              style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}
                              onClick={() => {
                                setExpandedAssessments((prev) => {
                                  const next = new Set(prev);
                                  if (next.has(tag)) next.delete(tag);
                                  else next.add(tag);
                                  return next;
                                });
                              }}
                            >
                              Assessments
                              <span style={{ fontSize: "0.8rem" }}>{isAssessmentsExpanded ? "▲" : "▼"}</span>
                            </button>
                            {isAssessmentsExpanded && (
                              <div id={`assessments-${tag}`} className="stack">
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
                        <div key={doc.filename} className="document-item" style={{ background: "var(--surface-strong)" }}>
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
                                  className="micro-pill document-tag-select"
                                  aria-label={`Topic for ${doc.filename}`}
                                  value={doc.tag && tags.includes(doc.tag) ? doc.tag : ""}
                                  onChange={(event) => {
                                    if (event.target.value !== (doc.tag || "")) {
                                      void handleUpdateTag(doc.filename, event.target.value);
                                    }
                                  }}
                                >
                                  <option value="">Uncategorized</option>
                                  {tags.map((topic) => (
                                    <option key={topic} value={topic}>{topic}</option>
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
                            aria-label={`Delete ${doc.filename}`}
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
            aria-label="New note"
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
