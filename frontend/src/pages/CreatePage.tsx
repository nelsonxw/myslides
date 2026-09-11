import React, { useState } from 'react';
import { api, SessionState } from '../api/client';

export const CreatePage: React.FC = () => {
  const [prompt, setPrompt] = useState('');
  const [feedback, setFeedback] = useState('');
  const [session, setSession] = useState<SessionState | null>(null);
  const [activeVersion, setActiveVersion] = useState<number>(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showFeedbackBox, setShowFeedbackBox] = useState(false);

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const newSession = await api.createSession(prompt);
      setSession(newSession);
      setActiveVersion(newSession.current_version);
      setShowFeedbackBox(false);
    } catch (err: any) {
      setError(err.message || 'Generation failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleIterate = async () => {
    if (!feedback.trim() || !session) return;
    setIsLoading(true);
    setError(null);
    try {
      const updated = await api.iterateSession(session.session_id, feedback);
      setSession(updated);
      setActiveVersion(updated.current_version);
      setFeedback('');
      setShowFeedbackBox(false);
    } catch (err: any) {
      setError(err.message || 'Iteration failed');
    } finally {
      setIsLoading(false);
    }
  };

  const currentVersionData = session?.versions.find((v) => v.version_number === activeVersion);

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px 24px' }}>
      {/* Header & Prompt Section */}
      <div style={{ background: '#fff', borderRadius: '12px', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '8px', color: '#1D2C3B' }}>
          Describe Your One-Page Slide
        </h2>
        <p style={{ color: '#64748B', fontSize: '14px', marginBottom: '16px' }}>
          Tell the AI what you need (e.g. "Executive KPI summary showing quarterly revenue growth of 24%, cloud adoption milestones, and top strategic focus areas").
        </p>
        
        <div style={{ display: 'flex', gap: '12px' }}>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe your slide topic, key numbers, milestones, or layout structure..."
            rows={3}
            style={{
              flex: 1,
              padding: '12px 16px',
              borderRadius: '8px',
              border: '1px solid #CBD5E1',
              fontSize: '14px',
              fontFamily: 'inherit',
              resize: 'vertical',
            }}
          />
          <button
            onClick={handleGenerate}
            disabled={isLoading || !prompt.trim()}
            style={{
              padding: '0 28px',
              background: '#0672CB',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              fontWeight: '600',
              fontSize: '15px',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              opacity: isLoading ? 0.7 : 1,
              alignSelf: 'stretch',
            }}
          >
            {isLoading && !session ? 'Generating...' : 'Create Slide'}
          </button>
        </div>

        {error && (
          <div style={{ marginTop: '12px', padding: '10px 14px', background: '#FEE2E2', color: '#991B1B', borderRadius: '6px', fontSize: '13px' }}>
            {error}
          </div>
        )}
      </div>

      {/* Slide Preview & Iteration Section */}
      {session && currentVersionData && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
          {/* Main Slide Preview Card */}
          <div style={{ background: '#fff', borderRadius: '12px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '16px', fontWeight: '700', color: '#1D2C3B' }}>
                  {currentVersionData.blueprint.title || 'Slide Preview'}
                </h3>
                <span style={{ fontSize: '12px', color: '#64748B' }}>
                  Version {currentVersionData.version_number} &bull; {currentVersionData.change_summary}
                </span>
              </div>
              
              {/* Version Selector Tabs */}
              <div style={{ display: 'flex', gap: '6px' }}>
                {session.versions.map((v) => (
                  <button
                    key={v.version_number}
                    onClick={() => setActiveVersion(v.version_number)}
                    style={{
                      padding: '4px 10px',
                      borderRadius: '4px',
                      border: '1px solid',
                      borderColor: activeVersion === v.version_number ? '#0672CB' : '#CBD5E1',
                      background: activeVersion === v.version_number ? '#0672CB' : '#fff',
                      color: activeVersion === v.version_number ? '#fff' : '#475569',
                      fontSize: '12px',
                      fontWeight: '600',
                      cursor: 'pointer',
                    }}
                  >
                    v{v.version_number}
                  </button>
                ))}
              </div>
            </div>

            {/* 16:9 Image Preview Frame */}
            <div style={{ position: 'relative', width: '100%', paddingTop: '56.25%', background: '#1D2C3B', borderRadius: '8px', overflow: 'hidden', border: '1px solid #E2E8F0' }}>
              <img
                src={api.getPreviewUrl(session.session_id, currentVersionData.version_number)}
                alt="PowerPoint Preview"
                style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', objectFit: 'contain' }}
                onError={(e) => {
                  // Fallback if image not yet rendered
                  (e.target as HTMLElement).style.display = 'none';
                }}
              />
            </div>

            {/* Interactive Loop: "Need changes?" */}
            <div style={{ marginTop: '20px', padding: '16px', background: '#F8FAFC', borderRadius: '8px', border: '1px solid #E2E8F0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: '600', fontSize: '14px', color: '#1E293B' }}>
                  Are any changes needed for this slide?
                </span>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    onClick={() => setShowFeedbackBox(true)}
                    style={{
                      padding: '8px 16px',
                      background: '#fff',
                      border: '1px solid #0672CB',
                      color: '#0672CB',
                      borderRadius: '6px',
                      fontWeight: '600',
                      fontSize: '13px',
                      cursor: 'pointer',
                    }}
                  >
                    Yes, refine slide
                  </button>
                  <a
                    href={api.getDownloadUrl(session.session_id, currentVersionData.version_number)}
                    download
                    style={{
                      padding: '8px 18px',
                      background: '#10B981',
                      color: '#fff',
                      borderRadius: '6px',
                      fontWeight: '600',
                      fontSize: '13px',
                      textDecoration: 'none',
                      display: 'inline-block',
                    }}
                  >
                    No, download .pptx
                  </a>
                </div>
              </div>

              {/* Feedback Input on "Yes" */}
              {showFeedbackBox && (
                <div style={{ marginTop: '16px', borderTop: '1px solid #E2E8F0', paddingTop: '16px' }}>
                  <textarea
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    placeholder="Describe your desired changes (e.g. 'Make the cards darker', 'Add a 4th milestone for Q4', 'Change stat number to $4.2M')..."
                    rows={2}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '6px',
                      border: '1px solid #CBD5E1',
                      fontSize: '13px',
                      fontFamily: 'inherit',
                      marginBottom: '10px',
                    }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                    <button
                      onClick={() => setShowFeedbackBox(false)}
                      style={{ padding: '6px 12px', background: '#F1F5F9', border: 'none', borderRadius: '4px', fontSize: '12px', cursor: 'pointer' }}
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleIterate}
                      disabled={isLoading || !feedback.trim()}
                      style={{
                        padding: '6px 16px',
                        background: '#0672CB',
                        color: '#fff',
                        border: 'none',
                        borderRadius: '4px',
                        fontWeight: '600',
                        fontSize: '12px',
                        cursor: 'pointer',
                      }}
                    >
                      {isLoading ? 'Updating...' : 'Generate Iteration'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right Panel: Blueprint Inspector & Archetype Insights */}
          <div style={{ background: '#fff', borderRadius: '12px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '12px', color: '#1D2C3B' }}>
              Slide Design Details
            </h3>

            <div style={{ marginBottom: '16px' }}>
              <span style={{ fontSize: '11px', fontWeight: '700', color: '#64748B', textTransform: 'uppercase' }}>Archetype</span>
              <p style={{ fontWeight: '600', color: '#0672CB', fontSize: '14px' }}>
                {currentVersionData.blueprint.archetype}
              </p>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <span style={{ fontSize: '11px', fontWeight: '700', color: '#64748B', textTransform: 'uppercase' }}>Shapes & Components</span>
              <p style={{ fontSize: '13px', color: '#334155' }}>
                {currentVersionData.blueprint.shapes.length} structured design elements
              </p>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <span style={{ fontSize: '11px', fontWeight: '700', color: '#64748B', textTransform: 'uppercase' }}>Brand Palette</span>
              <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
                {currentVersionData.blueprint.palette?.map((col: string, idx: number) => (
                  <div
                    key={idx}
                    title={col}
                    style={{ width: '24px', height: '24px', borderRadius: '4px', background: col, border: '1px solid #CBD5E1' }}
                  />
                ))}
              </div>
            </div>

            <div style={{ borderTop: '1px solid #E2E8F0', paddingTop: '16px', marginTop: '16px' }}>
              <span style={{ fontSize: '11px', fontWeight: '700', color: '#64748B', textTransform: 'uppercase' }}>Version History</span>
              <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {session.versions.map((v) => (
                  <div
                    key={v.version_number}
                    onClick={() => setActiveVersion(v.version_number)}
                    style={{
                      padding: '8px 10px',
                      borderRadius: '6px',
                      background: activeVersion === v.version_number ? '#EFF6FF' : '#F8FAFC',
                      border: '1px solid',
                      borderColor: activeVersion === v.version_number ? '#93C5FD' : '#E2E8F0',
                      cursor: 'pointer',
                      fontSize: '12px',
                    }}
                  >
                    <div style={{ fontWeight: '600', color: '#1E293B' }}>Version {v.version_number}</div>
                    <div style={{ color: '#64748B', fontSize: '11px' }}>{v.change_summary}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
