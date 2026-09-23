/**
 * Prompt Interface Component (FR-5.2)
 *
 * Large text input area with example prompt suggestions and generate button.
 */
import React, { useState } from 'react';
import { api } from '../api/client';

const EXAMPLE_PROMPTS = [
  'Create a 3-step process flow for employee onboarding',
  'Build a comparison slide for Plan A vs Plan B pricing',
  'Show quarterly revenue as a bar chart with a trend line',
  'Make a timeline of our product milestones from 2020 to 2025',
  'Create a title slide for Q4 sales presentation',
];

function PromptInterface({ onPromptParsed, onSlideGenerated }) {
  const [promptText, setPromptText] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [parsedIntent, setParsedIntent] = useState(null);
  const [error, setError] = useState(null);

  const handlePromptChange = (e) => {
    setPromptText(e.target.value);
    setError(null);
  };

  const handleExampleClick = (example) => {
    setPromptText(example);
    setError(null);
  };

  const handleParse = async () => {
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

  const handleGenerate = async () => {
    if (!parsedIntent) {
      setError('Please parse the prompt first');
      return;
    }

    setIsGenerating(true);
    setError(null);

    try {
      const response = await api.createSlide(
        parsedIntent.slide_type,
        parsedIntent.content,
        parsedIntent.tone,
        null, // template_id
        parsedIntent.element_preferences,
        parsedIntent.color_preference
      );

      if (onSlideGenerated) {
        onSlideGenerated(response.data);
      }
    } catch (err) {
      setError('Failed to generate slide. Please try again.');
      console.error(err);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="prompt-interface">
      <div className="prompt-header">
        <h2>Generate Slides from Natural Language</h2>
        <p>Describe the slide you want to create, and we'll generate it for you.</p>
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
          className="btn btn-secondary"
          onClick={handleParse}
          disabled={isGenerating || !promptText.trim()}
        >
          {isGenerating ? 'Parsing...' : 'Parse Prompt'}
        </button>
        <button
          className="btn btn-primary"
          onClick={handleGenerate}
          disabled={isGenerating || !parsedIntent}
        >
          {isGenerating ? 'Generating...' : 'Generate Slide'}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {parsedIntent && (
        <div className="parsed-intent">
          <h3>Parsed Intent</h3>
          <pre>{JSON.stringify(parsedIntent, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default PromptInterface;
