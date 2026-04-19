import { useDialog } from "../../hooks/useDialog";
import { formatDate, getStudySetLabel } from "../../utils";

export default function StudySetPracticeModal({
  state,
  onClose,
  onAnswer,
  onFlip,
  onPrev,
  onNext,
  onWrittenChange,
  onReveal,
}) {
  const items = Array.isArray(state.data?.items) ? state.data.items : [];
  const currentItem = items[state.index];
  const dialogRef = useDialog(true, onClose);
  const createdAt = state.data?.created_at ? formatDate(state.data.created_at) : "";

  function renderItem(item) {
    if (!item) {
      return <div className="empty-state">No study items returned.</div>;
    }

    if (item.type === "flashcard") {
      return (
        <button
          className="flashcard practice-flashcard"
          type="button"
          onClick={onFlip}
          aria-label={`Flip flashcard ${state.index + 1} of ${items.length}`}
        >
          <div>
            <div className="flashcard-label">{state.side === "front" ? "Prompt" : "Answer"}</div>
            <div className="flashcard-text">{state.side === "front" ? item.front : item.back}</div>
          </div>
        </button>
      );
    }

    if (item.type === "mcq") {
      const selected = state.answers[state.index];
      const answered = selected !== undefined;
      return (
        <section className="practice-item">
          <h3>{item.question}</h3>
          <div className="quiz-options">
            {(item.options || []).map((option) => {
              const classNames = ["quiz-option"];
              if (selected === option) {
                classNames.push("selected");
              }
              if (answered && option === item.correct_answer) {
                classNames.push("correct");
              } else if (answered && selected === option && option !== item.correct_answer) {
                classNames.push("incorrect");
              }

              return (
                <button
                  key={option}
                  className={classNames.join(" ")}
                  type="button"
                  disabled={answered}
                  onClick={() => onAnswer(state.index, option)}
                >
                  {option}
                </button>
              );
            })}
          </div>
          {answered ? (
            <div className="quiz-explanation">
              <div className="quiz-feedback">
                {selected === item.correct_answer ? "Correct." : `Correct answer: ${item.correct_answer}`}
              </div>
              <strong>Why:</strong> {item.explanation}
            </div>
          ) : null}
        </section>
      );
    }

    const revealed = Boolean(state.revealed[state.index]);
    return (
      <section className="practice-item">
        <h3>{item.prompt}</h3>
        <textarea
          className="textarea written-answer"
          value={state.writtenDrafts[state.index] || ""}
          onChange={(event) => onWrittenChange(state.index, event.currentTarget.value)}
          placeholder="Draft your answer here. It is not saved."
        />
        <button className="modal-button primary" type="button" onClick={() => onReveal(state.index)}>
          {revealed ? "Hide model answer" : "Reveal model answer"}
        </button>
        {revealed ? (
          <div className="written-review">
            <div>
              <div className="flashcard-label">Model answer</div>
              <p>{item.model_answer}</p>
            </div>
            <div>
              <div className="flashcard-label">Rubric</div>
              <p>{item.rubric}</p>
            </div>
          </div>
        ) : null}
      </section>
    );
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        ref={dialogRef}
        className="modal practice-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="study-set-title"
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <div>
            <div id="study-set-title" className="chat-title">
              {state.data?.title || "Study Set"}
            </div>
            <div className="header-subtitle">
              {state.loading
                ? "Building and saving your study set."
                : state.error
                  ? "Study set generation failed."
                  : `${getStudySetLabel(state.data?.type)} from ${state.data?.source_filename || "your source"}${createdAt ? ` • ${createdAt}` : ""}`}
            </div>
          </div>
          <button className="modal-close" type="button" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="modal-body">
          {state.loading ? (
            <div className="empty-state">Generating and saving...</div>
          ) : state.error ? (
            <div className="empty-state error-text">{state.error}</div>
          ) : items.length ? (
            <>
              <div className="practice-progress">
                <span className="micro-pill">{currentItem?.type || "item"}</span>
                <span>
                  {state.index + 1} / {items.length}
                </span>
              </div>
              {renderItem(currentItem)}
              <div className="flashcard-controls">
                <button className="modal-button" type="button" onClick={onPrev} disabled={state.index === 0}>
                  Back
                </button>
                {currentItem?.type === "flashcard" ? (
                  <button className="modal-button" type="button" onClick={onFlip}>
                    Flip
                  </button>
                ) : null}
                <button
                  className="modal-button primary"
                  type="button"
                  onClick={onNext}
                  disabled={state.index >= items.length - 1}
                >
                  Next
                </button>
              </div>
            </>
          ) : (
            <div className="empty-state">No study items returned.</div>
          )}
        </div>
      </div>
    </div>
  );
}
