import { PRIVACY_CONTACT_EMAIL } from "../../constants";
import { useDialog } from "../../hooks/useDialog";

export default function SettingsModal({
  onClose,
  onOpenPrivacyNotice,
  onExportAccount,
  onDeleteAccount,
  tags,
  tagDraft,
  onTagDraftChange,
  onAddTag,
  onDeleteTag,
  accessibility,
  onToggleAccessibility,
  voiceInputStatus,
  currentUsername,
  exportBusy,
  deleteBusy,
  deleteState,
  onDeleteStateChange,
}) {
  const dialogRef = useDialog(true, onClose);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        ref={dialogRef}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
        style={{ maxWidth: "600px" }}
      >
        <div className="modal-head">
          <div>
            <div id="settings-title" className="chat-title">Settings</div>
            <div className="header-subtitle">
              Manage topics, sections, and global workspace preferences.
            </div>
          </div>
          <button className="modal-close" type="button" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="modal-body">
          <section className="section">
            <div className="section-head">
              <div className="section-title">Topics</div>
              <div className="helper-text">{tags.length} active lens{tags.length === 1 ? "" : "es"}</div>
            </div>
            <p className="meta-text" style={{ marginBottom: "16px" }}>
              Topics act as academic filters for your documents and insights.
            </p>
            <div className="tags-wrap" style={{ marginBottom: "20px" }}>
              {tags.length ? (
                tags.map((tag) => (
                  <div key={tag} className="tag-chip">
                    <span>{tag}</span>
                    <button
                      type="button"
                      aria-label={`Delete ${tag}`}
                      onClick={() => void onDeleteTag(tag)}
                    >
                      ×
                    </button>
                  </div>
                ))
              ) : (
                <div className="empty-card compact">No topics yet.</div>
              )}
            </div>
            <div className="input-row">
              <input
                className="input"
                value={tagDraft}
                placeholder="Add a topic lens (e.g. AI, CS101)..."
                onChange={(event) => onTagDraftChange(event.currentTarget.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    void onAddTag();
                  }
                }}
              />
              <button
                className="small-button primary"
                type="button"
                onClick={() => void onAddTag()}
              >
                Add
              </button>
            </div>
          </section>

          <section className="section" style={{ marginTop: "32px" }}>
            <div className="section-head">
              <div className="section-title">Accessibility</div>
              <div className="helper-text">Opt-in</div>
            </div>
            <p className="meta-text" style={{ marginBottom: "16px" }}>
              Enable only the support features you want. Regular users keep the existing experience.
            </p>
            <div className="settings-toggle-list">
              <label className="settings-toggle">
                <div>
                  <div className="settings-toggle-title">Voice input for chat</div>
                  <div className="meta-text">
                    Show a microphone in the composer and convert speech to text.
                    {!voiceInputStatus.supported ? ` ${voiceInputStatus.reason}` : ""}
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={accessibility.voiceInput}
                  disabled={!voiceInputStatus.supported}
                  onChange={() => onToggleAccessibility("voiceInput")}
                />
              </label>
              <label className="settings-toggle">
                <div>
                  <div className="settings-toggle-title">Enhanced focus indicators</div>
                  <div className="meta-text">Use stronger outlines and control separation so keyboard focus stands out immediately.</div>
                </div>
                <input
                  type="checkbox"
                  checked={accessibility.enhancedFocus}
                  onChange={() => onToggleAccessibility("enhancedFocus")}
                />
              </label>
              <label className="settings-toggle">
                <div>
                  <div className="settings-toggle-title">Larger text and spacing</div>
                  <div className="meta-text">Increase reading comfort in chat, notes, and side panels.</div>
                </div>
                <input
                  type="checkbox"
                  checked={accessibility.largerText}
                  onChange={() => onToggleAccessibility("largerText")}
                />
              </label>
              <label className="settings-toggle">
                <div>
                  <div className="settings-toggle-title">Higher contrast surfaces</div>
                  <div className="meta-text">Use darker borders, brighter surfaces, and stronger text contrast across the workspace.</div>
                </div>
                <input
                  type="checkbox"
                  checked={accessibility.highContrast}
                  onChange={() => onToggleAccessibility("highContrast")}
                />
              </label>
              <label className="settings-toggle">
                <div>
                  <div className="settings-toggle-title">Reduce motion</div>
                  <div className="meta-text">Minimize animated transitions and pulsing effects.</div>
                </div>
                <input
                  type="checkbox"
                  checked={accessibility.reducedMotion}
                  onChange={() => onToggleAccessibility("reducedMotion")}
                />
              </label>
              <label className="settings-toggle">
                <div>
                  <div className="settings-toggle-title">Screen reader status updates</div>
                  <div className="meta-text">Announce uploads, chat progress, and generation events.</div>
                </div>
                <input
                  type="checkbox"
                  checked={accessibility.announceUpdates}
                  onChange={() => onToggleAccessibility("announceUpdates")}
                />
              </label>
            </div>
          </section>

          <section className="section" style={{ marginTop: "32px" }}>
            <div className="section-head">
              <div className="section-title">Privacy & GDPR</div>
              <div className="helper-text">Your rights</div>
            </div>
            <p className="meta-text" style={{ marginBottom: "16px" }}>
              Review the privacy notice, export your data, or permanently delete your account.
            </p>
            <div className="settings-card-stack">
              <div className="settings-action-card">
                <div>
                  <div className="settings-toggle-title">Privacy Notice</div>
                  <div className="meta-text">
                    Read what Study Space stores, how it is used, and how to contact{" "}
                    <a href={`mailto:${PRIVACY_CONTACT_EMAIL}`}>{PRIVACY_CONTACT_EMAIL}</a>.
                  </div>
                </div>
                <button className="small-button" type="button" onClick={onOpenPrivacyNotice}>
                  Open notice
                </button>
              </div>

              <div className="settings-action-card">
                <div>
                  <div className="settings-toggle-title">Export account data</div>
                  <div className="meta-text">
                    Download your account data, uploaded files, processed files, notes, folders, saved study sets, and related metadata as a ZIP.
                  </div>
                </div>
                <button className="small-button primary" type="button" onClick={() => void onExportAccount()} disabled={exportBusy}>
                  {exportBusy ? "Preparing..." : "Export my data"}
                </button>
              </div>

              <div className="settings-danger-card">
                <div>
                  <div className="settings-toggle-title">Delete account</div>
                  <div className="meta-text">
                    Permanently remove <strong>@{currentUsername}</strong> and all associated files, metadata, notes, and saved study sets. This cannot be undone.
                  </div>
                </div>
                <div className="settings-delete-grid">
                  <label className="auth-field">
                    <span>Confirm username</span>
                    <input
                      className="input"
                      value={deleteState.username}
                      onChange={(event) => onDeleteStateChange("username", event.currentTarget.value)}
                      placeholder={currentUsername}
                    />
                  </label>
                  <label className="auth-field">
                    <span>Password</span>
                    <input
                      className="input"
                      type="password"
                      value={deleteState.password}
                      onChange={(event) => onDeleteStateChange("password", event.currentTarget.value)}
                      placeholder="Current password"
                    />
                  </label>
                </div>
                <div className="meta-text">
                  If you need help with a GDPR request, contact{" "}
                  <a href={`mailto:${PRIVACY_CONTACT_EMAIL}`}>{PRIVACY_CONTACT_EMAIL}</a>.
                </div>
                <div className="settings-danger-actions">
                  <button
                    className="small-button danger-button"
                    type="button"
                    onClick={() => void onDeleteAccount()}
                    disabled={deleteBusy || !deleteState.username.trim() || !deleteState.password}
                  >
                    {deleteBusy ? "Deleting..." : "Delete account"}
                  </button>
                </div>
              </div>
            </div>
          </section>
        </div>
        <div className="modal-footer" style={{ marginTop: "20px", display: "flex", justifyContent: "flex-end" }}>
          <button className="small-button primary" onClick={onClose}>Done</button>
        </div>
      </div>
    </div>
  );
}
