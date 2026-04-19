import { useDialog } from "../../hooks/useDialog";

export default function QuizModal({ state, onClose, onAnswer }) {
  const questions = state.data?.questions || [];
  const dialogRef = useDialog(true, onClose);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        ref={dialogRef}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="quiz-title"
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <div>
            <div id="quiz-title" className="chat-title">{state.data?.title || "Quiz"}</div>
            <div className="header-subtitle">
              {state.loading
                ? "Building a question set from the selected source."
                : state.error
                  ? "Quiz generation failed."
                  : "Lock in an answer to reveal the explanation."}
            </div>
          </div>
          <button className="modal-close" type="button" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="modal-body">
          {state.loading ? (
            <div className="empty-state">Generating quiz questions...</div>
          ) : state.error ? (
            <div className="empty-state error-text">{state.error}</div>
          ) : questions.length ? (
            questions.map((question, index) => {
              const selected = state.answers[index];

              return (
                <section key={`${question.question}-${index}`} className="quiz-question">
                  <h3>
                    {index + 1}. {question.question}
                  </h3>
                  <div className="quiz-options">
                    {(question.options || []).map((option) => {
                      const answered = selected !== undefined;
                      const classNames = ["quiz-option"];

                      if (selected === option) {
                        classNames.push("selected");
                      }
                      if (answered && option === question.correct_answer) {
                        classNames.push("correct");
                      } else if (answered && selected === option && option !== question.correct_answer) {
                        classNames.push("incorrect");
                      }

                      return (
                        <button
                          key={option}
                          className={classNames.join(" ")}
                          type="button"
                          disabled={answered}
                          onClick={() => onAnswer(index, option)}
                        >
                          {option}
                        </button>
                      );
                    })}
                  </div>
                  {selected !== undefined ? (
                    <div className="quiz-explanation">
                      <div className="quiz-feedback">
                        {selected === question.correct_answer
                          ? "Locked in. Correct."
                          : `You picked: ${selected}`}
                      </div>
                      <strong>Why:</strong> {question.explanation}
                    </div>
                  ) : null}
                </section>
              );
            })
          ) : (
            <div className="empty-state">No quiz questions returned.</div>
          )}
        </div>
      </div>
    </div>
  );
}
