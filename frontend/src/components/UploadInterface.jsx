/**
 * Upload Interface Component (FR-5.1)
 *
 * Drag-and-drop zone for PPTX files with upload progress.
 */
import React, { useState, useCallback } from 'react';
import { api } from '../api/client';

function UploadInterface({ onUploadComplete }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});
  const [uploading, setUploading] = useState(false);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(async (e) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    const pptxFiles = files.filter((file) => file.name.endsWith('.pptx'));

    if (pptxFiles.length === 0) {
      alert('Please upload .pptx files only');
      return;
    }

    setUploading(true);

    for (const file of pptxFiles) {
      setUploadProgress((prev) => ({
        ...prev,
        [file.name]: { status: 'uploading', progress: 0 },
      }));

      try {
        const response = await api.uploadCollection(file);
        setUploadProgress((prev) => ({
          ...prev,
          [file.name]: { status: 'complete', progress: 1, templatesCreated: response.data.templates_created },
        }));

        if (onUploadComplete) {
          onUploadComplete(response.data);
        }
      } catch (error) {
        setUploadProgress((prev) => ({
          ...prev,
          [file.name]: { status: 'error', progress: 0, error: error.message },
        }));
      }
    }

    setUploading(false);
  }, [onUploadComplete]);

  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files);
    const pptxFiles = files.filter((file) => file.name.endsWith('.pptx'));

    if (pptxFiles.length === 0) {
      alert('Please upload .pptx files only');
      return;
    }

    setUploading(true);

    for (const file of pptxFiles) {
      setUploadProgress((prev) => ({
        ...prev,
        [file.name]: { status: 'uploading', progress: 0 },
      }));

      try {
        const response = await api.uploadCollection(file);
        setUploadProgress((prev) => ({
          ...prev,
          [file.name]: { status: 'complete', progress: 1, templatesCreated: response.data.templates_created },
        }));

        if (onUploadComplete) {
          onUploadComplete(response.data);
        }
      } catch (error) {
        setUploadProgress((prev) => ({
          ...prev,
          [file.name]: { status: 'error', progress: 0, error: error.message },
        }));
      }
    }

    setUploading(false);
  };

  return (
    <div className="upload-interface">
      <div
        className={`drop-zone ${isDragging ? 'dragging' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          type="file"
          id="file-input"
          accept=".pptx"
          multiple
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        <label htmlFor="file-input" className="drop-zone-label">
          <div className="drop-zone-content">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <p>Drag and drop PPTX files here, or click to browse</p>
          </div>
        </label>
      </div>

      {Object.keys(uploadProgress).length > 0 && (
        <div className="upload-progress">
          <h3>Upload Progress</h3>
          {Object.entries(uploadProgress).map(([fileName, progress]) => (
            <div key={fileName} className="progress-item">
              <div className="progress-info">
                <span className="file-name">{fileName}</span>
                <span className={`status ${progress.status}`}>
                  {progress.status === 'complete' && `✓ ${progress.templatesCreated} templates created`}
                  {progress.status === 'error' && `✗ ${progress.error}`}
                  {progress.status === 'uploading' && 'Uploading...'}
                </span>
              </div>
              {progress.status === 'uploading' && (
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${progress.progress * 100}%` }} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default UploadInterface;
