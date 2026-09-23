/**
 * Deck Builder & Slide Sorter Canvas Component (FR-5.5)
 *
 * Multi-slide thumbnail sorter with drag-and-drop reordering,
 * add/duplicate/delete slides, and deck export.
 */
import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

function DeckBuilder({ deckId, onDeckExported }) {
  const [deck, setDeck] = useState(null);
  const [slides, setSlides] = useState([]);
  const [loading, setLoading] = useState(false);
  const [draggedIndex, setDraggedIndex] = useState(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (deckId) {
      loadDeck();
    }
  }, [deckId]);

  const loadDeck = async () => {
    if (!deckId) return;

    setLoading(true);
    try {
      const response = await api.getDeck(deckId);
      setDeck(response.data);
      setSlides(response.data.slides || []);
    } catch (error) {
      console.error('Failed to load deck:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDragStart = (e, index) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e, dropIndex) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === dropIndex) return;

    const newSlides = [...slides];
    const [draggedSlide] = newSlides.splice(draggedIndex, 1);
    newSlides.splice(dropIndex, 0, draggedSlide);

    setSlides(newSlides);
    setDraggedIndex(null);
    saveDeckOrder(newSlides);
  };

  const saveDeckOrder = async (newSlides) => {
    try {
      await api.updateDeck(deckId, { slides: newSlides });
    } catch (error) {
      console.error('Failed to save deck order:', error);
    }
  };

  const handleAddSlide = () => {
    const newSlide = {
      id: null,
      title: 'New Slide',
      type: 'content_slide',
      content: { title: 'New Slide' }
    };
    setSlides([...slides, newSlide]);
  };

  const handleDuplicateSlide = (index) => {
    const slideToDuplicate = slides[index];
    const duplicatedSlide = {
      ...slideToDuplicate,
      id: null,
      title: `${slideToDuplicate.title} (Copy)`
    };
    const newSlides = [...slides];
    newSlides.splice(index + 1, 0, duplicatedSlide);
    setSlides(newSlides);
  };

  const handleDeleteSlide = (index) => {
    if (slides.length <= 1) {
      alert('Deck must have at least one slide');
      return;
    }
    const newSlides = slides.filter((_, i) => i !== index);
    setSlides(newSlides);
    saveDeckOrder(newSlides);
  };

  const handleExportDeck = async () => {
    if (!deckId) return;

    setExporting(true);
    try {
      const response = await api.downloadDeck(deckId);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${deck.title || 'deck'}.pptx`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      if (onDeckExported) {
        onDeckExported();
      }
    } catch (error) {
      console.error('Failed to export deck:', error);
    } finally {
      setExporting(false);
    }
  };

  if (loading) {
    return <div className="deck-builder loading">Loading deck...</div>;
  }

  if (!deck && !deckId) {
    return (
      <div className="deck-builder">
        <div className="empty-state">
          <h3>No Deck Selected</h3>
          <p>Generate a multi-slide deck to use the deck builder</p>
        </div>
      </div>
    );
  }

  return (
    <div className="deck-builder">
      <div className="deck-header">
        <h2>Deck Builder</h2>
        {deck && <h3>{deck.title || 'Untitled Deck'}</h3>}
        <div className="deck-actions">
          <button className="btn btn-secondary" onClick={handleAddSlide}>
            + Add Slide
          </button>
          <button
            className="btn btn-primary"
            onClick={handleExportDeck}
            disabled={exporting || slides.length === 0}
          >
            {exporting ? 'Exporting...' : 'Export Deck'}
          </button>
        </div>
      </div>

      <div className="slide-sorter">
        {slides.map((slide, index) => (
          <div
            key={slide.id || index}
            className={`slide-thumbnail ${draggedIndex === index ? 'dragging' : ''}`}
            draggable
            onDragStart={(e) => handleDragStart(e, index)}
            onDragOver={handleDragOver}
            onDrop={(e) => handleDrop(e, index)}
          >
            <div className="slide-number">{index + 1}</div>
            <div className="slide-preview">
              <svg width="80" height="60" viewBox="0 0 24 24" fill="none" stroke="#ccc" strokeWidth="1">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <line x1="9" y1="3" x2="9" y2="21" />
              </svg>
            </div>
            <div className="slide-info">
              <div className="slide-title">{slide.title || 'Untitled'}</div>
              <div className="slide-type">{slide.type || 'content_slide'}</div>
            </div>
            <div className="slide-actions">
              <button
                className="btn-icon"
                onClick={() => handleDuplicateSlide(index)}
                title="Duplicate"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
              </button>
              <button
                className="btn-icon btn-danger"
                onClick={() => handleDeleteSlide(index)}
                title="Delete"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                </svg>
              </button>
            </div>
          </div>
        ))}
      </div>

      {slides.length === 0 && (
        <div className="empty-state">
          <p>No slides in deck. Add a slide to get started.</p>
        </div>
      )}
    </div>
  );
}

export default DeckBuilder;
