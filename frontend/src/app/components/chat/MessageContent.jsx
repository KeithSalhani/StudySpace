import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function MessageContent({ message }) {
  if (message.type === "user") {
    return <div className="message-body">{message.content}</div>;
  }

  return (
    <div className="message-body message-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node: _node, ...props }) => <a {...props} target="_blank" rel="noreferrer" />,
        }}
      >
        {message.content}
      </ReactMarkdown>
    </div>
  );
}
