import { useState } from "react";

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
  selectedFiles,
  setSelectedFiles,
  handleUpdateTag,
  handleDeleteMetadataEntry,
  handleDeleteDocument,
  notes,
  noteDraft,
  setNoteDraft,
  handleAddNote,
  handleDeleteNote,
}) {
  const [openMetadataDocument, setOpenMetadataDocument] = useState(null);
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

  function getDocumentMetadataCount(docMeta) {
    if (!docMeta || typeof docMeta !== "object") {
      return 0;
    }
    return ["assessments", "deadlines", "contacts"].reduce((total, key) => {
      return total + (Array.isArray(docMeta[key]) ? docMeta[key].length : 0);
    }, 0);
  }

  const activeMetadata = openMetadataDocument ? metadata[openMetadataDocument] || {} : null;

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

                    <div className="stack">
                      {docs.map((doc) => {
                        const docMeta = metadata[doc.filename] || {};
                        const metadataCount = getDocumentMetadataCount(docMeta);
                        return (
                          <div key={doc.filename} className="document-card-shell">
                            <div className="document-item" style={{ background: "var(--surface-strong)" }}>
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
                              <div className="document-actions">
                                {metadataCount > 0 ? (
                                  <button
                                    className="icon-button metadata-toggle-button"
                                    type="button"
                                    title="View metadata"
                                    aria-label={`View metadata for ${doc.filename}`}
                                    onClick={() => setOpenMetadataDocument(doc.filename)}
                                  >
                                    <span className="metadata-toggle-glyph" aria-hidden="true">i</span>
                                    <span className="metadata-count">{metadataCount}</span>
                                  </button>
                                ) : null}
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
                            </div>
                          </div>
                        );
                      })}
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

      {openMetadataDocument ? (
        <div className="modal-backdrop" onClick={() => setOpenMetadataDocument(null)}>
          <section
            className="modal metadata-modal"
            role="dialog"
            aria-modal="true"
            aria-label={`Metadata for ${openMetadataDocument}`}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-head">
              <div>
                <div className="section-title">Document Metadata</div>
                <div className="meta-text">{openMetadataDocument}</div>
              </div>
              <button
                className="icon-button modal-close"
                type="button"
                aria-label="Close metadata panel"
                onClick={() => setOpenMetadataDocument(null)}
              >
                ×
              </button>
            </div>
            <div className="modal-body metadata-modal-body">
              {Array.isArray(activeMetadata?.assessments) && activeMetadata.assessments.length > 0 ? (
                <div className="metadata-section">
                  <div className="insight-label">Assessments</div>
                  <div className="stack">
                    {activeMetadata.assessments.map((entry, index) => (
                      <div key={`assessment-${index}`} className="insight-item metadata-entry">
                        <div className="insight-text">
                          <strong>{entry.item}</strong>
                          {entry.weight ? ` • ${entry.weight}` : ""}
                        </div>
                        <button
                          className="metadata-delete"
                          type="button"
                          onClick={() =>
                            void handleDeleteMetadataEntry(openMetadataDocument, "assessments", index)
                          }
                        >
                          Delete
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {Array.isArray(activeMetadata?.deadlines) && activeMetadata.deadlines.length > 0 ? (
                <div className="metadata-section">
                  <div className="insight-label">Deadlines</div>
                  <div className="stack">
                    {activeMetadata.deadlines.map((entry, index) => (
                      <div key={`deadline-${index}`} className="insight-item metadata-entry">
                        <div className="insight-text">
                          <strong>{entry.event}</strong>
                          {entry.date ? ` • ${formatDate(entry.date)}` : ""}
                        </div>
                        <button
                          className="metadata-delete"
                          type="button"
                          onClick={() =>
                            void handleDeleteMetadataEntry(openMetadataDocument, "deadlines", index)
                          }
                        >
                          Delete
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {Array.isArray(activeMetadata?.contacts) && activeMetadata.contacts.length > 0 ? (
                <div className="metadata-section">
                  <div className="insight-label">Contacts</div>
                  <div className="stack">
                    {activeMetadata.contacts.map((entry, index) => (
                      <div key={`contact-${index}`} className="insight-item metadata-entry">
                        <div className="insight-text">
                          <strong>{entry.name}</strong>
                          {entry.role ? ` (${entry.role})` : ""}
                          {entry.email ? ` • ${entry.email}` : ""}
                        </div>
                        <button
                          className="metadata-delete"
                          type="button"
                          onClick={() =>
                            void handleDeleteMetadataEntry(openMetadataDocument, "contacts", index)
                          }
                        >
                          Delete
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {getDocumentMetadataCount(activeMetadata) === 0 ? (
                <div className="empty-card">No extracted metadata for this document.</div>
              ) : null}
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
