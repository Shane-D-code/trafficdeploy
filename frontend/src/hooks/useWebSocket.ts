import { useEffect, useRef, useCallback } from 'react';
import { onMessage, sendMessage } from '../api/websocket';

export function useWebSocket(callback?: (data: any) => void) {
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  useEffect(() => {
    if (!callbackRef.current) return;
    const handler = (data: any) => callbackRef.current?.(data);
    const unsub = onMessage(handler);
    return unsub;
  }, []);

  const send = useCallback((data: any) => sendMessage(data), []);

  return { send };
}
