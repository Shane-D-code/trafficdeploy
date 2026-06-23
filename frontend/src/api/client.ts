import axios from 'axios';

const getWsUrl = () => {
  if (import.meta.env.PROD) {
    const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    return `${protocol}${window.location.host}/ws`;
  }
  return import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:4000/ws';
};

export const WS_URL = getWsUrl();

const API_BASE = import.meta.env.VITE_API_URL || '/api';

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 300000,
});
