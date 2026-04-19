import MessageContent from "./MessageContent";
import RetrievalTrace from "./RetrievalTrace";
import { dedupeSources } from "../../utils";

export default function ChatMessageCard({ message }) {
  const hasSources = dedupeSources(message.sources).length > 0;
  const showTrace = message.type === "bot";
  const displayContent =
    message.type === "bot" && message.status === "running" && !message.content
      ? "Working through your material..."
      : message.content;

  return (
    <article className={`message ${message.type} ${message.status === "running" ? "pending" : ""}`}>
      <div className="message-sender">{message.type === "user" ? "You" : "Study Space"}</div>
      <MessageContent message={{ ...message, content: displayContent }} />
      {showTrace ? <RetrievalTrace message={message} /> : null}
      {hasSources ? (
        <div className="sources">
          <div className="source-list-label">Evidence used</div>
          <div className="source-pills">
            {dedupeSources(message.sources).map((source, index) => (
              <span
                key={`${message.id}-${source.filename || source.source || index}`}
                className="source-pill"
              >
                {source.source_id ? `${source.source_id} • ` : ""}
                {source.filename || source.source || "Unknown source"}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </article>
  );
}
