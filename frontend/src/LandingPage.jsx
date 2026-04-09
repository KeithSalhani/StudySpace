import React from 'react';

export default function LandingPage({ onLogin, onSignUp }) {
  return (
    <div className="landing-shell">
      <header className="landing-topbar">
        <div className="topbar-brand">

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
        <section className="landing-hero clean-hero">
          <div className="hero-badge">Active Recall Platform</div>
          <h1 className="landing-title">Master your studies with precision.</h1>
          <p className="landing-subtitle">
            A centralized workspace for your documents, automated quizzes, and targeted flashcards. Built to optimize focus and retention.
          </p>
          <div className="hero-cta">
            <button className="large-button primary" type="button" onClick={onSignUp}>Start learning</button>
            <button className="large-button secondary-button" type="button" onClick={onLogin}>Sign In</button>
          </div>
        </section>

        <section className="feature-grid">
           <div className="feature-card">
             <div className="feature-icon-svg">
               <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                 <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
                 <path d="M3 5V19A9 3 0 0 0 21 19V5"></path>
                 <path d="M3 12A9 3 0 0 0 21 12"></path>
               </svg>
             </div>
             <h3>Unified Workspace</h3>
             <p>Upload PDFs, slides, and notes. Instantly search across all your materials and extract precisely what you need.</p>
           </div>
           <div className="feature-card">
             <div className="feature-icon-svg">
               <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                 <polyline points="9 11 12 14 22 4"></polyline>
                 <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
               </svg>
             </div>
             <h3>Targeted Quizzes</h3>
             <p>Test your knowledge with algorithmically generated quizzes designed strictly to reinforce core concepts from your materials.</p>
           </div>
           <div className="feature-card">
             <div className="feature-icon-svg">
               <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                 <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                 <line x1="3" y1="9" x2="21" y2="9"></line>
                 <line x1="9" y1="21" x2="9" y2="9"></line>
               </svg>
             </div>
             <h3>Dynamic Flashcards</h3>
             <p>Cut your prep time down safely with focused flashcard generation that targets your weak spots and reinforces key information.</p>
           </div>
        </section>
      </main>
    </div>
  );
}
