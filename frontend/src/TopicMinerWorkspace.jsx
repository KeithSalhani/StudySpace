import { useEffect, useMemo, useRef, useState } from "react";
import {
  analyzeExamFolder,
  createExamFolder,
  getExamFolderAnalysis,
  getExamFolders,
  getExamPaperFileUrl,
  getExamPapers,
  moveExamPaper,
  uploadExamPaper
} from "./api";

function isPdfDocument(filename = "") {
  return filename.toLowerCase().endsWith(".pdf");
}

function getFolderDocumentCount(folderId, documents) {
  return documents.filter((document) => document.folder_id === folderId).length;
}

function isAnalysisActive(analysis) {
  return analysis?.status === "queued" || analysis?.status === "processing";
}

function getFolderAnalysisMeta(analysis) {
  if (!analysis) {
    return "Ready to analyze";
  }

  if (analysis.status === "queued" || analysis.status === "processing") {
    const progressLabel = Number.isFinite(analysis.progress) ? `${analysis.progress}%` : "Working";
    return `${progressLabel} · ${analysis.stage || "Analyzing folder"}`;
  }

  if (analysis.status === "failed") {
    return analysis.error || "Analysis failed";
  }

  if (analysis.status === "completed") {
    const themeCount = analysis.summary?.theme_count || 0;
    return analysis.stale ? `Out of date · ${themeCount} themes` : `${themeCount} themes mined`;
  }

  return analysis.stage || "Ready to analyze";
}

