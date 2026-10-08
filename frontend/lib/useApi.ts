"use client";
// Small fetch hook: loading / error / data / refetch — powers every screen's
// skeleton, error, and empty states without a heavier state library.
import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "./api";

interface UseApiState<T> {
  data: T | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[] = []): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  // Reset to the loading state during render whenever the request key changes
  // (React's documented "adjust state during render" pattern — avoids a
  // cascading setState-in-effect).
  const requestKey = `${tick}:${JSON.stringify(deps)}`;
  const [lastRequestKey, setLastRequestKey] = useState<string | null>(null);
  if (requestKey !== lastRequestKey) {
    setLastRequestKey(requestKey);
    setIsLoading(true);
    setError(null);
  }

  // Keep the latest fetcher without retriggering the fetch effect; declared
  // before it so the ref is current when the fetch effect runs.
  const fetcherRef = useRef(fetcher);
  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  useEffect(() => {
    let isActive = true;
    fetcherRef
      .current()
      .then((result) => {
        if (!isActive) return;
        setData(result);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!isActive) return;
        setError(err instanceof ApiError ? err.message : "Something went wrong loading this data.");
      })
      .finally(() => {
        if (isActive) setIsLoading(false);
      });
    return () => {
      isActive = false;
    };
  }, [requestKey]);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  return { data, isLoading, error, refetch };
}
