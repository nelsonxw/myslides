/**
 * MySlides - Main Application
 *
 * AI-Powered Slide Builder from Curated Templates
 */
import React, { useState, Component, useCallback } from 'react';
import PromptInterface from './components/PromptInterface';
import SuggestionPreviewPanel from './components/SuggestionPreviewPanel';
import EditingPanel from './components/EditingPanel';
import CuratedSlidesCatalog from './components/CuratedSlidesCatalog';
import { api } from './api/client';
import './App.css';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-fallback-card">
          <h2>Application Notice</h2>
          <p>{this.state.error?.message || 'An unexpected display error occurred.'}</p>
          <button
            className="btn btn-primary"
            onClick={() => {
              this.setState({ hasError: false, error: null });
              if (this.props.onReset) this.props.onReset();
            }}
          >
            Return to Generator
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

function App() {
  const [activeTab, setActiveTab] = useState('prompt');
  const [parsedIntent, setParsedIntent] = useState(null);
  const [_selectedTemplate, setSelectedTemplate] = useState(null);
  const [generatedSlide, setGeneratedSlide] = useState(null);

  const handlePromptParsed = useCallback((intent) => {
    setParsedIntent(intent);
    setActiveTab('suggestions');
  }, []);

  const handleTemplateSelected = useCallback((template) => {
    setSelectedTemplate(template);
  }, []);

  const handleSlideGenerated = useCallback((slideData, navigateToEdit = true) => {
    setGeneratedSlide(slideData);
    if (navigateToEdit) {
      setActiveTab('edit');
    }
  }, []);

  const handleRegenerate = useCallback((newSlideData) => {
    setGeneratedSlide(newSlideData);
  }, []);

  const handleDownload = useCallback(async (requestId) => {
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
  }, []);

  const handleOpenEditor = useCallback(() => {
    setActiveTab('edit');
  }, []);

  const handleReset = useCallback(() => {
    setActiveTab('prompt');
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>MySlides</h1>
        <p>AI-Powered Slide Builder from Curated Templates</p>
      </header>

      <nav className="app-nav">
        <button
          className={`nav-tab ${activeTab === 'prompt' ? 'active' : ''}`}
          onClick={() => setActiveTab('prompt')}
        >
          Generate
        </button>
        <button
          className={`nav-tab ${activeTab === 'catalog' ? 'active' : ''}`}
          onClick={() => setActiveTab('catalog')}
        >
          Curated Slides
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
      </nav>

      <main className="app-main">
        <ErrorBoundary onReset={handleReset}>
          {activeTab === 'prompt' && (
            <PromptInterface
              onPromptParsed={handlePromptParsed}
            />
          )}

          {activeTab === 'catalog' && (
            <CuratedSlidesCatalog />
          )}

          {activeTab === 'suggestions' && (
            <SuggestionPreviewPanel
              parsedIntent={parsedIntent}
              onTemplateSelected={handleTemplateSelected}
              onSlideGenerated={handleSlideGenerated}
              onOpenEditor={handleOpenEditor}
            />
          )}

          {activeTab === 'edit' && (
            <EditingPanel
              generatedSlide={generatedSlide}
              onRegenerate={handleRegenerate}
              onDownload={handleDownload}
            />
          )}
        </ErrorBoundary>
      </main>

      <footer className="app-footer">
        <p>MySlides v2.0.0 - Phase 2</p>
      </footer>
    </div>
  );
}

export default App;
