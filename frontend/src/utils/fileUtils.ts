export interface UploadedFile {
  id: string;
  filename: string;
  type: 'image' | 'document' | 'audio' | 'other';
  size: number;
  path: string;
  url?: string;
}

export const uploadFiles = async (files: FileList): Promise<UploadedFile[]> => {
  const formData = new FormData();
  
  Array.from(files).forEach(file => {
    formData.append('files', file);
  });

  try {
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.text();
      throw new Error(`Upload failed: ${response.status} ${errorData}`);
    }

    const result = await response.json();
    return result.files.map((file: UploadedFile) => ({
      ...file,
      url: `/uploads/${file.path.split('/').pop()}`
    }));
  } catch (error) {
    console.error('Upload error:', error);
    throw error;
  }
};

export const transcribeAudio = async (audioBlob: Blob): Promise<string> => {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'recording.wav');

  try {
    const response = await fetch('/api/transcribe', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.text();
      throw new Error(`Transcription failed: ${response.status} ${errorData}`);
    }

    const result = await response.json();
    return result.text || '';
  } catch (error) {
    console.error('Transcription error:', error);
    throw error;
  }
};

export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};