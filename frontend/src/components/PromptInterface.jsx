/**
 * Prompt Interface Component (FR-5.2 & Slide Redesign)
 *
 * Supports generating slides from natural language prompts or uploading
 * an existing slide to analyze and suggest improved visual layouts.
 */
import React, { useState, useCallback } from 'react';
import { api } from '../api/client';

const EXAMPLE_PROMPTS = [
  'Create a 3-step process flow for employee onboarding',
  'Build a comparison slide for Plan A vs Plan B pricing',
  'Show quarterly revenue as a bar chart with a trend line',
  'Make a timeline of our product milestones from 2020 to 2025',
  'Create a title slide for Q4 sales presentation',
];

function PromptInterface({ onPromptParsed }) {
  const [mode, setMode] = useState('prompt'); // 'prompt' | 'improve'
  const [promptText, setPromptText] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [parsedIntent, setParsedIntent] = useState(null);
  const [error, setError] = useState(null);

  // Improve slide state
  const [selectedFile, setSelectedFile] = useState(null);
  const [improvementInstruction, setImprovementInstruction] = useState('');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  const handlePromptChange = (e) => {
    setPromptText(e.target.value);
    setError(null);
  };

  const handleExampleClick = (example) => {
    setPromptText(example);
    setError(null);
  };

  const handleGenerateSlide = async () => {
    if (!promptText.trim()) {
      setError('Please enter a prompt');
      return;
    }

    setIsGenerating(true);
    setError(null);

    try {
      const response = await api.parsePrompt(promptText);
      setParsedIntent(response.data);

      if (onPromptParsed) {
        onPromptParsed(response.data);
      }
    } catch (err) {
      setError('Failed to parse prompt. Please try again.');
      console.error(err);
    } finally {
      setIsGenerating(false);
    }
  };

  // Drag and drop handlers for existing slide upload
  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    setError(null);

    const files = Array.from(e.dataTransfer.files);
    const pptxFile = files.find((f) => f.name.endsWith('.pptx'));
    if (!pptxFile) {
      setError('Please upload a PowerPoint .pptx slide file.');
      return;
    }
    setSelectedFile(pptxFile);
    setAnalysisResult(null);
  }, []);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file && file.name.endsWith('.pptx')) {
      setSelectedFile(file);
      setAnalysisResult(null);
      setError(null);
    } else if (file) {
      setError('Please upload a PowerPoint .pptx slide file.');
    }
  };

  const handleAnalyzeSlide = async () => {
    if (!selectedFile) {
      setError('Please select a slide file to improve.');
      return;
    }

    setIsGenerating(true);
    setError(null);

    try {
      const response = await api.improveSlide(selectedFile, improvementInstruction);
      const data = response.data;
      setAnalysisResult(data);
      setParsedIntent(data.parsed_intent);

      if (onPromptParsed) {
        onPromptParsed(data.parsed_intent);
      }
    } catch (err) {
      setError('Failed to analyze slide. Please verify the PPTX file format.');
      console.error(err);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleApplyRecommendedType = (typeName) => {
    if (!analysisResult) return;
    const updatedIntent = {
      ...analysisResult.parsed_intent,
      slide_type: typeName,
    };
    setParsedIntent(updatedIntent);
    if (onPromptParsed) {
      onPromptParsed(updatedIntent);
    }
  };

  return (
    <div className="prompt-interface">
      <div className="generation-mode-switch">
        <button
          className={`mode-toggle ${mode === 'prompt' ? 'active' : ''}`}
          onClick={() => {
            setMode('prompt');
            setError(null);
          }}
        >
          Prompt to Slide
        </button>
        <button
          className={`mode-toggle ${mode === 'improve' ? 'active' : ''}`}
          onClick={() => {
            setMode('improve');
            setError(null);
          }}
        >
          Improve Existing Slide
        </button>
      </div>

      {mode === 'prompt' ? (
        <div className="mode-content">
          <div className="prompt-header">
            <h2>Generate Slides from Natural Language</h2>
            <p>Describe the slide you want to create, and we will generate it for you.</p>
          </div>

          <div className="prompt-input-section">
            <textarea
              className="prompt-textarea"
              placeholder="e.g., Create a 3-step process flow for employee onboarding"
              value={promptText}
              onChange={handlePromptChange}
              rows={4}
            />
          </div>

          <div className="example-prompts">
            <p className="example-label">Example prompts:</p>
            <div className="example-list">
              {EXAMPLE_PROMPTS.map((example, index) => (
                <button
                  key={index}
                  className="example-button"
                  onClick={() => handleExampleClick(example)}
                >
                  {example}
                </button>
              ))}
            </div>
          </div>

          <div className="prompt-actions">
            <button
              className="btn btn-primary"
              onClick={handleGenerateSlide}
              disabled={isGenerating || !promptText.trim()}
            >
              {isGenerating ? 'Generating Slide...' : 'Generate Slide'}
            </button>
          </div>
        </div>
      ) : (
        <div className="mode-content improve-slide-mode">
          <div className="prompt-header">
            <h2>Improve & Redesign Existing Slide</h2>
            <p>
              Upload a slide to extract its content, get layout recommendations, and match with curated templates.
            </p>
          </div>

          <div
            className={`slide-dropzone ${isDragging ? 'dragging' : ''} ${selectedFile ? 'has-file' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleFileDrop}
          >
            <input
              type="file"
              id="slide-file-input"
              accept=".pptx"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
            <label htmlFor="slide-file-input" className="slide-dropzone-label">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="12" y1="18" x2="12" y2="12" />
                <polyline points="9 15 12 12 15 15" />
              </svg>
              {selectedFile ? (
                <div className="selected-file-info">
                  <strong>{selectedFile.name}</strong>
                  <span>{(selectedFile.size / 1024).toFixed(1)} KB — Click or drop another to replace</span>
                </div>
              ) : (
                <div className="dropzone-text">
                  <p>Drag and drop your PPTX slide here, or <span>browse file</span></p>
                </div>
              )}
            </label>
          </div>

          <div className="prompt-input-section">
            <label className="input-label">Optional redesign instruction or preference:</label>
            <textarea
              className="prompt-textarea"
              placeholder="e.g., Turn bullet points into horizontal milestone cards, executive modern theme"
              value={improvementInstruction}
              onChange={(e) => setImprovementInstruction(e.target.value)}
              rows={2}
            />
          </div>

          <div className="prompt-actions">
            <button
              className="btn btn-primary"
              onClick={handleAnalyzeSlide}
              disabled={isGenerating || !selectedFile}
            >
              {isGenerating ? 'Analyzing Slide...' : 'Analyze & Suggest Better Layouts'}
            </button>
          </div>

          {analysisResult && (
            <div className="analysis-summary-card">
              <h3>Slide Analysis & Recommendations</h3>
              <div className="analysis-meta">
                <span className="analysis-tag">
                  Current Layout: <strong>{analysisResult.original_classification.replace('_', ' ')}</strong>
                </span>
                <span className="analysis-tag">
                  Extracted Title: <strong>{analysisResult.extracted_title}</strong>
                </span>
              </div>

              {analysisResult.extracted_items && analysisResult.extracted_items.length > 0 && (
                <div className="extracted-points">
                  <p className="points-label">Extracted Content Points:</p>
                  <ul>
                    {analysisResult.extracted_items.map((pt, i) => (
                      <li key={i}>{pt}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="recommended-layouts">
                <p className="points-label">Recommended Visual Layouts:</p>
                <div className="layout-chips">
                  {analysisResult.recommended_slide_types.map((type) => (
                    <button
                      key={type}
                      className={`layout-chip ${parsedIntent?.slide_type === type ? 'selected' : ''}`}
                      onClick={() => handleApplyRecommendedType(type)}
                    >
                      {type.replace('_', ' ')}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {error && <div className="error-message">{error}</div>}
    </div>
  );
}

export default PromptInterface;
