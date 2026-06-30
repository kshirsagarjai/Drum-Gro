import axios from "axios";

export const API_BASE_URL = "http://127.0.0.1:8000/api";

export async function uploadAudio(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
}

export async function analyzeAudio(fileId) {
  const response = await axios.post(`${API_BASE_URL}/analyze/${fileId}`);
  return response.data;
}

export async function getStatus(fileId) {
  const response = await axios.get(`${API_BASE_URL}/status/${fileId}`);
  return response.data;
}

export async function getTimeline(fileId) {
  const response = await axios.get(`${API_BASE_URL}/timeline/${fileId}`);
  return response.data;
}

export function getAudioUrl(fileId, layerName) {
  return `${API_BASE_URL}/audio/${fileId}/${layerName}`;
}
