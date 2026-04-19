import { useDialog } from "../../hooks/useDialog";

export default function FlashcardModal({ state, onClose, onFlip, onPrev, onNext }) {
  const cards = state.data?.cards || [];
  const currentCard = cards[state.index];
  const dialogRef = useDialog(true, onClose);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        ref={dialogRef}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="flashcards-title"
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <div>
            <div id="flashcards-title" className="chat-title">
              {state.data?.title || "Flashcards"}
            </div>
            <div className="header-subtitle">
              {state.loading
                ? "Cooking up a fresh flashcard deck from the selected source."
                : state.error
                  ? "Flashcard generation failed."
                  : "Tap the card to flip between prompt and answer."}
            </div>
          </div>
          <button className="modal-close" type="button" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="modal-body">
          {state.loading ? (
            <div className="empty-state">Building the deck...</div>
          ) : state.error ? (
            <div className="empty-state error-text">{state.error}</div>
          ) : currentCard ? (
            <>
              <button
                className="flashcard"
                type="button"
                onClick={onFlip}
                aria-label={`Flip flashcard ${state.index + 1} of ${cards.length}`}
              >
                <div>
                  <div className="flashcard-label">
                    {state.side === "front" ? "Prompt" : "Answer"}
                  </div>
                  <div className="flashcard-text">
                    {state.side === "front" ? currentCard.front : currentCard.back}
                  </div>
                </div>
              </button>
              <div className="flashcard-controls">
                <button
                  className="modal-button"
                  type="button"
                  onClick={onPrev}
                  disabled={state.index === 0}
                >
                  Back
                </button>
                <div className="flashcard-meta">
                  {state.index + 1} / {cards.length}
                </div>
                <button className="modal-button" type="button" onClick={onFlip}>
                  Flip
                </button>
                <button
                  className="modal-button primary"
                  type="button"
                  onClick={onNext}
                  disabled={state.index >= cards.length - 1}
                >
                  Next
                </button>
              </div>
            </>
          ) : (
            <div className="empty-state">No flashcards returned.</div>
          )}
        </div>
      </div>
    </div>
  );
}
