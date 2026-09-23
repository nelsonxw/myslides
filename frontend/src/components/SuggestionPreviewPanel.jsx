/**
 * Suggestion & Preview Panel Component (FR-5.3)
 *
 * Side-by-side view of suggested templates and generated slide preview.
 */
import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

function SuggestionPreviewPanel({ parsedIntent, onTemplateSelected, onSlideGenerated }) {
  const [suggestions, setSuggestions] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generatedSlide, setGeneratedSlide] = useState(null);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    if (parsedIntent) {
      fetchSuggestions();
    }
  }, [parsedIntent]);

  const fetchSuggestions = async () => {
    if (!parsedIntent) return;

    setLoading(true);
    try {
      const response = await api.suggestTemplates(
        parsedIntent.slide_type,
        parsedIntent.content,
        parsedIntent.tone,
        5,
        true
      );
      setSuggestions(response.data);

      if (response.data.length > 0) {
        setSelectedTemplate(response.data[0]);
        if (onTemplateSelected) {
          onTemplateSelected(response.data[0]);
        }
      }
    } catch (error) {
      console.error('Failed to fetch suggestions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTemplateClick = (template) => {
    setSelectedTemplate(template);
    if (onTemplateSelected) {
      onTemplateSelected(template);
    }
  };

  const handleGenerateFromTemplate = async () => {
    if (!selectedTemplate || !parsedIntent) return;

    setGenerating(true);
    try {
      const response = await api.createSlide(
        parsedIntent.slide_type,
        parsedIntent.content,
        parsedIntent.tone,
        selectedTemplate.template_id,
        parsedIntent.element_preferences,
        parsedIntent.color_preference
      );
      setGeneratedSlide(response.data);
      if (onSlideGenerated) {
        onSlideGenerated(response.data);
      }
    } catch (error) {
      console.error('Failed to generate slide:', error);
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async () => {
    if (!generatedSlide) return;

    try {
      const response = await api.downloadSlide(generatedSlide.request_id);
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
    <div className="suggestion-preview-panel">
      <div className="panel-header">
        <h2>Template Suggestions & Preview</h2>
      </div>

      <div className="panel-content">
        {/* Left Panel: Template Suggestions */}
        <div className="suggestions-panel">
          <h3>Suggested Templates</h3>
          {loading ? (
            <div className="loading">Loading suggestions...</div>
          ) : suggestions.length === 0 ? (
            <div className="empty-state">No suggestions available</div>
          ) : (
            <div className="suggestions-list">
              {suggestions.map((suggestion, index) => (
                <div
                  key={suggestion.template_id}
                  className={`suggestion-item ${selectedTemplate?.template_id === suggestion.template_id ? 'selected' : ''}`}
                  onClick={() => handleTemplateClick(suggestion)}
                >
                  <div className="suggestion-rank">#{suggestion.rank}</div>
                  <div className="suggestion-info">
                    <div className="suggestion-classification">
                      {suggestion.template_data.classification}
                    </div>
                    <div className="suggestion-score">
                      Score: {suggestion.similarity_score.toFixed(2)}
                    </div>
                    <div className="suggestion-reason">{suggestion.match_reason}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Panel: Preview */}
        <div className="preview-panel">
          <h3>Generated Slide Preview</h3>
          {generating ? (
            <div className="loading">Generating slide...</div>
          ) : generatedSlide ? (
            <div className="preview-content">
              <div className="preview-placeholder">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <line x1="9" y1="3" x2="9" y2="21" />
                </svg>
                <p>Slide generated successfully!</p>
                <button className="btn btn-primary" onClick={handleDownload}>
                  Download PPTX
                </button>
              </div>
            </div>
          ) : (
            <div className="preview-placeholder">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <line x1="9" y1="3" x2="9" y2="21" />
              </svg>
              <p>Select a template and generate to see preview</p>
            </div>
          )}

          {selectedTemplate && !generatedSlide && (
            <div className="generate-action">
              <button
                className="btn btn-primary"
                onClick={handleGenerateFromTemplate}
                disabled={generating}
              >
                {generating ? 'Generating...' : 'Generate with Selected Template'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default SuggestionPreviewPanel;
