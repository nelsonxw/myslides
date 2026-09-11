import React, { useState, useEffect } from 'react';
import { CreatePage } from './pages/CreatePage';
import { LibraryPage } from './pages/LibraryPage';
import { SourcesPage } from './pages/SourcesPage';
import { api } from './api/client';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'create' | 'library' | 'sources'>('create');
  const [llmStatus, setLlmStatus] = useState<{ using_mock: boolean; message: string } | null>(null);

  useEffect(() => {
    fetch('/api/sessions/llm-status')
      .then(response => response.json())
      .then(data => setLlmStatus(data))
      .catch(() => setLlmStatus(null));
  }, []);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Navigation Bar */}
      <header
        style={{
          background: '#1D2C3B',
          color: '#fff',
          padding: '0 24px',
          height: '60px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '6px',
              background: '#0672CB',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: '800',
              fontSize: '16px',
            }}
          >
            S
          </div>
          <div>
            <h1 style={{ fontSize: '16px', fontWeight: '700', letterSpacing: '-0.3px' }}>MySlides AI</h1>
            <span style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              One-Page Slide Studio
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: 'flex', gap: '4px' }}>
          {[
            { id: 'create', label: 'Create Slide' },
            { id: 'library', label: 'Template Library' },
            { id: 'sources', label: 'Scrapers & Sources' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              style={{
                padding: '8px 16px',
                borderRadius: '6px',
                background: activeTab === tab.id ? '#0672CB' : 'transparent',
                color: activeTab === tab.id ? '#fff' : '#94A3B8',
                border: 'none',
                fontWeight: '600',
                fontSize: '13px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>

      {/* LLM Warning Banner */}
      {llmStatus?.using_mock && (
        <div
          style={{
            background: '#FEF3C7',
            border: '1px solid #F59E0B',
            color: '#92400E',
            padding: '12px 24px',
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <span style={{ fontSize: '16px' }}>⚠️</span>
          <span>{llmStatus.message}</span>
        </div>
      )}

      {/* Main Page Content */}
      <main style={{ flex: 1 }}>
        {activeTab === 'create' && <CreatePage />}
        {activeTab === 'library' && <LibraryPage />}
        {activeTab === 'sources' && <SourcesPage />}
      </main>
    </div>
  );
};
