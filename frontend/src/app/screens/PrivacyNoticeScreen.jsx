import { PRIVACY_CONTACT_EMAIL } from "../constants";

export default function PrivacyNoticeScreen({ authenticated, username, onClose }) {
  return (
    <div className="auth-shell privacy-shell">
      <div className="app-noise" />
      <div className="orb orb-one" />
      <div className="orb orb-two" />
      <div className="orb orb-three" />
      <section className="privacy-panel glass-panel">
        <div className="privacy-header">
          <div>
            <div className="auth-kicker">Legal</div>
            <h1>Privacy Notice</h1>
            <p className="auth-copy">
              This notice explains what Study Space stores, how it uses that data, and how you can exercise your GDPR rights.
            </p>
          </div>
          <button className="small-button" type="button" onClick={onClose}>
            {authenticated ? "Back to workspace" : "Back"}
          </button>
        </div>

        <div className="privacy-grid">
          <section className="privacy-section">
            <h2>Who controls your data</h2>
            <p>
              Study Space is operated by Keith Salhani. For privacy questions or GDPR requests, contact{" "}
              <a href={`mailto:${PRIVACY_CONTACT_EMAIL}`}>{PRIVACY_CONTACT_EMAIL}</a>.
            </p>
          </section>
          <section className="privacy-section">
            <h2>Data collected</h2>
            <p>
              Study Space stores your username, password hash and salt, session records, uploaded study files, processed document text,
              notes, tags, folders, saved generated study sets, exam papers, exam folder analyses, and document metadata used by search and study features.
            </p>
          </section>
          <section className="privacy-section">
            <h2>How your data is used</h2>
            <p>
              Data is used to authenticate your account, organize study material, provide chat, generate and revisit quizzes or flashcards, topic mining, and
              keep your workspace available across sessions.
            </p>
          </section>
          <section className="privacy-section">
            <h2>AI processing</h2>
            <p>
              When you use AI-powered features, relevant study content may be sent to the configured AI provider for processing. Search
              embeddings and retrieval data are stored locally by the app.
            </p>
          </section>
          <section className="privacy-section">
            <h2>Retention and local storage</h2>
            <p>
              Account data, including saved study sets, remains until you delete content or delete the account. Session records expire automatically. Theme and
              accessibility preferences are stored in your browser.
            </p>
          </section>
          <section className="privacy-section">
            <h2>Your rights</h2>
            <p>
              You can export your data, delete your account, and contact{" "}
              <a href={`mailto:${PRIVACY_CONTACT_EMAIL}`}>{PRIVACY_CONTACT_EMAIL}</a> to request correction or raise a privacy issue.
              {authenticated ? ` You are currently signed in as @${username}.` : ""}
            </p>
          </section>
        </div>

        {!authenticated ? (
          <div className="privacy-actions">
            <button className="small-button primary" type="button" onClick={() => { window.location.hash = "login"; }}>
              Sign in
            </button>
            <button className="small-button" type="button" onClick={() => { window.location.hash = "signup"; }}>
              Create account
            </button>
          </div>
        ) : null}
      </section>
    </div>
  );
}
