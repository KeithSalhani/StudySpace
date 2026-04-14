import React from 'react';

export default function AuthScreen({
  mode,
  form,
  busy,
  error,
  onChange,
  onSubmit,
  onToggleMode
}) {
  const isSignUp = mode === "signup";

  return (
    <div className="auth-shell">
      <div className="app-noise" />
      <div className="orb orb-one" />
      <div className="orb orb-two" />
      <div className="orb orb-three" />
      
      <div className="auth-card-container">
        <section className="auth-panel glass-panel">
          <div className="auth-hero-art">
             <div className="auth-hero-content">
               <div className="brand-mark large-brand-mark">
                  <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
                  </svg>
               </div>
               <h2>Study Space</h2>
               <p>Your AI-powered environment for active learning, deep focus, and better retention.</p>
             </div>
          </div>
          <div className="auth-form-container">
            <div className="auth-kicker">Private workspace</div>
            <h1>{isSignUp ? "Create account" : "Welcome back"}</h1>
            <p className="auth-copy">
              Log in to access your notes, quizzes, and chat context.
            </p>
            <form
              className="auth-form"
              onSubmit={(event) => {
                event.preventDefault();
                onSubmit();
              }}
            >
              <label className="auth-field">
                <span>Username</span>
                <input
                  className="input"
                  autoComplete="username"
                  value={form.username}
                  onChange={(event) => onChange("username", event.currentTarget.value)}
                  placeholder="your-name"
                />
              </label>
              <label className="auth-field">
                <span>Password</span>
                <input
                  className="input"
                  type="password"
                  autoComplete={isSignUp ? "new-password" : "current-password"}
                  value={form.password}
                  onChange={(event) => onChange("password", event.currentTarget.value)}
                  placeholder="At least 8 characters"
                />
              </label>
              {error ? <div className="banner error-text">{error}</div> : null}
              <div className="auth-actions">
                <button className="small-button primary auth-submit" type="submit" disabled={busy}>
                  {busy ? "Working..." : isSignUp ? "Create account" : "Sign in"}
                </button>
                <button className="small-button text-button" type="button" onClick={onToggleMode} disabled={busy}>
                  {isSignUp ? "Already have an account? Sign in" : "Need an account? Sign up"}
                </button>
              </div>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
}
