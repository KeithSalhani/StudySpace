import { useEffect, useMemo, useRef, useState } from "react";
import {
  createExamFolder,
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
  const [newFolderName, setNewFolderName] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [navView, setNavView] = useState("folders");
  const [previewOpen, setPreviewOpen] = useState(false);
  const [isCreatingFolder, setIsCreatingFolder] = useState(false);
  const [movingDocumentId, setMovingDocumentId] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  async function refreshState() {
    const [foldersPayload, papersPayload] = await Promise.all([
      getExamFolders(),
      getExamPapers()
    ]);
    setFolders(Array.isArray(foldersPayload.folders) ? foldersPayload.folders : []);
    setExamDocuments(Array.isArray(papersPayload.documents) ? papersPayload.documents : []);
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
  }, [fullScreen, onError]);

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

  function handleFolderSelect(folderId) {
    if (selectedFolderId === folderId && navView === "papers") {
      setNavView("folders");
      return;
    }

    setSelectedFolderId(folderId);
    setSidebarOpen(true);
    setNavView("papers");
  }

  function handleDocumentSelect(documentId) {
    if (selectedDocumentId === documentId && previewOpen) {
      setPreviewOpen(false);
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
                  <button className="small-button primary" type="button" onClick={() => void handleCreateFolder()}>
                    {isCreatingFolder ? "Adding..." : "Add"}
                  </button>
                </div>

                <div className="topic-miner-folder-list">
                  {folders.length ? (
                    folders.map((folder) => {
                      const count = getFolderDocumentCount(folder.id, examDocuments);
                      const active = folder.id === selectedFolderId;

                      return (
                        <button
                          key={folder.id}
                          className={`topic-miner-folder-item ${active ? "active" : ""}`}
                          type="button"
                          onClick={() => handleFolderSelect(folder.id)}
                        >
                          <div>
                            <div className="topic-miner-folder-name">{folder.name}</div>
                            <div className="meta-text">{count} paper{count === 1 ? "" : "s"}</div>
                          </div>
                          <div className="topic-miner-folder-actions">
                            <span className="micro-pill">{count}</span>
                            <span className="topic-miner-chevron" aria-hidden="true">›</span>
                          </div>
                        </button>
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
                      <div className="topic-miner-head-actions">
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
          {previewDocument && previewOpen && isPdfDocument(previewDocument.filename) ? (
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
              {previewDocument && previewOpen ? (
                <div className="topic-miner-preview-empty">
                  <div className="topic-miner-preview-title">No preview available</div>
                  <p className="meta-text">This file type might not have a preview.</p>
                </div>
              ) : previewDocument && !previewOpen ? (
                <div className="topic-miner-collapsed-actions">
                  <button
                    className="topic-miner-rail-button"
                    type="button"
                    aria-label={`Open preview for ${previewDocument.filename}`}
                    title={`Open preview for ${previewDocument.filename}`}
                    onClick={() => setPreviewOpen(true)}
                  >
                    ⤢
                  </button>
                  <div className="meta-text preview-hint">{previewDocument.filename}</div>
                </div>
              ) : !previewOpen ? (
                <div className="topic-miner-collapsed-actions">
                  <button
                    className="topic-miner-rail-button"
                    type="button"
                    aria-label="Open preview panel"
                    title="Open preview panel"
                    onClick={() => setPreviewOpen(true)}
                  >
                    ⤢
                  </button>
                </div>
              ) : (
                <>
                  <div className="topic-miner-preview-head">
                    <div />
                    <button className="small-button" type="button" onClick={() => setPreviewOpen(false)}>
                      Collapse
                    </button>
                  </div>
                  <div className="topic-miner-preview-empty">
                    <div className="topic-miner-preview-title">No paper selected</div>
                    <p className="meta-text">Pick a folder, then choose a PDF to preview it here.</p>
                  </div>
                </>
              )}
            </>
          )}
        </main>
      </div>
    </section>
  );
}
