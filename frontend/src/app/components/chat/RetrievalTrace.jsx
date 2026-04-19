import { useEffect, useState } from "react";

import {
  formatDistance,
  formatSearchModeLabel,
  formatTraceTiming,
  getSearchModeClass,
} from "../../utils";

export default function RetrievalTrace({ message }) {
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
      "Choosing search modes",
      "Searching your study material",
      "Building one grounded answer",
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

  const generatedQueries = Array.isArray(trace.generated_queries) ? trace.generated_queries : [];
  const queryCount = generatedQueries.length;
  const fusedResults = Array.isArray(trace.fused_results) ? trace.fused_results : [];
  const retrievalRuns = Array.isArray(trace.retrieval_runs) ? trace.retrieval_runs : [];
  const fullDocumentFetches = Array.isArray(trace.full_document_fetches) ? trace.full_document_fetches : [];
  const searchModesUsed = Array.from(
    new Set(generatedQueries.map((query) => query?.search_mode).filter(Boolean))
  );
  const summary = trace.summary || {};
  const timings = trace.timings_ms || {};
  const fullDocumentFetchesByQuery = fullDocumentFetches.reduce((accumulator, item) => {
    const queryId = item?.query_id;
    if (!queryId) {
      return accumulator;
    }
    accumulator[queryId] = [...(accumulator[queryId] || []), item];
    return accumulator;
  }, {});

  function renderModePill(mode, compact = false, keyValue = null) {
    return (
      <span
        key={keyValue || undefined}
        className={`trace-mode-pill ${getSearchModeClass(mode)} ${compact ? "compact" : ""}`.trim()}
      >
        {formatSearchModeLabel(mode)}
      </span>
    );
  }

  function renderTargetFiles(files) {
    if (!Array.isArray(files) || !files.length) {
      return null;
    }

    return (
      <div className="trace-target-list">
        {files.map((filename) => (
          <span key={filename} className="trace-target-pill">
            {filename}
          </span>
        ))}
      </div>
    );
  }

  function renderFullDocumentFetchCard(item, keyPrefix = "") {
    return (
      <article key={`${keyPrefix}${item.source_id || item.filename}`} className="trace-result-card kept">
        <div className="trace-result-top">
          <div className="trace-result-file">
            {item.source_id ? `${item.source_id} • ` : ""}
            {item.filename}
          </div>
          <div className="trace-result-meta">
            {renderModePill(item.search_mode, true)}
            {item.query_id ? <span>{item.query_id.toUpperCase()}</span> : null}
            {item.tag ? <span>{item.tag}</span> : null}
            {item.source ? <span>{item.source}</span> : null}
          </div>
        </div>
        {item.reason ? <div className="trace-result-snippet">{item.reason}</div> : null}
      </article>
    );
  }

  return (
    <div className="retrieval-trace">
      <div className="trace-head">
        <div className="source-list-label">Search breakdown</div>
        <div className="trace-pill-row">
          <span className="chat-status-pill">{queryCount} step{queryCount === 1 ? "" : "s"}</span>
          <span className="chat-status-pill">{summary.passages_used || fusedResults.length} passages</span>
          <span className="chat-status-pill">{summary.documents_considered || 0} docs</span>
          {searchModesUsed.map((mode) => renderModePill(mode, true, mode))}
          {formatTraceTiming(timings.total) ? (
            <span className="chat-status-pill">{formatTraceTiming(timings.total)}</span>
          ) : null}
        </div>
      </div>

      <details className="trace-details">
        <summary>How I searched</summary>
        <div className="trace-section">
          <div className="trace-query-grid">
            {generatedQueries.map((query) => (
              <article key={query.id} className="trace-query-card">
                <div className="trace-query-top">
                  <div className="trace-query-id">{query.id?.toUpperCase() || "Q"}</div>
                  <div className="trace-chip-row">
                    {renderModePill(query.search_mode)}
                    {query.module_tag ? (
                      <span className="micro-pill">Tag {query.module_tag}</span>
                    ) : null}
                  </div>
                </div>
                <div className="trace-query-text">{query.text}</div>
                {renderTargetFiles(query.target_files)}
                {query.goal ? <div className="meta-text">{query.goal}</div> : null}
              </article>
            ))}
          </div>
        </div>

        <div className="trace-section">
          <div className="trace-section-title">Executed steps</div>
          <div className="trace-run-list">
            {retrievalRuns.map((run) => (
              <section key={run.query_id} className="trace-run-card">
                <div className="trace-run-head">
                  <div>
                    <div className="trace-run-label">{run.query_id?.toUpperCase() || "Query"}</div>
                    <div className="trace-run-query">{run.query}</div>
                  </div>
                  <div className="trace-chip-row">
                    {renderModePill(run.search_mode)}
                    {run.module_tag ? <span className="micro-pill">Tag {run.module_tag}</span> : null}
                  </div>
                </div>
                {renderTargetFiles(run.target_files)}
                {run.search_mode === "full_document" ? (
                  Array.isArray(fullDocumentFetchesByQuery[run.query_id]) &&
                  fullDocumentFetchesByQuery[run.query_id].length ? (
                    <div className="trace-result-list">
                      {fullDocumentFetchesByQuery[run.query_id].map((item) =>
                        renderFullDocumentFetchCard(item, `${run.query_id}-`)
                      )}
                    </div>
                  ) : (
                    <div className="empty-card compact">No full documents could be loaded for this step.</div>
                  )
                ) : Array.isArray(run.results) && run.results.length ? (
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
                  <div className="empty-card compact">No passages retrieved for this step.</div>
                )}
              </section>
            ))}
          </div>
        </div>

        {fullDocumentFetches.length ? (
          <div className="trace-section">
            <div className="trace-section-title">Full document reads</div>
            <div className="trace-result-list">
              {fullDocumentFetches.map((item) => renderFullDocumentFetchCard(item))}
            </div>
          </div>
        ) : null}

        {fusedResults.length || fullDocumentFetches.length ? (
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
              {fullDocumentFetches.map((item) => (
                <article key={`full-${item.source_id || item.filename}`} className="trace-result-card kept">
                  <div className="trace-result-top">
                    <div className="trace-result-file">
                      {item.source_id ? `${item.source_id} • ` : ""}
                      {item.filename}
                    </div>
                    <div className="trace-result-meta">
                      <span>Full document</span>
                      {item.tag ? <span>{item.tag}</span> : null}
                    </div>
                  </div>
                  {item.reason ? <div className="trace-result-snippet">{item.reason}</div> : null}
                </article>
              ))}
            </div>
          </div>
        ) : null}
      </details>
    </div>
  );
}
