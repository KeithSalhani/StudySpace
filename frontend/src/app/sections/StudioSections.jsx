import TopicMinerWorkspace from "../../TopicMinerWorkspace";
import {
  STUDY_SET_DIFFICULTIES,
  STUDY_SET_TYPES,
} from "../constants";
import {
  getStudySetCount,
  getStudySetLabel,
} from "../utils";

export default function StudioSections({
  selectedDocument,
  setSelectedDocument,
  documents,
  studySetType,
  setStudySetType,
  studySetDifficulty,
  setStudySetDifficulty,
  hasStudioSelection,
  handleGenerateStudySet,
  studySets,
  handleOpenStudySet,
  handleDeleteStudySet,
  onOpenTopicMiner,
}) {
  return (
    <div className="studio-stack">
      <section className="section">
        <div className="section-title">Source document</div>
        <select
          className="select"
          aria-label="Source document"
          value={selectedDocument}
          onChange={(event) => setSelectedDocument(event.currentTarget.value)}
        >
          <option value="">Select a document...</option>
          {documents.map((doc) => (
            <option key={doc.filename} value={doc.filename}>
              {doc.filename}
            </option>
          ))}
        </select>
      </section>

      <section className="section">
        <div className="section-head">
          <div className="section-title">Generate</div>
          <div className="helper-text">Auto-saves</div>
        </div>
        <div className="study-mode-grid" role="group" aria-label="Study set type">
          {STUDY_SET_TYPES.map((type) => (
            <button
              key={type.value}
              className={`study-mode-button ${studySetType === type.value ? "active" : ""}`}
              type="button"
              aria-pressed={studySetType === type.value}
              onClick={() => setStudySetType(type.value)}
            >
              {type.label}
            </button>
          ))}
        </div>
        <select
          className="select"
          aria-label="Study difficulty"
          value={studySetDifficulty}
          onChange={(event) => setStudySetDifficulty(event.currentTarget.value)}
        >
          {STUDY_SET_DIFFICULTIES.map((difficulty) => (
            <option key={difficulty} value={difficulty}>
              {difficulty}
            </option>
          ))}
        </select>
        <button
          className="studio-card quiz-card"
          type="button"
          disabled={!hasStudioSelection}
          onClick={() => void handleGenerateStudySet()}
        >
          <div className="studio-card-icon">📝</div>
          <div>
            <div className="studio-card-title">Generate {getStudySetLabel(studySetType)}</div>
            <div className="meta-text">{getStudySetCount(studySetType)} items from the selected source</div>
          </div>
        </button>
      </section>

      <section className="section">
        <div className="section-head">
          <div className="section-title">Saved sets</div>
          <div className="helper-text">{studySets.length} saved</div>
        </div>
        <div className="saved-study-list">
          {studySets.length ? (
            studySets.map((studySet) => (
              <div key={studySet.id} className="saved-study-card">
                <button
                  className="saved-study-main"
                  type="button"
                  onClick={() => void handleOpenStudySet(studySet.id)}
                >
                  <div className="saved-study-title">{studySet.title}</div>
                  <div className="meta-text">
                    {getStudySetLabel(studySet.type)} • {studySet.item_count || studySet.items?.length || 0} items
                  </div>
                  <div className="meta-text">{studySet.source_filename}</div>
                </button>
                <button
                  className="icon-button"
                  type="button"
                  title="Delete saved set"
                  aria-label={`Delete ${studySet.title}`}
                  onClick={() => void handleDeleteStudySet(studySet.id)}
                >
                  ×
                </button>
              </div>
            ))
          ) : (
            <div className="empty-card compact">No saved study sets yet.</div>
          )}
        </div>
      </section>

      <TopicMinerWorkspace onOpenWorkspace={onOpenTopicMiner} />
    </div>
  );
}
