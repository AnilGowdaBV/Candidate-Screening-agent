import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { TechnologyCards } from './components/TechnologyCards';
import { ControlPanel } from './components/ControlPanel';
import { CurrentOperationCard } from './components/CurrentOperationCard';
import { WorkflowTracker } from './components/WorkflowTracker';
import { MetricsCards } from './components/MetricsCards';
import { ActivityTimeline } from './components/ActivityTimeline';
import { CandidateExplorer } from './components/CandidateExplorer';
import { RunHistory } from './components/RunHistory';

import {
  fetchStatus,
  fetchMetrics,
  fetchEvents,
  fetchCandidates,
  fetchRuns,
  startRun,
  pauseRun,
  resumeRun,
  stopRun,
} from './services/api';

import {
  SystemStatus,
  DashboardMetrics,
  ActivityEvent,
  Candidate,
  ScreeningRun,
  TechnologyKey,
} from './types';

export const App: React.FC = () => {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [candidateTotal, setCandidateTotal] = useState(0);
  const [runs, setRuns] = useState<ScreeningRun[]>([]);

  // Multi-Technology State
  const [selectedTechnology, setSelectedTechnology] = useState<TechnologyKey>('golang');
  const [searchUrl, setSearchUrl] = useState<string>('');
  const [techCounts, setTechCounts] = useState<Record<TechnologyKey, number>>({
    golang: 177,
    python: 0,
    java: 0,
    javascript: 0,
    typescript: 0,
    frontend: 0,
    qa_automation: 0,
  });

  // Search & filter state
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState('');
  const [pageSize, setPageSize] = useState<number>(500);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch counts for all technologies to display on top cards
  const refreshAllCounts = useCallback(async () => {
    const keys: TechnologyKey[] = ['golang', 'python', 'java', 'javascript', 'typescript', 'frontend', 'qa_automation'];
    const results = await Promise.allSettled(keys.map((k) => fetchMetrics(k)));
    setTechCounts((prev) => {
      const updated = { ...prev };
      results.forEach((res, idx) => {
        if (res.status === 'fulfilled') {
          updated[keys[idx]] =
            res.value.candidates_processed || res.value.candidates_discovered || 0;
        }
      });
      return updated;
    });
  }, []);

  // Load core status and metrics for selected technology
  const refreshCore = useCallback(async () => {
    try {
      const [statusData, metricsData, eventsData] = await Promise.all([
        fetchStatus(),
        fetchMetrics(selectedTechnology),
        fetchEvents(100),
      ]);
      setStatus(statusData);
      setMetrics(metricsData);
      setEvents(eventsData);
    } catch (err) {
      console.error('Failed to refresh core status:', err);
    }
  }, [selectedTechnology]);

  // Load candidate list for selected technology (defaults to 500 to show all candidates)
  const refreshCandidates = useCallback(async () => {
    try {
      const data = await fetchCandidates(search, activeFilter, pageSize, 0, selectedTechnology);
      setCandidates(data.items);
      setCandidateTotal(data.total);
    } catch (err) {
      console.error('Failed to refresh candidates:', err);
    }
  }, [search, activeFilter, pageSize, selectedTechnology]);

  // Load runs for selected technology (last 5 runs)
  const refreshRuns = useCallback(async () => {
    try {
      const data = await fetchRuns(5, selectedTechnology);
      setRuns(data);
    } catch (err) {
      console.error('Failed to refresh runs:', err);
    }
  }, [selectedTechnology]);

  // Initial load and on technology switch
  useEffect(() => {
    refreshCore();
    refreshCandidates();
    refreshRuns();
    refreshAllCounts();
  }, [refreshCore, refreshCandidates, refreshRuns, refreshAllCounts]);

  // Connect to live SSE stream for real-time activity events
  useEffect(() => {
    const eventSource = new EventSource('/api/events/stream');
    eventSource.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        const newEvent: ActivityEvent = {
          id: Math.floor(Date.now() + Math.random() * 1000),
          run_id: parsed.run_id,
          candidate_id: parsed.candidate_id,
          event_type: parsed.event_type,
          message: parsed.message,
          created_at: new Date().toISOString(),
          metadata_json: JSON.stringify(parsed.metadata),
        };
        setEvents((prev) => [...prev, newEvent]);
        refreshCore();
        refreshCandidates();
        refreshAllCounts();
      } catch (err) {
        console.error('SSE parse error:', err);
      }
    };
    return () => {
      eventSource.close();
    };
  }, [refreshCore, refreshCandidates, refreshAllCounts]);

  // Fallback poll interval (every 4s)
  useEffect(() => {
    const timer = setInterval(() => {
      refreshCore();
      refreshCandidates();
      refreshAllCounts();
    }, 4000);
    return () => clearInterval(timer);
  }, [refreshCore, refreshCandidates, refreshAllCounts]);

  // Actions
  const handleStart = async () => {
    if (!searchUrl || !searchUrl.trim().startsWith('http')) {
      alert(`Instahyre Search URL is required. Please paste your filtered Instahyre search URL before starting.`);
      return;
    }
    setIsLoading(true);
    try {
      const res = await startRun(selectedTechnology, searchUrl.trim());
      if (!res.success) alert(res.message);
      await refreshCore();
      await refreshRuns();
      await refreshAllCounts();
    } catch (err) {
      alert('Error starting run: ' + String(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handlePause = async () => {
    setIsLoading(true);
    try {
      const res = await pauseRun();
      if (!res.success) alert(res.message);
      await refreshCore();
    } catch (err) {
      alert('Error pausing run: ' + String(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handleResume = async () => {
    setIsLoading(true);
    try {
      const res = await resumeRun();
      if (!res.success) alert(res.message);
      await refreshCore();
    } catch (err) {
      alert('Error resuming run: ' + String(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handleStop = async () => {
    setIsLoading(true);
    try {
      const res = await stopRun();
      if (!res.success) alert(res.message);
      await refreshCore();
      await refreshRuns();
    } catch (err) {
      alert('Error stopping run: ' + String(err));
    } finally {
      setIsLoading(false);
    }
  };

  const isRunActive = status?.run_state === 'RUNNING' || status?.run_state === 'VALIDATING';

  return (
    <div className="app-container">
      {/* 1. Application Header */}
      <Header status={status} selectedTechnology={selectedTechnology} />

      {/* 2. Top-Level Multi-Technology Workspace Cards */}
      <TechnologyCards
        selectedTechnology={selectedTechnology}
        onSelectTechnology={setSelectedTechnology}
        candidateCounts={techCounts}
      />

      {/* 3. Configuration, Skill Target Dropdown & URL Input Controls */}
      <ControlPanel
        status={status}
        selectedTechnology={selectedTechnology}
        onSelectTechnology={setSelectedTechnology}
        searchUrl={searchUrl}
        onSearchUrlChange={setSearchUrl}
        onStart={handleStart}
        onPause={handlePause}
        onResume={handleResume}
        onStop={handleStop}
        isLoading={isLoading}
      />

      {/* 4. Live Operation & Workflow Stage */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 360px), 1fr))', gap: '20px' }}>
        <CurrentOperationCard
          operation={status?.current_operation}
          runState={status?.run_state}
        />
        <WorkflowTracker
          currentStage={status?.current_operation?.workflow_stage}
          isRunActive={isRunActive}
        />
      </div>

      {/* 5. Dashboard Metrics Grid (Dynamically labeled for selected tech) */}
      <MetricsCards
        metrics={metrics}
        activeFilter={activeFilter}
        onSelectFilter={setActiveFilter}
        selectedTechnology={selectedTechnology}
      />

      {/* 6. Candidate Explorer Table */}
      <CandidateExplorer
        candidates={candidates}
        total={candidateTotal}
        search={search}
        onSearchChange={setSearch}
        activeFilter={activeFilter}
        onFilterChange={setActiveFilter}
        onRefresh={refreshCandidates}
        selectedTechnology={selectedTechnology}
        pageSize={pageSize}
        onPageSizeChange={setPageSize}
      />

      {/* 7. Live Activity Timeline */}
      <ActivityTimeline events={events} />

      {/* 8. Run History */}
      <RunHistory runs={runs} onRefresh={refreshRuns} />
    </div>
  );
};
