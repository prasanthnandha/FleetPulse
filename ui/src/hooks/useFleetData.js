import { useState, useEffect, useCallback } from 'react';

const API_BASE = '/api';

export function useFleetData() {
  const [overview, setOverview] = useState(null);
  const [devices, setDevices] = useState([]);
  const [trends, setTrends] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedFleet, setSelectedFleet] = useState(null);

  const fetchOverview = useCallback(async (fleetName = null) => {
    try {
      const params = fleetName ? `?fleet_name=${encodeURIComponent(fleetName)}` : '';
      const res = await fetch(`${API_BASE}/fleet/overview${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setOverview(data);
      return data;
    } catch (e) {
      console.error('Failed to fetch overview:', e);
      setError(e.message);
      return null;
    }
  }, []);

  const fetchDevices = useCallback(async (params = {}) => {
    try {
      const query = new URLSearchParams();
      if (params.fleetName) query.set('fleet_name', params.fleetName);
      if (params.riskTier) query.set('risk_tier', params.riskTier);
      if (params.sortBy) query.set('sort_by', params.sortBy);
      if (params.order) query.set('order', params.order);
      if (params.limit) query.set('limit', params.limit.toString());

      const res = await fetch(`${API_BASE}/fleet/devices?${query}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setDevices(data);
      return data;
    } catch (e) {
      console.error('Failed to fetch devices:', e);
      setError(e.message);
      return [];
    }
  }, []);

  const fetchTrends = useCallback(async (fleetName = null, days = 30) => {
    try {
      const params = new URLSearchParams({ days: days.toString() });
      if (fleetName) params.set('fleet_name', fleetName);

      const res = await fetch(`${API_BASE}/fleet/trends?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setTrends(data);
      return data;
    } catch (e) {
      console.error('Failed to fetch trends:', e);
      setError(e.message);
      return null;
    }
  }, []);

  const loadAll = useCallback(async (fleetName = null) => {
    setIsLoading(true);
    setError(null);
    setSelectedFleet(fleetName);

    await Promise.all([
      fetchOverview(fleetName),
      fetchDevices({ fleetName, sortBy: 'overall_risk_score', order: 'desc' }),
      fetchTrends(fleetName),
    ]);

    setIsLoading(false);
  }, [fetchOverview, fetchDevices, fetchTrends]);

  // Load on mount
  useEffect(() => {
    loadAll();
  }, []);

  return {
    overview,
    devices,
    trends,
    isLoading,
    error,
    selectedFleet,
    fetchOverview,
    fetchDevices,
    fetchTrends,
    loadAll,
    setSelectedFleet,
  };
}