export default function TopicMinerWorkspace({
  fullScreen = false,
  onOpenWorkspace,
  onCloseWorkspace,
  onError
}) {
  const fileInputRef = useRef(null);
  const [folders, setFolders] = useState([]);
  const [examDocuments, setExamDocuments] = useState([]);
  const [selectedFolderId, setSelectedFolderId] = useState(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState(null);
  const [selectedFolderAnalysis, setSelectedFolderAnalysis] = useState(null);
  const [newFolderName, setNewFolderName] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [navView, setNavView] = useState("folders");
  const [previewOpen, setPreviewOpen] = useState(false);
  const [isCreatingFolder, setIsCreatingFolder] = useState(false);
  const [movingDocumentId, setMovingDocumentId] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [analyzingFolderId, setAnalyzingFolderId] = useState("");

  async function refreshState() {
    const [foldersPayload, papersPayload] = await Promise.all([
      getExamFolders(),
      getExamPapers()
    ]);
    setFolders(Array.isArray(foldersPayload.folders) ? foldersPayload.folders : []);
    setExamDocuments(Array.isArray(papersPayload.documents) ? papersPayload.documents : []);
  }

  async function loadFolderAnalysis(folderId) {
    if (!folderId) {
      setSelectedFolderAnalysis(null);
      return null;
    }

    try {
      const payload = await getExamFolderAnalysis(folderId);
      setSelectedFolderAnalysis(payload);
      return payload;
    } catch (error) {
      if (error?.status === 404) {
        setSelectedFolderAnalysis(null);
        return null;
      }
      throw error;
    }
  }

  useEffect(() => {
    if (!fullScreen) {
      return;
    }

    let active = true;

    async function loadState() {
      try {
        const [foldersPayload, papersPayload] = await Promise.all([
          getExamFolders(),
          getExamPapers()
        ]);
        if (!active) {
          return;
        }
        setFolders(Array.isArray(foldersPayload.folders) ? foldersPayload.folders : []);
        setExamDocuments(Array.isArray(papersPayload.documents) ? papersPayload.documents : []);
      } catch (error) {
        onError?.(error.message);
      }
    }

    void loadState();

    return () => {
      active = false;
    };
  }, [fullScreen]);

  useEffect(() => {
    if (!fullScreen) {
      return;
    }

    if (!selectedFolderId) {
      const firstFolderWithDocs = folders.find(
        (folder) => getFolderDocumentCount(folder.id, examDocuments) > 0
      );
      if (firstFolderWithDocs) {
        setSelectedFolderId(firstFolderWithDocs.id);
      }
      return;
    }

    if (!folders.some((folder) => folder.id === selectedFolderId)) {
      setSelectedFolderId(null);
    }
  }, [examDocuments, folders, fullScreen, selectedFolderId]);

  const selectedFolder = useMemo(
    () => folders.find((folder) => folder.id === selectedFolderId) || null,
    [folders, selectedFolderId]
  );

  useEffect(() => {
    if (!fullScreen || !selectedFolderId) {
      setSelectedFolderAnalysis(null);
      return;
    }

    let active = true;

    async function fetchAnalysis() {
      try {
        const payload = await loadFolderAnalysis(selectedFolderId);
        if (!active) {
          return;
        }
        setSelectedFolderAnalysis(payload);
      } catch (error) {
        if (!active) {
          return;
        }
        onError?.(error.message);
      }
    }

    void fetchAnalysis();

    return () => {
      active = false;
    };
  }, [fullScreen, onError, selectedFolderId]);

  const documentsInSelectedFolder = useMemo(() => {
    if (!selectedFolderId) {
      return [];
    }

    return examDocuments.filter((document) => document.folder_id === selectedFolderId);
  }, [examDocuments, selectedFolderId]);

  useEffect(() => {
    if (selectedDocumentId) {
      const stillVisible = documentsInSelectedFolder.some(
        (document) => document.id === selectedDocumentId
      );
      if (!stillVisible) {
        setSelectedDocumentId(null);
      }
    }
  }, [documentsInSelectedFolder, selectedDocumentId]);

  const previewDocument = useMemo(
    () =>
      documentsInSelectedFolder.find((document) => document.id === selectedDocumentId) || null,
    [documentsInSelectedFolder, selectedDocumentId]
  );
  const activeFolderAnalysis = selectedFolderAnalysis || selectedFolder?.analysis || null;
  const activeFolderAnalysisMeta = getFolderAnalysisMeta(activeFolderAnalysis);

  useEffect(() => {
    if (!fullScreen || !selectedFolderId || !isAnalysisActive(selectedFolderAnalysis)) {
      return;
    }

    const intervalId = window.setInterval(() => {
      void (async () => {
        try {
          await refreshState();
          await loadFolderAnalysis(selectedFolderId);
        } catch (error) {
          onError?.(error.message);
        }
      })();
    }, 3000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [fullScreen, onError, selectedFolderAnalysis, selectedFolderId]);

  const layoutClassName = [
    "topic-miner-layout",
    sidebarOpen ? "sidebar-open" : "sidebar-closed",
    previewOpen ? "preview-open" : "preview-closed"
  ].join(" ");

  async function handleCreateFolder() {
    const value = newFolderName.trim();
    if (!value || isCreatingFolder) {
      return;
    }

    try {
      setIsCreatingFolder(true);
      const payload = await createExamFolder(value);
      setNewFolderName("");
      await refreshState();
      setSelectedFolderId(payload.folder?.id || null);
      setSelectedFolderAnalysis(null);
      setSidebarOpen(true);
      setNavView("papers");
    } catch (error) {
      onError?.(error.message);
    } finally {
      setIsCreatingFolder(false);
    }
  }

  async function handleMoveDocument(documentId, folderId) {
    try {
      setMovingDocumentId(documentId);
      await moveExamPaper(documentId, folderId);
      await refreshState();
    } catch (error) {
      onError?.(error.message);
    } finally {
      setMovingDocumentId("");
    }
  }

  async function handleFolderUpload(files) {
    if (!selectedFolderId) {
      return;
    }

    const fileList = Array.from(files || []);
    if (!fileList.length) {
      return;
    }

    try {
      setIsUploading(true);
      for (const file of fileList) {
        await uploadExamPaper(file, selectedFolderId);
      }
      await refreshState();
      setSidebarOpen(true);
    } catch (error) {
      onError?.(error.message);
    } finally {
      setIsUploading(false);
    }
  }

  async function handleAnalyzeFolder(folderId) {
    if (!folderId || analyzingFolderId === folderId) {
      return;
    }

    try {
      setAnalyzingFolderId(folderId);
      setSelectedFolderId(folderId);
      setSelectedDocumentId(null);
      setSelectedFolderAnalysis({ status: "queued", stage: "Queuing analysis" });
      setPreviewOpen(true);
      setSidebarOpen(true);
      setNavView("papers");
      await analyzeExamFolder(folderId);
      await refreshState();
      await loadFolderAnalysis(folderId);
    } catch (error) {
      if (error?.status === 409) {
        await refreshState();
        await loadFolderAnalysis(folderId);
        return;
      }
      onError?.(error.message);
    } finally {
      setAnalyzingFolderId("");
    }
  }

  function handleOpenAnalysisView(folderId = selectedFolderId) {
    if (!folderId) {
      return;
    }

    setSelectedFolderId(folderId);
    setSelectedDocumentId(null);
    setPreviewOpen(true);
    setSidebarOpen(true);
    setNavView("papers");
  }

  function handleFolderSelect(folderId) {
    if (selectedFolderId === folderId && navView === "papers") {
      setNavView("folders");
      return;
    }

    if (selectedFolderId !== folderId) {
      setSelectedFolderAnalysis(null);
    }
    
    setSelectedFolderId(folderId);
    setSelectedDocumentId(null);
    setSidebarOpen(true);
    setNavView("papers");
    setPreviewOpen(true);
  }

  function handleDocumentSelect(documentId) {
    if (selectedDocumentId === documentId && previewOpen) {
      setSelectedDocumentId(null);
      return;
    }

    setSelectedDocumentId(documentId);
    setPreviewOpen(true);
  }

  if (!fullScreen) {
    return (
      <section className="section topic-miner-shell">
        <div className="section-head">
          <div>
            <div className="section-title">Topic Miner</div>
            <div className="helper-text">Separate exam papers workspace</div>
          </div>
        </div>

        <button className="studio-card topic-miner-card active" type="button" onClick={onOpenWorkspace}>
          <div className="studio-card-icon">⛏</div>
          <div>
            <div className="studio-card-title">Open Topic Miner</div>
            <div className="meta-text">
              Open the exam-papers workspace with its own folders and PDF preview flow.
            </div>
          </div>
        </button>
      </section>
    );
  }

  return (
    <section className="topic-miner-fullscreen">
      <div className="app-topbar topic-miner-topbar">
        <div className="topbar-copy">
          <div className="section-kicker">Topic Miner</div>
          <h1>Exam Workspace</h1>
        </div>
        <div className="topbar-actions">
          <button className="small-button" type="button" onClick={onCloseWorkspace}>
            Back to workspace
          </button>
        </div>
      </div>

      <div className={layoutClassName}>
        <aside className={`topic-miner-navigator-sidebar ${sidebarOpen ? "open" : "collapsed"}`}>
          {!sidebarOpen ? (
            <div className="topic-miner-collapsed-actions">
              <button
                className="topic-miner-rail-button"
                type="button"
                aria-label="Open navigator"
                title="Open navigator"
                onClick={() => setSidebarOpen(true)}
              >
                📁
              </button>
            </div>
          ) : (
            <div className={`navigator-slider-wrapper nav-view-${navView}`}>
              <div className="navigator-pane folders-pane">
                <div className="topic-miner-sidebar-head">
                  <div>
                    <div className="topic-miner-sidebar-title">Exam Folders</div>
                    <div className="helper-text">{folders.length} total</div>
                  </div>
                  <button className="small-button" type="button" onClick={() => setSidebarOpen(false)}>
                    Collapse
                  </button>
                </div>

                <div className="topic-miner-folder-create">
                  <input
                    className="input"
                    placeholder="New exam folder"
                    value={newFolderName}
                    onChange={(event) => setNewFolderName(event.currentTarget.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        void handleCreateFolder();
                      }
                    }}
                  />
                  <button
                    className="small-button primary"
                    type="button"
                    disabled={!newFolderName.trim() || isCreatingFolder}
                    onClick={() => void handleCreateFolder()}
                  >
                    {isCreatingFolder ? "Adding..." : "Add"}
                  </button>
                </div>

                <div className="topic-miner-folder-list">
                  {folders.length ? (
                    folders.map((folder) => {
                      const count = getFolderDocumentCount(folder.id, examDocuments);
                      const active = folder.id === selectedFolderId;
                      const analysis = folder.analysis;
                      const analyzing = analyzingFolderId === folder.id || isAnalysisActive(analysis);

                      return (
                        <article
                          key={folder.id}
                          className={`topic-miner-folder-item ${active ? "active" : ""}`}
                        >
                          <button
                            className="topic-miner-folder-button"
                            type="button"
                            onClick={() => handleFolderSelect(folder.id)}
                          >
                            <div>
                              <div className="topic-miner-folder-name">{folder.name}</div>
                              <div className="meta-text">{count} paper{count === 1 ? "" : "s"}</div>
                              <div className="helper-text topic-miner-folder-analysis-copy">
                                {getFolderAnalysisMeta(analysis)}
                              </div>
                            </div>
                            <div className="topic-miner-folder-actions">
                              <span className="micro-pill">{count}</span>
                              <span className="topic-miner-chevron" aria-hidden="true">›</span>
                            </div>
                          </button>
                          <button
                            className={`small-button ${analysis?.status === "completed" ? "" : "primary"}`}
                            type="button"
                            disabled={!count || analyzingFolderId === folder.id || isAnalysisActive(analysis)}
                            onClick={() => void handleAnalyzeFolder(folder.id)}
                          >
                            {analyzing ? "Analyzing..." : analysis?.status === "completed" ? "Re-run" : "Analyze"}
                          </button>
                        </article>
                      );
                    })
                  ) : (
                    <div className="empty-card compact">Create your first exam folder.</div>
                  )}
                </div>
              </div>

              <div className="navigator-pane papers-pane">
                {selectedFolder ? (
                  <>
                    <div className="topic-miner-sidebar-head">
                      <div className="topic-miner-back-container">
                        <button className="small-button" type="button" onClick={() => setNavView("folders")}>
                          &larr; Back
                        </button>
                        <div>
                          <div className="topic-miner-sidebar-title">{selectedFolder.name}</div>
                          <div className="helper-text">
                            {documentsInSelectedFolder.length} paper{documentsInSelectedFolder.length === 1 ? "" : "s"}
                          </div>
                        </div>
                      </div>
                      <div className="topic-miner-head-actions topic-miner-papers-actions">
                        <button
                          className={`small-button ${activeFolderAnalysis?.status === "completed" ? "" : "primary"}`}
                          type="button"
                          disabled={!documentsInSelectedFolder.length || analyzingFolderId === selectedFolder.id || isAnalysisActive(activeFolderAnalysis)}
                          onClick={() => void handleAnalyzeFolder(selectedFolder.id)}
                        >
                          {analyzingFolderId === selectedFolder.id || isAnalysisActive(activeFolderAnalysis)
                            ? "Analyzing..."
                            : activeFolderAnalysis?.status === "completed"
                              ? "Re-run analysis"
                              : "Analyze folder"}
                        </button>
                        <button
                          className="small-button"
                          type="button"
                          disabled={!activeFolderAnalysis || (previewOpen && !selectedDocumentId)}
                          onClick={() => handleOpenAnalysisView(selectedFolder.id)}
                        >
                          {previewOpen && !selectedDocumentId ? "Viewing analysis" : "View analysis"}
                        </button>
                        <button className="small-button" type="button" onClick={() => fileInputRef.current?.click()}>
                          {isUploading ? "..." : "Upload PDF"}
                        </button>
                      </div>
                      <input
                        ref={fileInputRef}
                        hidden
                        type="file"
                        accept=".pdf"
                        multiple
                        onChange={async (event) => {
                          await handleFolderUpload(event.currentTarget.files);
                          event.currentTarget.value = "";
                        }}
                      />
                    </div>

                    <div className="topic-miner-analysis-status-card">
                      <div>
                        <div className="topic-miner-analysis-status-title">Topic mining</div>
                        <div className="helper-text">{activeFolderAnalysisMeta}</div>
                      </div>
                      <div className="topic-miner-analysis-status-actions">
                        {activeFolderAnalysis?.summary?.theme_count ? (
                          <span className="micro-pill active">
                            {activeFolderAnalysis.summary.theme_count} themes
                          </span>
                        ) : null}
                        <button
                          className="small-button"
                          type="button"
                          disabled={!activeFolderAnalysis || (previewOpen && !selectedDocumentId)}
                          onClick={() => handleOpenAnalysisView(selectedFolder.id)}
                        >
                          {previewOpen && !selectedDocumentId ? "Viewing" : "Open"}
                        </button>
                      </div>
                    </div>

                    <div className="topic-miner-paper-list">
                      {documentsInSelectedFolder.length ? (
                        documentsInSelectedFolder.map((document) => (
                          <article
                            key={document.id}
                            className={`topic-miner-paper-card ${previewDocument?.id === document.id ? "active" : ""}`}
                          >
                            <button
                              className="topic-miner-paper-button"
                              type="button"
                              onClick={() => handleDocumentSelect(document.id)}
                            >
                              <div className="topic-miner-paper-thumb">
                                {isPdfDocument(document.filename) ? (
                                  <iframe
                                    title={`${document.filename} first page preview`}
                                    src={`${getExamPaperFileUrl(document.id)}#page=1&toolbar=0&navpanes=0&scrollbar=0&view=FitH`}
                                  />
                                ) : (
                                  <div className="topic-miner-paper-fallback">No PDF preview</div>
                                )}
                              </div>
                              <div className="topic-miner-paper-meta">
                                <div className="topic-miner-paper-name">{document.filename}</div>
                                <div className="meta-text">
                                  {previewDocument?.id === document.id && previewOpen
                                    ? "Click again to collapse preview"
                                    : "Open preview"}
                                </div>
                              </div>
                            </button>

                            <select
                              className="select topic-miner-move-select"
                              aria-label={`Move ${document.filename} to another folder`}
                              value={document.folder_id || ""}
                              disabled={movingDocumentId === document.id}
                              onChange={(event) => void handleMoveDocument(document.id, event.currentTarget.value)}
                            >
                              {folders.map((folder) => (
                                <option key={folder.id} value={folder.id}>
                                  {folder.name}
                                </option>
                              ))}
                            </select>
                          </article>
                        ))
                      ) : (
                        <div className="empty-card">
                          No papers in this folder yet. Upload PDFs here to start previewing them.
                        </div>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="topic-miner-sidebar-placeholder">
                    <div className="empty-card">Choose an exam folder to open its papers.</div>
                  </div>
                )}
              </div>
            </div>
          )}
        </aside>

        <main className={`topic-miner-preview-panel ${previewOpen ? "open" : "collapsed"}`}>
          {previewOpen ? (
            previewDocument ? (
              isPdfDocument(previewDocument.filename) ? (
                <>
                  <div className="topic-miner-preview-head">
                    <div>
                      <div className="topic-miner-preview-title">{previewDocument.filename}</div>
                      <div className="helper-text">Scroll inside the preview.</div>
                    </div>
                    <button className="small-button" type="button" onClick={() => setPreviewOpen(false)}>
                      Collapse
                    </button>
                  </div>
                  <div className="topic-miner-preview-frame-wrap">
                    <iframe
                      className="topic-miner-preview-frame"
                      title={`${previewDocument.filename} preview`}
                      src={`${getExamPaperFileUrl(previewDocument.id)}#toolbar=0&navpanes=0&view=FitH`}
                    />
                  </div>
                </>
              ) : (
                <>
                  <div className="topic-miner-preview-head">
                    <div>
                      <div className="topic-miner-preview-title">{previewDocument.filename}</div>
                      <div className="helper-text">Preview unavailable for this file type.</div>
                    </div>
                    <button className="small-button" type="button" onClick={() => setPreviewOpen(false)}>
                      Collapse
                    </button>
                  </div>
                  <div className="topic-miner-preview-empty">
                    <div className="topic-miner-preview-title">No preview available</div>
                    <p className="meta-text">This file type might not have an inline preview.</p>
                  </div>
                </>
              )
            ) : selectedFolder ? (
              <>
                <div className="topic-miner-preview-head">
                  <div>
                    <div className="topic-miner-preview-title">{selectedFolder.name} topic analysis</div>
                    <div className="helper-text">{activeFolderAnalysisMeta}</div>
                  </div>
                  <div className="topic-miner-head-actions">
                    <button
                      className={`small-button ${activeFolderAnalysis?.status === "completed" ? "" : "primary"}`}
                      type="button"
                      disabled={!documentsInSelectedFolder.length || analyzingFolderId === selectedFolder.id || isAnalysisActive(activeFolderAnalysis)}
                      onClick={() => void handleAnalyzeFolder(selectedFolder.id)}
                    >
                      {analyzingFolderId === selectedFolder.id || isAnalysisActive(activeFolderAnalysis)
                        ? "Analyzing..."
                        : activeFolderAnalysis?.status === "completed"
                          ? "Re-run analysis"
                          : "Analyze folder"}
                    </button>
                    <button className="small-button" type="button" onClick={() => setPreviewOpen(false)}>
                      Collapse
                    </button>
                  </div>
                </div>

                <div className="topic-miner-analysis-body">
                  {activeFolderAnalysis?.status === "failed" ? (
                    <div className="empty-card topic-miner-analysis-empty">
                      <div className="topic-miner-preview-title">Analysis failed</div>
                      <p className="meta-text">{activeFolderAnalysis.error || "Try running the folder again."}</p>
                    </div>
                  ) : activeFolderAnalysis?.status === "completed" && activeFolderAnalysis?.result ? (
                    <>
                      <div className="topic-miner-analysis-summary-grid">
                        <article className="topic-miner-analysis-stat">
                          <span className="meta-text">Papers</span>
                          <strong>{activeFolderAnalysis.result.summary?.paper_count || 0}</strong>
                        </article>
                        <article className="topic-miner-analysis-stat">
                          <span className="meta-text">Questions</span>
                          <strong>{activeFolderAnalysis.result.summary?.question_count || 0}</strong>
                        </article>
                        <article className="topic-miner-analysis-stat">
                          <span className="meta-text">Themes</span>
                          <strong>{activeFolderAnalysis.result.summary?.theme_count || 0}</strong>
                        </article>
                        <article className="topic-miner-analysis-stat">
                          <span className="meta-text">Status</span>
                          <strong>{activeFolderAnalysis.stale ? "Stale" : "Current"}</strong>
                        </article>
                      </div>

                      {activeFolderAnalysis.result.observations?.length ? (
                        <section className="topic-miner-observations">
                          <div className="topic-miner-analysis-status-title">Observations</div>
                          <div className="topic-miner-observation-list">
                            {activeFolderAnalysis.result.observations.map((note, index) => (
                              <article key={`${note}-${index}`} className="topic-miner-observation-card">
                                {note}
                              </article>
                            ))}
                          </div>
                        </section>
                      ) : null}

                      <section className="topic-miner-theme-list">
                        {activeFolderAnalysis.result.themes?.length ? (
                          activeFolderAnalysis.result.themes.map((theme) => (
                            <article key={theme.canonical_topic} className="topic-miner-theme-card">
                              <div className="topic-miner-theme-head">
                                <div>
                                  <div className="topic-miner-theme-title">{theme.canonical_topic}</div>
                                  <div className="helper-text">
                                    Seen in {theme.frequency?.papers_with_topic || 0}/
                                    {theme.frequency?.total_papers || 0} papers
                                  </div>
                                </div>
                                <div className="topic-miner-theme-badges">
                                  {(theme.question_positions || []).map((position) => (
                                    <span key={`${theme.canonical_topic}-${position}`} className="micro-pill">
                                      Q{position}
                                    </span>
                                  ))}
                                </div>
                              </div>
                              <div className="topic-miner-theme-subtopics">
                                {(theme.recurring_subtopics || []).map((subtopic) => (
                                  <article key={`${theme.canonical_topic}-${subtopic.name}`} className="topic-miner-subtopic-card">
                                    <div className="topic-miner-subtopic-head">
                                      <div className="topic-miner-analysis-status-title">{subtopic.name}</div>
                                      <span className="micro-pill active">{subtopic.count}</span>
                                    </div>
                                    <div className="topic-miner-example-list">
                                      {(subtopic.example_questions || []).map((example) => (
                                        <article
                                          key={`${subtopic.name}-${example.paper}-${example.question_number}`}
                                          className="topic-miner-example-card"
                                        >
                                          <div className="meta-text">
                                            {example.paper} · Q{example.question_number}
                                          </div>
                                          <div>{example.summary}</div>
                                        </article>
                                      ))}
                                    </div>
                                  </article>
                                ))}
                              </div>
                            </article>
                          ))
                        ) : (
                          <div className="empty-card topic-miner-analysis-empty">
                            <div className="topic-miner-preview-title">No recurring topics yet</div>
                            <p className="meta-text">
                              The analysis finished, but no stable recurring themes were found.
                            </p>
                          </div>
                        )}
                      </section>
                    </>
                  ) : isAnalysisActive(activeFolderAnalysis) ? (
                    <div className="empty-card topic-miner-analysis-empty">
                      <div className="topic-miner-preview-title">Analyzing folder</div>
                      <p className="meta-text">{activeFolderAnalysisMeta}</p>
                    </div>
                  ) : (
                    <div className="empty-card topic-miner-analysis-empty">
                      <div className="topic-miner-preview-title">No topic analysis yet</div>
                      <p className="meta-text">
                        Run topic mining on this folder to surface recurring exam themes and examples.
                      </p>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <>
                <div className="topic-miner-preview-head">
                  <div />
                  <button className="small-button" type="button" onClick={() => setPreviewOpen(false)}>
                    Collapse
                  </button>
                </div>
                <div className="topic-miner-preview-empty">
                  <div className="topic-miner-preview-title">No folder selected</div>
                  <p className="meta-text">Pick a folder to preview its papers or analyze recurring topics.</p>
                </div>
              </>
            )
          ) : (
            <div className="topic-miner-collapsed-actions">
              <button
                className="topic-miner-rail-button"
                type="button"
                aria-label="Open main panel"
                title="Open main panel"
                onClick={() => setPreviewOpen(true)}
              >
                ⤢
              </button>
              {previewDocument ? <div className="meta-text preview-hint">{previewDocument.filename}</div> : null}
            </div>
          )}
        </main>
      </div>
    </section>
  );
}
