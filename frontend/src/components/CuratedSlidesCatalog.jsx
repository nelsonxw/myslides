/**
 * Curated Slides Catalog Component
 *
 * Displays training slides read directly from Firebase Storage 'curated slides' folder.
 */
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { api } from '../api/client';

function CuratedSlidePreview({ templateId, slideName }) {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  if (!templateId) {
    return (
      <div className="curated-slide-preview">
        <div className="curated-preview-placeholder">
          <span>Pending indexing</span>
        </div>
      </div>
    );
  }

  const previewUrl = `http://127.0.0.1:8000/api/training-slides/${templateId}/preview?t=${retryKey}`;

  return (
    <div className="curated-slide-preview">
      {!loaded && !failed && (
        <div className="curated-preview-placeholder">
          <div className="spinner-small" style={{ marginBottom: '8px' }} />
          <span>Loading preview...</span>
        </div>
      )}
      {failed ? (
        <div className="curated-preview-placeholder">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ marginBottom: '6px', opacity: 0.5 }}
          >
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <line x1="9" y1="9" x2="15" y2="15" />
            <line x1="15" y1="9" x2="9" y2="15" />
          </svg>
          <span>Preview unavailable</span>
          <button
            type="button"
            className="retry-preview-btn"
            onClick={(e) => {
              e.stopPropagation();
              setFailed(false);
              setLoaded(false);
              setRetryKey((k) => k + 1);
            }}
          >
            Retry
          </button>
        </div>
      ) : (
        <img
          src={previewUrl}
          alt={slideName}
          loading="lazy"
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
          style={{ display: loaded ? 'block' : 'none' }}
        />
      )}
    </div>
  );
}

