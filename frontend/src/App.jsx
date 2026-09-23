/**
 * MySlides - Main Application
 *
 * AI-Powered Slide Builder from Curated Templates
 */
import React, { useState } from 'react';
import UploadInterface from './components/UploadInterface';
import PromptInterface from './components/PromptInterface';
import SuggestionPreviewPanel from './components/SuggestionPreviewPanel';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('upload');
  const [parsedIntent, setParsedIntent] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState(null);

  const handleUploadComplete = (data) => {
    console.log('Upload complete:', data);
    // Could switch to templates view or show success message
  };

  const handlePromptParsed = (intent) => {
    setParsedIntent(intent);
    setActiveTab('suggestions');
  };

  const handleTemplateSelected = (template) => {
    setSelectedTemplate(template);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>MySlides</h1>
        <p>AI-Powered Slide Builder from Curated Templates</p>
      </header>

      <nav className="app-nav">
        <button
          className={`nav-tab ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab('upload')}
        >
          Upload
        </button>
        <button
          className={`nav-tab ${activeTab === 'prompt' ? 'active' : ''}`}
          onClick={() => setActiveTab('prompt')}
        >
          Generate
        </button>
        <button
          className={`nav-tab ${activeTab === 'suggestions' ? 'active' : ''}`}
          onClick={() => setActiveTab('suggestions')}
          disabled={!parsedIntent}
        >
          Suggestions
        </button>
      </nav>

      <main className="app-main">
        {activeTab === 'upload' && (
          <UploadInterface onUploadComplete={handleUploadComplete} />
        )}

        {activeTab === 'prompt' && (
          <PromptInterface
            onPromptParsed={handlePromptParsed}
          />
        )}

        {activeTab === 'suggestions' && (
          <SuggestionPreviewPanel
            parsedIntent={parsedIntent}
            onTemplateSelected={handleTemplateSelected}
          />
        )}
      </main>

      <footer className="app-footer">
        <p>MySlides v1.0.0 - Module 5 MVP</p>
      </footer>
    </div>
  );
}

export default App;
