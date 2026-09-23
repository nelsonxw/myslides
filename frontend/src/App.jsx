/**
 * MySlides - Main Application
 *
 * AI-Powered Slide Builder from Curated Templates
 */
import React, { useState } from 'react';
import UploadInterface from './components/UploadInterface';
import PromptInterface from './components/PromptInterface';
import SuggestionPreviewPanel from './components/SuggestionPreviewPanel';
import EditingPanel from './components/EditingPanel';
import DeckBuilder from './components/DeckBuilder';
import { api } from './api/client';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('upload');
  const [parsedIntent, setParsedIntent] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [generatedSlide, setGeneratedSlide] = useState(null);
  const [deckId, setDeckId] = useState(null);

  const handleUploadComplete = (data) => {
    console.log('Upload complete:', data);
  };

  const handlePromptParsed = (intent) => {
    setParsedIntent(intent);
    setActiveTab('suggestions');
  };

  const handleTemplateSelected = (template) => {
    setSelectedTemplate(template);
  };

  const handleSlideGenerated = (slideData) => {
    setGeneratedSlide(slideData);
    setActiveTab('edit');
  };

  const handleDeckGenerated = (deckData) => {
    setDeckId(deckData.deck_id);
    setActiveTab('deck');
  };

  const handleRegenerate = (newSlideData) => {
    setGeneratedSlide(newSlideData);
  };

  const handleDownload = async (requestId) => {
    try {
      const response = await api.downloadSlide(requestId);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'generated_slide.pptx');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Failed to download slide:', error);
    }
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
        <button
          className={`nav-tab ${activeTab === 'edit' ? 'active' : ''}`}
          onClick={() => setActiveTab('edit')}
          disabled={!generatedSlide}
        >
          Edit
        </button>
        <button
          className={`nav-tab ${activeTab === 'deck' ? 'active' : ''}`}
          onClick={() => setActiveTab('deck')}
          disabled={!deckId}
        >
          Deck
        </button>
      </nav>

      <main className="app-main">
        {activeTab === 'upload' && (
          <UploadInterface onUploadComplete={handleUploadComplete} />
        )}

        {activeTab === 'prompt' && (
          <PromptInterface
            onPromptParsed={handlePromptParsed}
            onSlideGenerated={handleSlideGenerated}
            onDeckGenerated={handleDeckGenerated}
          />
        )}

        {activeTab === 'suggestions' && (
          <SuggestionPreviewPanel
            parsedIntent={parsedIntent}
            onTemplateSelected={handleTemplateSelected}
            onSlideGenerated={handleSlideGenerated}
          />
        )}

        {activeTab === 'edit' && (
          <EditingPanel
            generatedSlide={generatedSlide}
            onRegenerate={handleRegenerate}
            onDownload={handleDownload}
          />
        )}

        {activeTab === 'deck' && (
          <DeckBuilder
            deckId={deckId}
            onDeckExported={() => console.log('Deck exported')}
          />
        )}
      </main>

      <footer className="app-footer">
        <p>MySlides v2.0.0 - Phase 2</p>
      </footer>
    </div>
  );
}

export default App;
