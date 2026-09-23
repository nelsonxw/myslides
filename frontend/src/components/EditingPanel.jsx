/**
 * Editing Panel Component (FR-5.4)
 *
 * Post-generation inline editing for text, chart type, color scheme, and element count.
 */
import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

function EditingPanel({ generatedSlide, onRegenerate, onDownload }) {
  const [editedContent, setEditedContent] = useState(null);
  const [selectedPalette, setSelectedPalette] = useState(null);
  const [palettes, setPalettes] = useState([]);
  const [isRegenerating, setIsRegenerating] = useState(false);

  useEffect(() => {
    if (generatedSlide) {
      setEditedContent(JSON.parse(JSON.stringify(generatedSlide.content)));
    }
    loadPalettes();
  }, [generatedSlide]);

  const loadPalettes = async () => {
    try {
      const response = await api.listPalettes(20);
      setPalettes(response.data.palettes);
    } catch (error) {
      console.error('Failed to load palettes:', error);
    }
  };

  const handleContentChange = (path, value) => {
    setEditedContent((prev) => {
      const updated = { ...prev };
      const keys = path.split('.');
      let current = updated;
      for (let i = 0; i < keys.length - 1; i++) {
        current[keys[i]] = current[keys[i]] || {};
        current = current[keys[i]];
      }
      current[keys[keys.length - 1]] = value;
      return updated;
    });
  };

  const handleChartTypeChange = (newChartType) => {
    if (editedContent.chart_data) {
      handleContentChange('chart_data.chart_type', newChartType);
    }
  };

  const handleAddStep = () => {
    if (editedContent.steps) {
      const newStep = {
        number: editedContent.steps.length + 1,
        label: 'New Step',
        description: 'Description'
      };
      setEditedContent((prev) => ({
        ...prev,
        steps: [...prev.steps, newStep]
      }));
    }
  };

  const handleRemoveStep = (index) => {
    if (editedContent.steps && editedContent.steps.length > 1) {
      setEditedContent((prev) => ({
        ...prev,
        steps: prev.steps.filter((_, i) => i !== index).map((step, i) => ({
          ...step,
          number: i + 1
        }))
      }));
    }
  };

  const handleRegenerate = async () => {
    if (!generatedSlide) return;

    setIsRegenerating(true);
    try {
      const response = await api.createSlide(
        generatedSlide.slide_type,
        editedContent,
        generatedSlide.tone,
        generatedSlide.template_id,
        generatedSlide.element_preferences,
        selectedPalette || generatedSlide.color_preference
      );

      if (onRegenerate) {
        onRegenerate(response.data);
      }
    } catch (error) {
      console.error('Failed to regenerate slide:', error);
    } finally {
      setIsRegenerating(false);
    }
  };

  if (!generatedSlide) {
    return (
      <div className="editing-panel">
        <div className="empty-state">Generate a slide to enable editing</div>
      </div>
    );
  }

  return (
    <div className="editing-panel">
      <div className="panel-header">
        <h2>Edit Slide</h2>
        <div className="panel-actions">
          <button
            className="btn btn-secondary"
            onClick={handleRegenerate}
            disabled={isRegenerating}
          >
            {isRegenerating ? 'Regenerating...' : 'Regenerate'}
          </button>
          <button
            className="btn btn-primary"
            onClick={() => onDownload && onDownload(generatedSlide.request_id)}
          >
            Download PPTX
          </button>
        </div>
      </div>

      <div className="editing-content">
        {/* Text Content Editing */}
        <div className="edit-section">
          <h3>Content</h3>
          {editedContent.title !== undefined && (
            <div className="edit-field">
              <label>Title</label>
              <input
                type="text"
                value={editedContent.title || ''}
                onChange={(e) => handleContentChange('title', e.target.value)}
              />
            </div>
          )}
          {editedContent.subtitle !== undefined && (
            <div className="edit-field">
              <label>Subtitle</label>
              <input
                type="text"
                value={editedContent.subtitle || ''}
                onChange={(e) => handleContentChange('subtitle', e.target.value)}
              />
            </div>
          )}
        </div>

        {/* Chart Type Editing */}
        {editedContent.chart_data && (
          <div className="edit-section">
            <h3>Chart Type</h3>
            <div className="chart-type-selector">
              {['bar_vertical', 'bar_horizontal', 'pie', 'line'].map((type) => (
                <button
                  key={type}
                  className={`chart-type-btn ${editedContent.chart_data.chart_type === type ? 'active' : ''}`}
                  onClick={() => handleChartTypeChange(type)}
                >
                  {type.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Process Flow Steps Editing */}
        {editedContent.steps && (
          <div className="edit-section">
            <h3>Steps</h3>
            <div className="steps-editor">
              {editedContent.steps.map((step, index) => (
                <div key={index} className="step-item">
                  <div className="step-number">{step.number}</div>
                  <div className="step-fields">
                    <input
                      type="text"
                      value={step.label || ''}
                      onChange={(e) => handleContentChange(`steps.${index}.label`, e.target.value)}
                      placeholder="Step label"
                    />
                    <textarea
                      value={step.description || ''}
                      onChange={(e) => handleContentChange(`steps.${index}.description`, e.target.value)}
                      placeholder="Description"
                      rows={2}
                    />
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => handleRemoveStep(index)}
                      disabled={editedContent.steps.length <= 1}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
              <button className="btn btn-secondary" onClick={handleAddStep}>
                + Add Step
              </button>
            </div>
          </div>
        )}

        {/* Timeline Milestones Editing */}
        {editedContent.milestones && (
          <div className="edit-section">
            <h3>Milestones</h3>
            <div className="milestones-editor">
              {editedContent.milestones.map((milestone, index) => (
                <div key={index} className="milestone-item">
                  <input
                    type="text"
                    value={milestone.date || ''}
                    onChange={(e) => handleContentChange(`milestones.${index}.date`, e.target.value)}
                    placeholder="Date"
                  />
                  <input
                    type="text"
                    value={milestone.label || ''}
                    onChange={(e) => handleContentChange(`milestones.${index}.label`, e.target.value)}
                    placeholder="Label"
                  />
                  <textarea
                    value={milestone.description || ''}
                    onChange={(e) => handleContentChange(`milestones.${index}.description`, e.target.value)}
                    placeholder="Description"
                    rows={2}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Bullet Points Editing */}
        {editedContent.bullet_points && (
          <div className="edit-section">
            <h3>Bullet Points</h3>
            <textarea
              value={editedContent.bullet_points.join('\n')}
              onChange={(e) => handleContentChange('bullet_points', e.target.value.split('\n').filter(b => b.trim()))}
              rows={6}
              placeholder="One bullet point per line"
            />
          </div>
        )}

        {/* Color Palette Selection */}
        <div className="edit-section">
          <h3>Color Palette</h3>
          <div className="palette-selector">
            <button
              className={`palette-btn ${!selectedPalette ? 'active' : ''}`}
              onClick={() => setSelectedPalette(null)}
            >
              Original
            </button>
            {palettes.slice(0, 10).map((palette, index) => (
              <button
                key={index}
                className={`palette-btn ${selectedPalette === palette.colors ? 'active' : ''}`}
                onClick={() => setSelectedPalette(palette.colors)}
              >
                <div className="palette-preview">
                  {palette.colors?.slice(0, 4).map((color, i) => (
                    <div
                      key={i}
                      className="palette-swatch"
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default EditingPanel;
