import { useEffect, useRef, useCallback } from 'react';

interface SSEEvent {
  type: string;
  [key: string]: any;
}

interface UseSSEOptions {
  /** Whether to enable SSE connection */
  enabled?: boolean;
  /** Reconnect delay in ms */
  reconnectDelay?: number;
  /** Event handler */
  onEvent?: (event: SSEEvent) => void;
}

/**
 * Hook for consuming Server-Sent Events from the backend.
 *
 * Connects to `/api/events/stream` and forwards parsed JSON events
 * to the provided `onEvent` callback.  Automatically reconnects on
 * connection errors after `reconnectDelay` ms.
 */
export function useSSE(options: UseSSEOptions = {}) {
  const { enabled = true, reconnectDelay = 3000, onEvent } = options;
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);

  // Keep a mutable ref so the latest callback is always invoked without
  // needing to tear down / re-create the EventSource every render.
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    // Close any existing connection before opening a new one.
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const es = new EventSource('/api/events/stream');
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const data: SSEEvent = JSON.parse(event.data);
        onEventRef.current?.(data);
      } catch (e) {
        console.error('SSE parse error:', e);
      }
    };

    es.onerror = () => {
      es.close();
      eventSourceRef.current = null;
      // Schedule a reconnect attempt.
      reconnectTimerRef.current = window.setTimeout(() => {
        if (enabled) connect();
      }, reconnectDelay);
    };
  }, [enabled, reconnectDelay]);

  useEffect(() => {
    if (enabled) {
      connect();
    }
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };
  }, [enabled, connect]);
}
