/**
 * Suggestion & Preview Panel Component (FR-5.3)
 *
 * Side-by-side view of detailed suggested templates and instant slide preview.
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';

function SuggestionPreviewPanel({
  parsedIntent,
  onTemplateSelected,
  onSlideGenerated,
  onOpenEditor,
}) {
  const [suggestions, setSuggestions] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generatedSlide, setGeneratedSlide] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('rendered'); // 'rendered' (1:1 PowerPoint PNG) | 'structure' (Interactive cards)

  // Stable references to prevent callback identity changes from triggering effect loops
  const onSlideGeneratedRef = useRef(onSlideGenerated);
  const onTemplateSelectedRef = useRef(onTemplateSelected);

  useEffect(() => {
    onSlideGeneratedRef.current = onSlideGenerated;
    onTemplateSelectedRef.current = onTemplateSelected;
  });

  const lastFetchedIntentKeyRef = useRef('');
  const isFetchingRef = useRef(false);
  const slideCacheRef = useRef({});

  const generateSlideFromTemplate = useCallback(
    async (template) => {
      if (!template || !parsedIntent) return;

      const templateId = template.template_id;

      // Use cached generated slide if available
      if (slideCacheRef.current[templateId]) {
        const cached = slideCacheRef.current[templateId];
        setGeneratedSlide(cached);
        if (onSlideGeneratedRef.current) {
          onSlideGeneratedRef.current(cached, false);
        }
        return;
      }

      setGenerating(true);
      setError(null);

      try {
        const response = await api.createSlide(
          parsedIntent.slide_type,
          parsedIntent.content,
          parsedIntent.tone,
          templateId,
          parsedIntent.element_preferences,
          parsedIntent.color_preference
        );

        const fullSlideData = {
          ...response.data,
          content: response.data.content || parsedIntent.content || {},
          slide_type: response.data.slide_type || parsedIntent.slide_type,
          template_id: templateId,
          selected_template: template,
        };

        slideCacheRef.current[templateId] = fullSlideData;
        setGeneratedSlide(fullSlideData);

        if (onSlideGeneratedRef.current) {
          onSlideGeneratedRef.current(fullSlideData, false);
        }
      } catch (err) {
        console.error('Failed to generate slide:', err);
        setError('Failed to generate slide preview. Please try again.');
      } finally {
        setGenerating(false);
      }
    },
    [parsedIntent]
  );

  const fetchSuggestions = useCallback(async () => {
    if (!parsedIntent || isFetchingRef.current) return;

    isFetchingRef.current = true;
    setLoading(true);
    setError(null);

    try {
      const response = await api.suggestTemplates(
        parsedIntent.slide_type,
        parsedIntent.content,
        parsedIntent.tone,
        5,
        true
      );

      const items = response.data || [];
      setSuggestions(items);

      if (items.length > 0) {
        const topTemplate = items[0];
        setSelectedTemplate(topTemplate);
        if (onTemplateSelectedRef.current) {
          onTemplateSelectedRef.current(topTemplate);
        }
        // Auto-generate preview immediately for the top-ranked suggestion
        await generateSlideFromTemplate(topTemplate);
      }
    } catch (err) {
      console.error('Failed to fetch suggestions:', err);
      setError('Could not fetch template suggestions.');
    } finally {
      setLoading(false);
      isFetchingRef.current = false;
    }
  }, [parsedIntent, generateSlideFromTemplate]);

  useEffect(() => {
    if (!parsedIntent) return;

    const intentKey = `${parsedIntent.slide_type}_${parsedIntent.content?.title || ''}_${(
      parsedIntent.content?.steps || []
    ).length}_${(parsedIntent.content?.items || []).length}`;

    if (lastFetchedIntentKeyRef.current === intentKey) {
      return;
    }
    lastFetchedIntentKeyRef.current = intentKey;
    fetchSuggestions();
  }, [parsedIntent, fetchSuggestions]);

  const handleTemplateClick = (template) => {
    setSelectedTemplate(template);
    if (onTemplateSelectedRef.current) {
      onTemplateSelectedRef.current(template);
    }
    generateSlideFromTemplate(template);
  };

  const handleDownload = async () => {
    if (!generatedSlide) return;

    try {
      const response = await api.downloadSlide(generatedSlide.request_id);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${generatedSlide.content?.title || 'generated_slide'}.pptx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error('Failed to download slide:', err);
    }
  };

  // Helper to extract clean filename
  const getTemplateFileName = (template) => {
    const raw =
      template?.template_data?.original_pptx_reference ||
      template?.template_data?.file_name ||
      '';
    return raw.replace(/^curated slides\//, '');
  };

  // Content for preview rendering
  const slideContent = generatedSlide?.content || parsedIntent?.content || {};
  const slideTitle = slideContent.title || 'Untitled Slide';
  const slideSubtitle = slideContent.subtitle || null;
  const primaryPalette =
    selectedTemplate?.template_data?.color_palette || ['#4f46e5', '#3b82f6', '#10b981'];

  return (
    <div className="suggestion-preview-panel">
      <div className="panel-header">
        <h2>Template Suggestions & Live Preview</h2>
        <p className="panel-subtitle">
          Matched from <strong>1,528 curated slides</strong> in Firebase Storage. Select any template
          to update the live preview.
        </p>
      </div>

      {error && <div className="catalog-error">{error}</div>}

      <div className="panel-content">
        {/* Left Panel: Template Suggestions */}
        <div className="suggestions-panel">
          <div className="suggestions-panel-header">
            <h3>Suggested Curated Templates</h3>
            <span className="suggestions-count">{suggestions.length} matched</span>
          </div>

          {loading ? (
            <div className="loading">Matching curated templates...</div>
          ) : suggestions.length === 0 ? (
            <div className="empty-state">No matching templates found</div>
          ) : (
            <div className="suggestions-list">
              {suggestions.map((suggestion) => {
                const isSelected = selectedTemplate?.template_id === suggestion.template_id;
                const fileName = getTemplateFileName(suggestion);
                const palette = suggestion.template_data?.color_palette || [];
                const tags = suggestion.template_data?.tags || [];

                return (
                  <div
                    key={suggestion.template_id}
                    className={`suggestion-card ${isSelected ? 'selected' : ''}`}
                    onClick={() => handleTemplateClick(suggestion)}
                  >
                    <div className="suggestion-card-top">
                      <span className="suggestion-rank-badge">#{suggestion.rank} Match</span>
                      <span className="suggestion-category-tag">
                        {suggestion.template_data?.classification || 'template'}
                      </span>
                      <span className="suggestion-score-badge">
                        Score: {(suggestion.similarity_score * 100).toFixed(0)}%
                      </span>
                    </div>

                    <h4 className="suggestion-title" title={fileName}>
                      {fileName || `Template ${suggestion.template_id}`}
                    </h4>

                    <p className="suggestion-reason-text">{suggestion.match_reason}</p>

                    {palette.length > 0 && (
                      <div className="palette-dots">
                        {palette.slice(0, 5).map((color, idx) => (
                          <span
                            key={idx}
                            className="palette-dot"
                            style={{ backgroundColor: color }}
                            title={color}
                          />
                        ))}
                      </div>
                    )}

                    {tags.length > 0 && (
                      <div className="suggestion-tags">
                        {tags.slice(0, 3).map((tag, i) => (
                          <span key={i} className="tag">
                            {tag}
                          </span>
                        ))}
                        {tags.length > 3 && <span className="tag-more">+{tags.length - 3}</span>}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Panel: Live Slide Preview */}
        <div className="preview-panel">
          <div className="preview-panel-header">
            <h3>Generated Slide Preview</h3>
            {generatedSlide && (
              <span className="preview-status-badge">Ready for Export</span>
            )}
          </div>

          {generating ? (
            <div className="generating-container">
              <div className="spinner" />
              <p>Assembling slide layout with curated template...</p>
            </div>
          ) : generatedSlide ? (
            <div className="live-slide-canvas">
              {/* Preview Mode Switcher */}
              <div className="preview-mode-switch">
                <button
                  className={`view-mode-btn ${viewMode === 'rendered' ? 'active' : ''}`}
                  onClick={() => setViewMode('rendered')}
                >
                  Exact PowerPoint Render (1:1 Output)
                </button>
                <button
                  className={`view-mode-btn ${viewMode === 'structure' ? 'active' : ''}`}
                  onClick={() => setViewMode('structure')}
                >
                  Interactive Structure View
                </button>
              </div>

              {viewMode === 'rendered' ? (
                <div className="slide-image-viewport">
                  <img
                    key={generatedSlide.request_id}
                    src={`http://127.0.0.1:8000/api/slides/${generatedSlide.request_id}/preview`}
                    alt="Exact PowerPoint Slide Preview"
                    className="slide-rendered-image"
                    onError={() => setViewMode('structure')}
                  />
                  <div className="slide-canvas-footer">
                    <span className="template-source-meta">
                      Curated Template: {getTemplateFileName(selectedTemplate) || 'Auto-matched'}
                    </span>
                  </div>
                </div>
              ) : (
                /* Visual Presentation Slide Canvas */
                <div
                  className="slide-viewport"
                  style={{ borderTop: `4px solid ${primaryPalette[0] || '#4f46e5'}` }}
                >
                  <div className="slide-canvas-header">
                    <h1 className="canvas-title">{slideTitle}</h1>
                    {slideSubtitle && <p className="canvas-subtitle">{slideSubtitle}</p>}
                  </div>

                  <div className="slide-canvas-body">
                    {/* Multi-Column Executive Cards Layout */}
                    {slideContent.columns && slideContent.columns.length > 0 && parsedIntent?.slide_type !== 'table_view' && (
                      <div className="preview-columns-grid">
                        {slideContent.columns.map((col, cIdx) => (
                          <div key={cIdx} className="preview-column-card">
                            <div
                              className="column-card-header"
                              style={{ backgroundColor: primaryPalette[cIdx % primaryPalette.length] || '#4f46e5' }}
                            >
                              <h4>{col.title}</h4>
                            </div>
                            <ul className="column-card-body">
                              {(col.points || []).map((pt, pIdx) => (
                                <li key={pIdx}>{pt}</li>
                              ))}
                            </ul>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Table Data Layout */}
                    {slideContent.table_data && (parsedIntent?.slide_type === 'table_view' || !slideContent.columns) && (
                      <div className="preview-table-container">
                        <table className="preview-table">
                          {slideContent.table_data.headers && slideContent.table_data.headers.length > 0 && (
                            <thead>
                              <tr style={{ backgroundColor: primaryPalette[0] || '#4f46e5' }}>
                                {slideContent.table_data.headers.map((h, i) => (
                                  <th key={i}>{h}</th>
                                ))}
                              </tr>
                            </thead>
                          )}
                          <tbody>
                            {(slideContent.table_data.rows || []).map((row, rIdx) => (
                              <tr key={rIdx} className={rIdx % 2 === 1 ? 'alt-row' : ''}>
                                {row.map((cell, cIdx) => (
                                  <td key={cIdx}>{cell}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {/* Step Flow Layout */}
                    {slideContent.steps && slideContent.steps.length > 0 && (
                      <div className="preview-steps-flow">
                        {slideContent.steps.map((step, idx) => (
                          <div key={idx} className="preview-step-card">
                            <div
                              className="step-badge"
                              style={{ backgroundColor: primaryPalette[idx % primaryPalette.length] || '#4f46e5' }}
                            >
                              {step.number || idx + 1}
                            </div>
                            <h4 className="step-title">{step.label || `Step ${idx + 1}`}</h4>
                            <p className="step-desc">{step.description || ''}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Milestones / Timeline Layout */}
                    {slideContent.milestones && slideContent.milestones.length > 0 && (
                      <div className="preview-timeline">
                        {slideContent.milestones.map((m, idx) => (
                          <div key={idx} className="preview-timeline-node">
                            <span
                              className="timeline-bullet"
                              style={{ backgroundColor: primaryPalette[0] || '#4f46e5' }}
                            />
                            <span className="timeline-date">{m.date}</span>
                            <strong className="timeline-label">{m.label}</strong>
                            <p className="timeline-desc">{m.description}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Key Items / Bullet Points Layout */}
                    {slideContent.items &&
                      slideContent.items.length > 0 &&
                      !slideContent.steps &&
                      !slideContent.milestones && (
                        <div className="preview-items-grid">
                          {slideContent.items.map((item, idx) => (
                            <div key={idx} className="preview-item-card">
                              <span
                                className="item-icon"
                                style={{ color: primaryPalette[0] || '#4f46e5' }}
                              >
                                ✓
                              </span>
                              <span className="item-text">{item}</span>
                            </div>
                          ))}
                        </div>
                      )}
                  </div>

                  <div className="slide-canvas-footer">
                    <span className="template-source-meta">
                      Curated Template: {getTemplateFileName(selectedTemplate) || 'Auto-matched'}
                    </span>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="preview-actions-bar">
                <button className="btn btn-primary" onClick={handleDownload}>
                  Download PPTX
                </button>
                {onOpenEditor && (
                  <button className="btn btn-secondary" onClick={onOpenEditor}>
                    Open in Editor
                  </button>
                )}
                <button
                  className="btn btn-outline"
                  onClick={() => generateSlideFromTemplate(selectedTemplate)}
                  disabled={generating}
                >
                  Regenerate
                </button>
              </div>
            </div>
          ) : (
            <div className="preview-placeholder">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <line x1="9" y1="3" x2="9" y2="21" />
              </svg>
              <p>Select a curated template to generate live preview</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default SuggestionPreviewPanel;
