export interface SlideLibraryItem {
  id: number;
  asset_id: number;
  asset_title: string;
  slide_index: number;
  title: string;
  subtitle: string;
  archetype: string;
  score: number;
  visuals_score: number;
  layout_score: number;
  formatting_score: number;
  tags: string[];
  has_chart: boolean;
  has_table: boolean;
  icon_count: number;
  license: string;
  attribution: string;
}

export interface SlideLibraryResponse {
  total_count: number;
  filtered_count: number;
  slides: SlideLibraryItem[];
}

export interface SourceItem {
  id: number;
  name: string;
  kind: string;
  url_or_path: string;
  license: string;
  attribution: string;
  enabled: boolean;
  last_scraped_at: string | null;
  last_status: string;
  last_error: string | null;
}

export interface SlideVersion {
  version_number: number;
  blueprint: any;
  pptx_path: string;
  preview_png_path: string | null;
  feedback_from_previous: string;
  change_summary: string;
  created_at: string;
}

export interface SessionState {
  session_id: string;
  initial_prompt: string;
  current_version: number;
  versions: SlideVersion[];
  created_at: string;
}

const API_BASE = '/api';

export const api = {
  // Generation
  createSession: async (prompt: string): Promise<SessionState> => {
    const res = await fetch(`${API_BASE}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  getSession: async (sessionId: string): Promise<SessionState> => {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  iterateSession: async (sessionId: string, feedback: string): Promise<SessionState> => {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/iterate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ feedback }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  getPreviewUrl: (sessionId: string, version: number) =>
    `${API_BASE}/sessions/${sessionId}/versions/${version}/preview.png`,

  getDownloadUrl: (sessionId: string, version: number) =>
    `${API_BASE}/sessions/${sessionId}/versions/${version}/download`,

  // Library
  getSlidePreviewUrl: (slideId: number) => `${API_BASE}/library/slides/${slideId}/preview.png`,

  getSlides: async (archetype?: string, minScore?: number, search?: string): Promise<SlideLibraryResponse> => {
    const params = new URLSearchParams();
    if (archetype) params.append('archetype', archetype);
    if (minScore) params.append('min_score', minScore.toString());
    if (search) params.append('search', search);
    const res = await fetch(`${API_BASE}/library/slides?${params.toString()}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  getRules: async (): Promise<any> => {
    const res = await fetch(`${API_BASE}/library/rules`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  deleteSlide: async (id: number) => {
    const res = await fetch(`${API_BASE}/library/slides/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  clearAllSlides: async () => {
    const res = await fetch(`${API_BASE}/library/slides`, { method: 'DELETE' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Sources
  getSources: async (): Promise<SourceItem[]> => {
    const res = await fetch(`${API_BASE}/sources`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  addSource: async (data: { name: string; kind: string; url_or_path: string; license?: string; attribution?: string }) => {
    const res = await fetch(`${API_BASE}/sources`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  deleteSource: async (id: number) => {
    const res = await fetch(`${API_BASE}/sources/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  runSource: async (id: number) => {
    const res = await fetch(`${API_BASE}/sources/${id}/run`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  getSourceProgress: async (id: number) => {
    const res = await fetch(`${API_BASE}/sources/${id}/progress`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  pickLocalPath: async (targetType: 'folder' | 'file' = 'file'): Promise<{ path: string; cancelled: boolean; error?: string }> => {
    const res = await fetch(`${API_BASE}/sources/pick-local-path?target_type=${targetType}`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
};