function CuratedSlidesCatalog() {
  const [slides, setSlides] = useState([]);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncProgress, setSyncProgress] = useState(null);
  const [error, setError] = useState(null);
  const [selectedClassification, setSelectedClassification] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  const loadCatalogData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusRes, slidesRes] = await Promise.all([
        api.getTrainingSlidesStatus(),
        api.listTrainingSlides(null, 0, 50),
      ]);
      setStatus(statusRes.data);
      setSlides(slidesRes.data.slides || []);
    } catch (err) {
      setError('Failed to load curated slides from Firebase Storage.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCatalogData();
  }, [loadCatalogData]);

  const handleSync = async () => {
    setSyncing(true);
    setError(null);
    try {
      await api.syncTrainingSlides();
      // Poll progress every 5 seconds (since processing is slow with rate limiting)
      const pollInterval = setInterval(async () => {
        try {
          const res = await api.getSyncReindexStatus();
          const job = res.data;
          setSyncProgress(job);

          if (job.status === 'completed') {
            clearInterval(pollInterval);
            setSyncing(false);
            await loadCatalogData();
          } else if (job.status === 'error') {
            clearInterval(pollInterval);
            setSyncing(false);
            const errorMsg = job.error || 'Sync and re-index encountered an error.';
            // Only show Gemini-specific error if it's actually about missing API key
            if (errorMsg.includes('API key not configured') || errorMsg.includes('not provided')) {
              setError('Gemini Flash AI is required. Please configure GEMINI_API_KEY in the backend .env file.');
            } else {
              setError(errorMsg);
            }
          }
        } catch {
          // ignore transient poll error
        }
      }, 5000);
    } catch (err) {
      setSyncing(false);
      const errMessage = err.response?.data?.detail || err.message || 'Failed to start sync and re-index job.';
      // Only show Gemini-specific error if it's actually about missing API key
      if (errMessage.includes('API key not configured') || errMessage.includes('not provided')) {
        setError('Gemini Flash AI is required. Please configure GEMINI_API_KEY in the backend .env file.');
      } else {
        setError(errMessage);
      }
      console.error(err);
    }
  };

  const classifications = useMemo(() => {
    const set = new Set();
    slides.forEach((s) => {
      if (s.classification) set.add(s.classification);
    });
    return Array.from(set).sort();
  }, [slides]);

  const filteredSlides = useMemo(() => {
    return slides.filter((slide) => {
      const matchesCategory =
        selectedClassification === 'all' || slide.classification === selectedClassification;
      const matchesSearch =
        !searchQuery.trim() ||
        slide.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (slide.tags && slide.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase())));
      return matchesCategory && matchesSearch;
    });
  }, [slides, selectedClassification, searchQuery]);

  return (
    <div className="curated-catalog">
      <div className="catalog-header">
        <div className="catalog-status-card">
          <div className="status-badge-container">
            <span
              className={`status-dot ${status?.firebase_connected ? 'connected' : 'disconnected'}`}
            />
            <span className="status-title">
              {status?.firebase_connected ? 'Firebase Storage Connected' : 'Storage Disconnected'}
            </span>
          </div>
          <p className="status-subtitle">
            Source: <strong>{status?.curated_slides_folder || 'curated slides/'}</strong> on{' '}
            <code>{status?.storage_bucket || 'Firebase Storage'}</code>
          </p>
          <div className="status-metrics">
            <div className="metric">
              <span className="metric-value">{status?.total_curated_in_storage ?? 0}</span>
              <span className="metric-label">Training Slides in Storage</span>
            </div>
            <div className="metric">
              <span className="metric-value">{status?.total_curated_indexed ?? 0}</span>
              <span className="metric-label">Indexed Templates</span>
            </div>
            <div className="metric">
              <span className="metric-value">{classifications.length}</span>
              <span className="metric-label">Categories</span>
            </div>
          </div>
        </div>

        <div className="catalog-actions">
          <button
            className="reindex-button"
            onClick={handleSync}
            disabled={syncing || loading}
          >
            {syncing ? 'Syncing & Re-indexing...' : 'Sync & Re-index with Gemini Flash AI'}
          </button>
        </div>
      </div>

      {syncProgress && (syncing || syncProgress.status === 'running') && (
        <div className="reindex-progress-card">
          <div className="reindex-progress-info">
            <span className="reindex-title">Syncing & Re-indexing with Gemini Flash AI</span>
            <span className="reindex-count">
              Synced {syncProgress.sync_synced_count} new slides • Re-indexing {syncProgress.reindex_processed} / {syncProgress.reindex_total} ({syncProgress.reindex_progress_percent}%)
            </span>
            <span className="reindex-note">Note: Processing slowed to 5s per slide to stay within Gemini API free tier quota</span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${syncProgress.reindex_progress_percent}%` }} />
          </div>
          {syncProgress.current && (
            <p className="reindex-current-slide">
              Current: <code>{syncProgress.current}</code>
            </p>
          )}
        </div>
      )}

      {syncProgress?.status === 'completed' && !syncing && (
        <div className="reindex-success-banner">
          ✓ Synced {syncProgress.sync_synced_count} new slides and re-indexed {syncProgress.reindex_total} curated slides in {syncProgress.time_taken_seconds}s!
        </div>
      )}

      {error && <div className="catalog-error">{error}</div>}

      <div className="catalog-controls">
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search slides by filename or tag..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="filter-chips">
          <button
            className={`filter-chip ${selectedClassification === 'all' ? 'active' : ''}`}
            onClick={() => setSelectedClassification('all')}
          >
            All ({slides.length})
          </button>
          {classifications.map((cat) => {
            const count = slides.filter((s) => s.classification === cat).length;
            return (
              <button
                key={cat}
                className={`filter-chip ${selectedClassification === cat ? 'active' : ''}`}
                onClick={() => setSelectedClassification(cat)}
              >
                {cat.replace('_', ' ')} ({count})
              </button>
            );
          })}
        </div>
      </div>

      {loading ? (
        <div className="catalog-loading">Reading training slides from Firebase Storage...</div>
      ) : (
        <div className="slides-grid">
          {filteredSlides.map((slide) => (
            <div key={slide.storage_path} className="slide-card">
              <div className="slide-card-header">
                <span className="slide-category">{slide.classification || 'unclassified'}</span>
                <span className="slide-indexed-tag">
                  {slide.is_indexed ? 'Indexed' : 'Pending'}
                </span>
              </div>
              <h4 className="slide-name" title={slide.name}>
                {slide.name}
              </h4>
              <CuratedSlidePreview
                templateId={slide.template_id}
                slideName={slide.name}
              />
              {slide.tags && slide.tags.length > 0 && (
                <div className="slide-tags">
                  {slide.tags.slice(0, 3).map((tag) => (
                    <span key={tag} className="tag">
                      {tag}
                    </span>
                  ))}
                  {slide.tags.length > 3 && (
                    <span className="tag-more">+{slide.tags.length - 3}</span>
                  )}
                </div>
              )}
            </div>
          ))}
          {filteredSlides.length === 0 && (
            <div className="no-slides">No training slides found matching your filters.</div>
          )}
        </div>
      )}
    </div>
  );
}

export default CuratedSlidesCatalog;
