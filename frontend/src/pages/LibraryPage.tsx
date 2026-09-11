import React, { useEffect, useState } from 'react';
import { api, SlideLibraryItem } from '../api/client';

export const LibraryPage: React.FC = () => {
  const [slides, setSlides] = useState<SlideLibraryItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [filteredCount, setFilteredCount] = useState<number>(0);
  const [archetype, setArchetype] = useState('all');
  const [minScore, setMinScore] = useState(0);
  const [search, setSearch] = useState('');
  const [rules, setRules] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const fetchLibrary = async () => {
    setIsLoading(true);
    try {
      const [res, rulesData] = await Promise.all([
        api.getSlides(archetype, minScore, search),
        api.getRules(),
      ]);
      setSlides(res.slides);
      setTotalCount(res.total_count);
      setFilteredCount(res.filtered_count);
      setRules(rulesData);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLibrary();
  }, [archetype, minScore]);

  const handleDeleteSlide = async (id: number) => {
    if (!confirm('Are you sure you want to delete this slide from the library?')) return;
    try {
      await api.deleteSlide(id);
      setActionMsg('Slide deleted.');
      fetchLibrary();
      setTimeout(() => setActionMsg(null), 3000);
    } catch (e: any) {
      alert(`Delete failed: ${e.message}`);
    }
  };

  const handleClearAll = async () => {
    if (!confirm('⚠️ Are you sure you want to delete ALL slides and templates from the library? You can re-seed them anytime.')) return;
    try {
      await api.clearAllSlides();
      setActionMsg('All slides cleared from library.');
      fetchLibrary();
      setTimeout(() => setActionMsg(null), 3000);
    } catch (e: any) {
      alert(`Clear failed: ${e.message}`);
    }
  };

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '32px 24px' }}>
      {/* Header & Filter Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: '700', color: '#1D2C3B' }}>
            PowerPoint Template & Slide Library
          </h2>
          <p style={{ color: '#64748B', fontSize: '14px' }}>
            Showing {slides.length} of {totalCount} total slides indexed, scored, and analyzed for effective design principles.
          </p>
        </div>

        {/* Filters and Actions */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <select
            value={archetype}
            onChange={(e) => setArchetype(e.target.value)}
            style={{ padding: '8px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px' }}
          >
            <option value="all">All Archetypes</option>
            <option value="kpi_summary">KPI Summary</option>
            <option value="timeline">Timeline / Process</option>
            <option value="comparison">Comparison</option>
            <option value="data_chart">Data / Chart</option>
            <option value="general">General</option>
          </select>

          <select
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            style={{ padding: '8px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px' }}
          >
            <option value="0">All Scores</option>
            <option value="60">Score 60+</option>
            <option value="70">Score 70+ (Good Quality)</option>
            <option value="80">Score 80+ (Top Tier)</option>
          </select>

          <button
            onClick={handleClearAll}
            disabled={slides.length === 0}
            style={{
              padding: '8px 14px',
              background: '#FEE2E2',
              color: '#DC2626',
              border: 'none',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: '600',
              cursor: slides.length === 0 ? 'not-allowed' : 'pointer',
              opacity: slides.length === 0 ? 0.6 : 1,
            }}
          >
            Clear Entire Library
          </button>
        </div>
      </div>

      {actionMsg && (
        <div style={{ marginBottom: '16px', padding: '10px 14px', background: '#F0FDF4', color: '#166534', borderRadius: '6px', fontSize: '13px' }}>
          {actionMsg}
        </div>
      )}

      {/* Grid of Slide Cards */}
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '60px', color: '#64748B' }}>Loading template library...</div>
      ) : slides.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px', background: '#fff', borderRadius: '12px', color: '#64748B' }}>
          <p style={{ fontSize: '16px', fontWeight: '600', marginBottom: '8px' }}>No slides in library</p>
          <p style={{ fontSize: '13px' }}>Go to the <strong>"Scrapers & Sources"</strong> tab to scrape new templates or run <code>python scripts/seed_library.py</code>.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '20px' }}>
          {slides.map((s) => (
            <div
              key={s.id}
              style={{
                background: '#fff',
                borderRadius: '10px',
                border: '1px solid #E2E8F0',
                overflow: 'hidden',
                boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              {/* Card Header & Score Badge */}
              <div style={{ padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #F1F5F9' }}>
                <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', color: '#0672CB', background: '#EFF6FF', padding: '2px 8px', borderRadius: '4px' }}>
                  {s.archetype}
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '13px', fontWeight: '700', color: s.score >= 80 ? '#10B981' : '#F59E0B' }}>
                    ★ {s.score} / 100
                  </span>
                  <button
                    onClick={() => handleDeleteSlide(s.id)}
                    title="Delete slide"
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#94A3B8',
                      cursor: 'pointer',
                      fontSize: '14px',
                      padding: '2px 6px',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = '#EF4444')}
                    onMouseLeave={(e) => (e.currentTarget.style.color = '#94A3B8')}
                  >
                    ✕
                  </button>
                </div>
              </div>

              {/* Slide Thumbnail Preview Image */}
              <div
                style={{
                  position: 'relative',
                  width: '100%',
                  paddingTop: '56.25%', // 16:9 Aspect Ratio
                  background: '#F1F5F9',
                  borderBottom: '1px solid #E2E8F0',
                  overflow: 'hidden',
                }}
              >
                <img
                  src={api.getSlidePreviewUrl(s.id)}
                  alt={s.title}
                  loading="lazy"
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                  }}
                  onError={(e) => {
                    // Fallback to stylized placeholder if thumbnail rendering is unavailable
                    e.currentTarget.style.display = 'none';
                    const parent = e.currentTarget.parentElement;
                    if (parent && !parent.querySelector('.img-fallback')) {
                      const fallback = document.createElement('div');
                      fallback.className = 'img-fallback';
                      fallback.style.cssText = 'position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; background: #1D2C3B; color: #94A3B8; font-size: 12px; gap: 6px; padding: 12px; text-align: center;';
                      fallback.innerHTML = `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="1.5"><rect width="18" height="14" x="3" y="3" rx="2"/><path d="m3 13 4-4a2 2 0 0 1 2.8 0l4.2 4.2"/><path d="m14 13 1-1a2 2 0 0 1 2.8 0l3.2 3.2"/></svg><span>${s.archetype.replace('_', ' ').toUpperCase()}</span>`;
                      parent.appendChild(fallback);
                    }
                  }}
                />
              </div>

              {/* Title & Metadata */}
              <div style={{ padding: '16px', flex: 1 }}>
                <h4 style={{ fontSize: '15px', fontWeight: '600', color: '#1E293B', marginBottom: '4px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {s.title}
                </h4>
                <p style={{ fontSize: '12px', color: '#64748B', marginBottom: '12px' }}>
                  Source: {s.asset_title} (Slide #{s.slide_index + 1})
                </p>

                {/* Score Breakdown Bar */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', background: '#F8FAFC', padding: '8px 10px', borderRadius: '6px', fontSize: '11px' }}>
                  <div>
                    <span style={{ color: '#64748B' }}>Visuals:</span> <strong style={{ color: '#1E293B' }}>{s.visuals_score}</strong>
                  </div>
                  <div>
                    <span style={{ color: '#64748B' }}>Layout:</span> <strong style={{ color: '#1E293B' }}>{s.layout_score}</strong>
                  </div>
                  <div>
                    <span style={{ color: '#64748B' }}>Design:</span> <strong style={{ color: '#1E293B' }}>{s.formatting_score}</strong>
                  </div>
                </div>

                {/* Tags */}
                {s.tags && s.tags.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '12px' }}>
                    {s.tags.slice(0, 3).map((tag, idx) => (
                      <span key={idx} style={{ fontSize: '11px', color: '#475569', background: '#F1F5F9', padding: '2px 6px', borderRadius: '4px' }}>
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
