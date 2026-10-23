/**
 * The live release from health.json (tag, source_updated), fetched once per page load and shared
 * by the footer attribution and the data freshness bar (#185). A failed fetch gives null, so
 * both fall back to showing no date.
 */
import { useEffect, useState } from 'react';
import { apiFetch } from './api';

/** A loader that calls fetchHealth once and hands every caller the same release, or null. */
export const createHealthLoader = (fetchHealth) => {
  let pending = null;
  return () => {
    if (!pending) {
      pending = Promise.resolve()
        .then(fetchHealth)
        .then((response) => response.json())
        .then((body) => body.data ?? null)
        .catch(() => null);
    }
    return pending;
  };
};

export const loadHealth = createHealthLoader(() => apiFetch('health'));

/** The live release: undefined while loading, null when health.json failed, else its data. */
export const useHealth = () => {
  const [release, setRelease] = useState(undefined);
  useEffect(() => {
    let live = true;
    loadHealth().then((data) => live && setRelease(data));
    return () => {
      live = false;
    };
  }, []);
  return release;
};
