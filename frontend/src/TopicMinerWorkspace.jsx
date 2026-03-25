function isLikelyPastPaper(filename = "") {
  return /past|exam|paper|final|midterm|sample/i.test(filename);
}

function formatCollectionLabel(count) {
  if (count === 0) {
    return "No likely past papers detected yet";
  }

  if (count === 1) {
    return "1 likely past paper detected";
  }

  return `${count} likely past papers detected`;
}

export default function TopicMinerWorkspace({
  documents,
  selectedDocument,
  setSelectedDocument,
  open,
  onToggle
}) {
  const likelyPastPapers = documents.filter((doc) => isLikelyPastPaper(doc.filename));
  const activeDocument =
    documents.find((doc) => doc.filename === selectedDocument) || likelyPastPapers[0] || documents[0] || null;
  const selectedLooksLikePastPaper = activeDocument ? isLikelyPastPaper(activeDocument.filename) : false;
  const collectionPreview = likelyPastPapers.slice(0, 4);

  return (
    <section className={`section topic-miner-shell ${open ? "open" : ""}`}>
      <div className="section-head">
        <div>
          <div className="section-title">Topic Miner</div>
          <div className="helper-text">Workspace for recurring exam themes</div>
        </div>
        <button className="small-button" type="button" onClick={onToggle}>
          {open ? "Collapse" : "Open"}
        </button>
      </div>

      <button
        className={`studio-card topic-miner-card ${open ? "active" : ""}`}
        type="button"
        onClick={onToggle}
      >
        <div className="studio-card-icon">⛏</div>
        <div>
          <div className="studio-card-title">Topic Miner workspace</div>
          <div className="meta-text">
            Group past-paper questions into repeated themes, then trace each theme back to source questions.
          </div>
        </div>
      </button>

      {open ? (
        <div className="topic-miner-workspace">
          <section className="hero-card topic-miner-hero">
            <div className="chat-hero-badge">Exam prep</div>
            <h2>Mine repeat topics before we build the model pass.</h2>
            <p>
              This workspace is the shell for the exam-theme flow: pick a source set, review
              readiness, then inspect mined themes with citations.
            </p>
          </section>

          <div className="topic-miner-grid">
            <section className="topic-miner-panel">
              <div className="topic-miner-panel-head">
                <div>
                  <div className="topic-miner-title">Source set</div>
                  <div className="meta-text">{formatCollectionLabel(likelyPastPapers.length)}</div>
                </div>
                <span className="micro-pill">{documents.length} total docs</span>
              </div>

              <label className="topic-miner-field">
                <span>Focus document</span>
                <select
                  className="select"
                  aria-label="Topic miner source document"
                  value={selectedDocument}
                  onChange={(event) => setSelectedDocument(event.currentTarget.value)}
                >
                  <option value="">Auto-pick best source</option>
                  {documents.map((doc) => (
                    <option key={doc.filename} value={doc.filename}>
                      {doc.filename}
                    </option>
                  ))}
                </select>
              </label>

              <div className="topic-miner-readiness">
                <article className="topic-miner-stat">
                  <div className="topic-miner-stat-label">Current focus</div>
                  <div className="topic-miner-stat-value">
                    {activeDocument ? activeDocument.filename : "No documents yet"}
                  </div>
                  <div className="meta-text">
                    {activeDocument
                      ? selectedLooksLikePastPaper
                        ? "Looks like a past paper candidate."
                        : "Not clearly a past paper from the filename."
                      : "Upload past papers to start building a collection."}
                  </div>
                </article>
                <article className="topic-miner-stat">
                  <div className="topic-miner-stat-label">Planned collection mode</div>
                  <div className="topic-miner-stat-value">
                    {likelyPastPapers.length > 1 ? "Module collection" : "Single document pass"}
                  </div>
                  <div className="meta-text">
                    Start narrow, then expand to all detected past papers for aggregation.
                  </div>
                </article>
              </div>

              <div className="topic-miner-list">
                {collectionPreview.length ? (
                  collectionPreview.map((doc) => (
                    <div key={doc.filename} className="topic-miner-list-item">
                      <div>
                        <div className="topic-miner-list-title">{doc.filename}</div>
                        <div className="meta-text">Likely exam source</div>
                      </div>
                      <span className="micro-pill">Candidate</span>
                    </div>
                  ))
                ) : (
                  <div className="empty-card compact">
                    No obvious past papers yet. The workspace still exists; we just need sources.
                  </div>
                )}
              </div>
            </section>

            <section className="topic-miner-panel">
              <div className="topic-miner-panel-head">
                <div>
                  <div className="topic-miner-title">Planned flow</div>
                  <div className="meta-text">UI scaffold for the next implementation steps</div>
                </div>
              </div>

              <div className="topic-miner-steps">
                <div className="topic-miner-step">
                  <div className="topic-miner-step-index">1</div>
                  <div>
                    <div className="topic-miner-step-title">Segment questions</div>
                    <div className="meta-text">
                      Split each paper into question-level units instead of generic chunks.
                    </div>
                  </div>
                </div>
                <div className="topic-miner-step">
                  <div className="topic-miner-step-index">2</div>
                  <div>
                    <div className="topic-miner-step-title">Extract normalized themes</div>
                    <div className="meta-text">
                      Capture a canonical topic, subtopic, and evidence quote for each question.
                    </div>
                  </div>
                </div>
                <div className="topic-miner-step">
                  <div className="topic-miner-step-index">3</div>
                  <div>
                    <div className="topic-miner-step-title">Merge duplicates</div>
                    <div className="meta-text">
                      Collapse wording variants into one stable exam-theme label.
                    </div>
                  </div>
                </div>
                <div className="topic-miner-step">
                  <div className="topic-miner-step-index">4</div>
                  <div>
                    <div className="topic-miner-step-title">Rank by recurrence</div>
                    <div className="meta-text">
                      Show which themes appear most often and how recently they appeared.
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <section className="topic-miner-results">
            <div className="topic-miner-results-head">
              <div>
                <div className="section-title">Result canvas</div>
                <div className="helper-text">Reserved for mined themes, citations, and year coverage</div>
              </div>
              <span className="micro-pill">Workspace only</span>
            </div>

            <div className="topic-miner-result-grid">
              <article className="topic-miner-result-card">
                <div className="topic-miner-result-title">Recurring themes</div>
                <p className="meta-text">
                  Ranked list of canonical topics with occurrence counts and example questions.
                </p>
              </article>
              <article className="topic-miner-result-card">
                <div className="topic-miner-result-title">Evidence map</div>
                <p className="meta-text">
                  Every theme should link back to the exact question text and source paper.
                </p>
              </article>
              <article className="topic-miner-result-card">
                <div className="topic-miner-result-title">Coverage gaps</div>
                <p className="meta-text">
                  Call out modules with too few papers or weak extraction confidence.
                </p>
              </article>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}
