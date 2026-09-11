import React, { useEffect, useState } from 'react';
import { api, SourceItem } from '../api/client';

interface ScrapeProgress {
  status: string;
  current: number;
  total: number;
  current_file: string;
  last_result: string;
}

export const SourcesPage: React.FC = () => {
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [name, setName] = useState('');
  const [kind, setKind] = useState('generic_url');
  const [urlOrPath, setUrlOrPath] = useState('');
  const [licenseStr, setLicenseStr] = useState('CC BY / Open');
  const [isLoading, setIsLoading] = useState(false);
  const [isPickingFile, setIsPickingFile] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Map of active scrape progress by source_id
  const [activeProgress, setActiveProgress] = useState<{ [key: number]: ScrapeProgress }>({});

  const handlePickLocal = async (targetType: 'file' | 'folder') => {
    setIsPickingFile(true);
    try {
      const res = await api.pickLocalPath(targetType);
      if (!res.cancelled && res.path) {
        setUrlOrPath(res.path);
        // Automatically suggest a friendly name if empty
        if (!name) {
          const parts = res.path.split(/[\/\\]/);
          const rawName = parts[parts.length - 1].replace(/\.pptx$/i, '');
          setName(rawName.replace(/[-_]/g, ' '));
        }
      }
    } catch (err: any) {
      console.error(err);
      setErrorMsg(`File picker error: ${err.message}`);
    } finally {
      setIsPickingFile(false);
    }
  };

  // Format ISO timestamp to user's local timezone
  const formatLocalTime = (isoString: string | null) => {
    if (!isoString) return '';
    try {
      // Ensure ISO string with no timezone suffix is treated as UTC
      const normalized = isoString.endsWith('Z') || isoString.includes('+') ? isoString : `${isoString}Z`;
      const date = new Date(normalized);
      return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true });
    } catch {
      return '';
    }
  };

  const fetchSources = async () => {
    try {
      const data = await api.getSources();
      setSources(data);

      // If any source is in "running" status in the DB and not yet in activeProgress, start polling it
      const newRunning: { [key: number]: ScrapeProgress } = {};
      data.forEach((s) => {
        if (s.last_status === 'running' && !activeProgress[s.id]) {
          newRunning[s.id] = {
            status: 'discovering',
            current: 0,
            total: 0,
            current_file: 'Scraping in progress...',
            last_result: '',
          };
        }
      });
      if (Object.keys(newRunning).length > 0) {
        setActiveProgress((prev) => ({ ...prev, ...newRunning }));
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchSources();
  }, []);

  // Poll progress for any active scraper jobs
  useEffect(() => {
    const runningSources = Object.keys(activeProgress).map(Number);
    if (runningSources.length === 0) return;

    const interval = setInterval(async () => {
      let anyChanged = false;
      const updatedProgress = { ...activeProgress };

      for (const sid of runningSources) {
        try {
          const prog = await api.getSourceProgress(sid);
          if (prog.status === 'completed' || prog.status === 'error' || prog.status === 'idle') {
            delete updatedProgress[sid];
            anyChanged = true;
          } else {
            updatedProgress[sid] = prog;
          }
        } catch (err) {
          console.error(err);
        }
      }

      if (anyChanged) {
        setActiveProgress(updatedProgress);
        fetchSources();
      } else {
        setActiveProgress(updatedProgress);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [activeProgress]);

  const handleAddSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !urlOrPath) return;
    setIsLoading(true);
    try {
      await api.addSource({
        name,
        kind,
        url_or_path: urlOrPath,
        license: licenseStr,
      });
      setName('');
      setUrlOrPath('');
      setErrorMsg(null);
      fetchSources();
    } catch (err: any) {
      setErrorMsg(`Error adding source: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunSource = async (id: number) => {
    try {
      await api.runSource(id);
      setActiveProgress((prev) => ({
        ...prev,
        [id]: {
          status: 'discovering',
          current: 0,
          total: 0,
          current_file: 'Starting scraper job...',
          last_result: '',
        },
      }));
      fetchSources();
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleStopSource = async (id: number) => {
    try {
      await api.stopSource(id);
      setActiveProgress((prev) => {
        const updated = { ...prev };
        delete updated[id];
        return updated;
      });
      fetchSources();
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this source?')) return;
    try {
      await api.deleteSource(id);
      setActiveProgress((prev) => {
        const updated = { ...prev };
        delete updated[id];
        return updated;
      });
      fetchSources();
    } catch (err: any) {
      console.error(err);
    }
  };

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '32px 24px' }}>
      <h2 style={{ fontSize: '22px', fontWeight: '700', color: '#1D2C3B', marginBottom: '8px' }}>
        Template Sources & Scrapers
      </h2>
      <p style={{ color: '#64748B', fontSize: '14px', marginBottom: '24px' }}>
        Manage online and local PowerPoint sources. The app automatically scrubs templates, extracts typography & visual patterns, and updates design rules.
      </p>

      {errorMsg && (
        <div style={{ marginBottom: '16px', padding: '10px 14px', background: '#FEE2E2', color: '#DC2626', border: '1px solid #FECACA', borderRadius: '6px', fontSize: '13px' }}>
          {errorMsg}
        </div>
      )}

      {/* Add New Source Form */}
      <div style={{ background: '#fff', borderRadius: '12px', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginBottom: '32px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: '700', color: '#1E293B', marginBottom: '16px' }}>
          Add Additional Template Source
        </h3>
        <form onSubmit={handleAddSource} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#475569', marginBottom: '6px' }}>
              Source Name
            </label>
            <input
              type="text"
              placeholder="e.g. Executive Templates Portal"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#475569', marginBottom: '6px' }}>
              Source Type
            </label>
            <select
              value={kind}
              onChange={(e) => setKind(e.target.value)}
              style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px' }}
            >
              <option value="generic_url">Web Page / Direct .pptx Link</option>
              <option value="slidescarnival">SlidesCarnival Free Templates</option>
              <option value="ms_create">Microsoft Create</option>
              <option value="github">GitHub .pptx Query</option>
              <option value="local_folder">Local Directory</option>
            </select>
          </div>

          <div style={{ gridColumn: 'span 2' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <label style={{ fontSize: '12px', fontWeight: '600', color: '#475569' }}>
                {kind === 'local_folder' ? 'Local File or Directory Path' : 'URL or Target Query'}
              </label>
              {kind === 'local_folder' && (
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    type="button"
                    onClick={() => handlePickLocal('file')}
                    disabled={isPickingFile}
                    style={{
                      padding: '4px 10px',
                      background: '#EFF6FF',
                      color: '#0672CB',
                      border: '1px solid #BFDBFE',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontWeight: '600',
                      cursor: isPickingFile ? 'wait' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    📂 Browse .pptx File
                  </button>
                  <button
                    type="button"
                    onClick={() => handlePickLocal('folder')}
                    disabled={isPickingFile}
                    style={{
                      padding: '4px 10px',
                      background: '#F8FAFC',
                      color: '#475569',
                      border: '1px solid #CBD5E1',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontWeight: '600',
                      cursor: isPickingFile ? 'wait' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    📁 Browse Folder
                  </button>
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="text"
                placeholder={kind === 'local_folder' ? 'Click Browse above or enter C:\\path\\to\\deck.pptx' : 'https://example.com/templates or query'}
                value={urlOrPath}
                onChange={(e) => setUrlOrPath(e.target.value)}
                required
                style={{ flex: 1, padding: '8px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px' }}
              />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#475569', marginBottom: '6px' }}>
              License / Terms
            </label>
            <input
              type="text"
              placeholder="e.g. Creative Commons BY 4.0"
              value={licenseStr}
              onChange={(e) => setLicenseStr(e.target.value)}
              style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #CBD5E1', fontSize: '13px' }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button
              type="submit"
              disabled={isLoading}
              style={{
                width: '100%',
                padding: '10px 16px',
                background: '#0672CB',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                fontWeight: '600',
                fontSize: '13px',
                cursor: 'pointer',
              }}
            >
              Add & Register Source
            </button>
          </div>
        </form>
      </div>

      {/* Sources Table with Real-time Progress Bar */}
      <div style={{ background: '#fff', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
          <thead>
            <tr style={{ background: '#F8FAFC', borderBottom: '1px solid #E2E8F0', color: '#64748B', fontWeight: '600' }}>
              <th style={{ padding: '12px 16px' }}>Name</th>
              <th style={{ padding: '12px 16px' }}>Kind</th>
              <th style={{ padding: '12px 16px' }}>License</th>
              <th style={{ padding: '12px 16px' }}>Status & Live Progress</th>
              <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((s) => {
              const prog = activeProgress[s.id];
              const isRunning = (prog && (prog.status === 'discovering' || prog.status === 'ingesting')) || s.last_status === 'running';
              const pct = prog && prog.total > 0 ? Math.round((prog.current / prog.total) * 100) : (s.last_status === 'running' ? (prog?.current ? Math.round((prog.current / (prog.total || 1)) * 100) : 10) : 0);

              return (
                <tr key={s.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                  <td style={{ padding: '12px 16px', fontWeight: '600', color: '#1E293B', verticalAlign: 'bottom' }}>{s.name}</td>
                  <td style={{ padding: '12px 16px', color: '#64748B', verticalAlign: 'bottom' }}>{s.kind}</td>
                  <td style={{ padding: '12px 16px', color: '#64748B', verticalAlign: 'bottom' }}>{s.license}</td>
                  <td style={{ padding: '12px 16px', minWidth: '240px', verticalAlign: 'bottom' }}>
                    {isRunning ? (
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', fontSize: '11px', color: '#0672CB', fontWeight: '600', marginBottom: '4px', gap: '8px' }}>
                          <span style={{ wordBreak: 'break-word', flex: 1 }}>{prog?.current_file || 'Scraping in progress...'}</span>
                          <span style={{ flexShrink: 0 }}>{pct}%</span>
                        </div>
                        <div style={{ width: '100%', height: '6px', background: '#E2E8F0', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{ width: `${Math.max(pct, 10)}%`, height: '100%', background: '#0672CB', transition: 'width 0.3s ease' }} />
                        </div>
                      </div>
                    ) : prog && prog.status === 'completed' ? (
                      <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: '600', background: '#D1FAE5', color: '#065F46' }}>
                        ✓ {prog.current_file}
                      </span>
                    ) : s.last_status === 'no_slides_found' ? (
                      <div>
                        <span
                          style={{
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: '600',
                            background: '#FFEDD5',
                            color: '#C2410C',
                            display: 'inline-block',
                            marginBottom: s.last_error ? '4px' : '0',
                          }}
                        >
                          ⚠️ 0 slides ingested {s.last_scraped_at ? `(${formatLocalTime(s.last_scraped_at)})` : ''}
                        </span>
                        {s.last_error && (
                          <div
                            style={{
                              fontSize: '11px',
                              color: '#9A3412',
                              background: '#FFF7ED',
                              border: '1px solid #FFEDD5',
                              borderRadius: '4px',
                              padding: '4px 8px',
                              maxWidth: '320px',
                              whiteSpace: 'pre-wrap',
                              wordBreak: 'break-word',
                            }}
                          >
                            {s.last_error}
                          </div>
                        )}
                      </div>
                    ) : s.last_status === 'error' ? (
                      <div>
                        <span
                          style={{
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: '600',
                            background: '#FEE2E2',
                            color: '#DC2626',
                            display: 'inline-block',
                            marginBottom: s.last_error ? '4px' : '0',
                          }}
                        >
                          error {s.last_scraped_at ? `(${formatLocalTime(s.last_scraped_at)})` : ''}
                        </span>
                        {s.last_error && (
                          <div
                            style={{
                              fontSize: '11px',
                              color: '#DC2626',
                              background: '#FFF5F5',
                              border: '1px solid #FECACA',
                              borderRadius: '4px',
                              padding: '4px 8px',
                              maxWidth: '320px',
                              whiteSpace: 'pre-wrap',
                              wordBreak: 'break-word',
                            }}
                          >
                            {s.last_error.length > 200 ? s.last_error.slice(0, 200) + '...' : s.last_error}
                          </div>
                        )}
                      </div>
                    ) : (
                      <span
                        style={{
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '11px',
                          fontWeight: '600',
                          background: s.last_status === 'running' ? '#FEF3C7' : s.last_status === 'success' ? '#D1FAE5' : '#F1F5F9',
                          color: s.last_status === 'running' ? '#B45309' : s.last_status === 'success' ? '#065F46' : '#475569',
                        }}
                      >
                        {s.last_status} {s.last_scraped_at ? `(${formatLocalTime(s.last_scraped_at)})` : ''}
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '12px 16px', textAlign: 'right', whiteSpace: 'nowrap', verticalAlign: 'bottom' }}>
                    <div style={{ display: 'inline-flex', gap: '8px', alignItems: 'center' }}>
                      {isRunning ? (
                        <button
                          onClick={() => handleStopSource(s.id)}
                          style={{
                            minWidth: '76px',
                            height: '28px',
                            padding: '0 10px',
                            background: '#FEE2E2',
                            color: '#DC2626',
                            border: '1px solid #FECACA',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontWeight: '600',
                            fontSize: '11px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '4px',
                            boxSizing: 'border-box',
                          }}
                        >
                          <span style={{ fontSize: '9px' }}>⏹</span> Stop
                        </button>
                      ) : (
                        <button
                          onClick={() => handleRunSource(s.id)}
                          style={{
                            minWidth: '76px',
                            height: '28px',
                            padding: '0 10px',
                            background: '#EFF6FF',
                            color: '#0672CB',
                            border: '1px solid #BFDBFE',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontWeight: '600',
                            fontSize: '11px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            boxSizing: 'border-box',
                          }}
                        >
                          Scrape Now
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(s.id)}
                        style={{
                          minWidth: '64px',
                          height: '28px',
                          padding: '0 10px',
                          background: '#FEE2E2',
                          color: '#DC2626',
                          border: '1px solid #FECACA',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontWeight: '600',
                          fontSize: '11px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          boxSizing: 'border-box',
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
