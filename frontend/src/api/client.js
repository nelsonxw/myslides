/**
 * API client for MySlides backend.
 */
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // Health check
  healthCheck: () => apiClient.get('/health'),

  // Collections
  uploadCollection: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post('/api/collections/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  listCollections: (skip = 0, limit = 100) =>
    apiClient.get('/api/collections', { params: { skip, limit } }),

  // Templates
  listTemplates: (classification = null, skip = 0, limit = 100) =>
    apiClient.get('/api/templates', { params: { classification, skip, limit } }),
  updateTemplate: (templateId, data) =>
    apiClient.patch(`/api/templates/${templateId}`, data),

  // Generation
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
  createDeck: (prompts, title = 'Generated Deck') =>
    apiClient.post('/api/generate/create-deck', { prompts, title }),

  // Slides and Decks
  getSlidePreview: (requestId) => apiClient.get(`/api/slides/${requestId}/preview`),
  downloadSlide: (requestId) => apiClient.get(`/api/slides/${requestId}/download`, { responseType: 'blob' }),
  downloadDeck: (deckId) => apiClient.get(`/api/decks/${deckId}/download`, { responseType: 'blob' }),

  // Palettes
  listPalettes: (limit = 50) => apiClient.get('/api/palettes', { params: { limit } }),
};

export default api;
