/**
 * API client for MySlides backend.
 */
import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 1 minute timeout for API calls (reduced from 5 minutes)
});

export const api = {
  // Health check
  healthCheck: () => apiClient.get('/health'),

  // Curated Training Slides (Firebase Storage 'curated slides' folder)
  getTrainingSlidesStatus: () => apiClient.get('/api/training-slides/status'),
  listTrainingSlides: (classification = null, skip = 0, limit = 100) =>
    apiClient.get('/api/training-slides', { params: { classification, skip, limit } }),
  syncTrainingSlides: (limit = null) =>
    apiClient.post('/api/training-slides/sync-and-reindex', null, { params: { limit } }),
  getSyncReindexStatus: () =>
    apiClient.get('/api/training-slides/sync-and-reindex/status'),
  getCuratedSlidePreview: (templateId) =>
    apiClient.get(`/api/training-slides/${templateId}/preview`, { responseType: 'blob' }),

  // Collections
  listCollections: (skip = 0, limit = 100) =>
    apiClient.get('/api/collections', { params: { skip, limit } }),

  // Templates
  listTemplates: (classification = null, skip = 0, limit = 100) =>
    apiClient.get('/api/templates', { params: { classification, skip, limit } }),
  updateTemplate: (templateId, data) =>
    apiClient.patch(`/api/templates/${templateId}`, data),

  // Generation
  improveSlide: (file, prompt = '') => {
    const formData = new FormData();
    formData.append('file', file);
    if (prompt) {
      formData.append('prompt', prompt);
    }
    return apiClient.post('/api/generate/improve-slide', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  parsePrompt: (promptText, conversationId = null) =>
    apiClient.post('/api/generate/parse-prompt', { prompt_text: promptText, conversation_id: conversationId }),
  suggestTemplates: (slideType, content, tone = null, nResults = 5, useAdaptiveElementCount = true) =>
    apiClient.post('/api/generate/suggest-templates', {
      slide_type: slideType,
      content,
      tone,
      n_results: nResults,
      use_adaptive_element_count: useAdaptiveElementCount,
    }),
  createSlide: (slideType, content, tone = null, templateId = null, elementPreferences = null, colorPreference = null) =>
    apiClient.post('/api/generate/create-slide', {
      slide_type: slideType,
      content,
      tone,
      template_id: templateId,
      element_preferences: elementPreferences,
      color_preference: colorPreference,
    }),
  refineSlide: (data) =>
    apiClient.post('/api/generate/refine-slide', data),
  createDeck: (prompts, title = 'Generated Deck') =>
    apiClient.post('/api/generate/create-deck', { prompts, title }),

  // Slides and Decks
  getSlidePreview: (requestId) => apiClient.get(`/api/slides/${requestId}/preview`),
  downloadSlide: (requestId) => apiClient.get(`/api/slides/${requestId}/download`, { responseType: 'blob' }),
  getDeck: (deckId) => apiClient.get(`/api/decks/${deckId}`),
  updateDeck: (deckId, data) => apiClient.patch(`/api/decks/${deckId}`, data),
  downloadDeck: (deckId) => apiClient.get(`/api/decks/${deckId}/download`, { responseType: 'blob' }),

  // Palettes
  listPalettes: (limit = 50) => apiClient.get('/api/palettes', { params: { limit } }),
};

export default api;
