import React from 'react';

export default function LandingPage({ onLogin, onSignUp }) {
  return (
    <div className="landing-shell">
      <div className="app-noise" />
      <div className="orb orb-one" />
      <div className="orb orb-two" />
      <div className="orb orb-three" />
      <div className="orb orb-four" />
      
      <header className="landing-topbar">
        <div className="topbar-brand">
          <div className="brand-mark">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
            </svg>
          </div>
          <div className="topbar-copy">
            <span className="eyebrow">Study Space</span>
          </div>
        </div>
        <div className="topbar-actions">
           <button className="small-button" type="button" onClick={onLogin}>Sign In</button>
           <button className="small-button primary" type="button" onClick={onSignUp}>Get Started</button>
        </div>
      </header>

      <main className="landing-main">
        <section className="landing-hero">
          <div className="hero-badge pulse-badge">✨ AI-Powered Learning</div>
          <h1 className="landing-title">Master your studies with <span className="text-gradient">active recall</span>.</h1>
          <p className="landing-subtitle">
            Upload your documents, generate smart flashcards, take AI-crafted quizzes, and chart your progress in a space built for deep focus.
          </p>
          <div className="hero-cta">
            <button className="large-button primary glow-button" type="button" onClick={onSignUp}>Start studying for free</button>
            <button className="large-button secondary-button" type="button" onClick={onLogin}>Login to your space</button>
          </div>
        </section>

        <section className="feature-grid">
           <div className="feature-card glass-panel">
             <div className="feature-icon">📚</div>
             <h3>Unified Workspace</h3>
             <p>Upload PDFs, slides, and notes. Instantly search across all your materials and extract precisely what you need.</p>
           </div>
           <div className="feature-card glass-panel">
             <div className="feature-icon">📝</div>
             <h3>Smart Quizzes</h3>
             <p>Our AI analyzes your documents to generate tailored quizzes, helping you practice active recall and lock in concepts.</p>
           </div>
           <div className="feature-card glass-panel">
             <div className="feature-icon">⚡️</div>
             <h3>Dynamic Flashcards</h3>
             <p>Cut your prep time in half with auto-generated flashcards that target your weak spots and reinforce key information.</p>
           </div>
        </section>
      </main>
    </div>
  );
}
