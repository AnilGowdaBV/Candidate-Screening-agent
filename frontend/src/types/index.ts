export type RunState =
  | 'IDLE'
  | 'VALIDATING'
  | 'RUNNING'
  | 'PAUSE_REQUESTED'
  | 'PAUSED'
  | 'STOP_REQUESTED'
  | 'STOPPED'
  | 'COMPLETED'
  | 'FAILED';

export interface CurrentOperation {
  current_operation: string;
  workflow_stage: string;
  candidate_reference?: string | null;
  current_status: string;
  last_completed_action?: string | null;
  next_planned_action?: string | null;
  warning_or_error?: string | null;
}

export type TechnologyKey = 'golang' | 'python' | 'java' | 'javascript' | 'typescript' | 'frontend' | 'qa_automation';

export interface TechnologyMeta {
  key: TechnologyKey;
  name: string;
  label: string;
  icon: string;
  color: string;
  detectedLabel: string;
  notDetectedLabel: string;
}

export interface SystemStatus {
  status: string;
  version: string;
  run_state: RunState;
  active_run_id: number | null;
  active_technology?: string;
  current_operation: CurrentOperation;
  is_github_configured: boolean;
  is_instahyre_configured: boolean;
  dry_run: boolean;
  instahyre_search_url: string;
  database_ready: boolean;
}

export interface DashboardMetrics {
  candidates_discovered: number;
  candidates_processed: number;
  candidates_remaining: number;
  github_profiles_found: number;
  github_profiles_missing: number;
  go_detected: number;
  go_not_detected: number;
  notes_added: number;
  notes_already_present: number;
  candidates_needing_review: number;
  errors: number;
}

export interface ScreeningResult {
  id: number;
  run_id: number;
  github_status: string;
  go_status: string;
  evidence_summary?: string | null;
  repositories_checked: number;
  checked_at: string;
  error_code?: string | null;
  error_message?: string | null;
  languages_found?: string | null;
}

export interface NoteAction {
  id: number;
  run_id: number;
  note_text: string;
  action_status: string;
  attempted_at: string;
  confirmed_at?: string | null;
  error_message?: string | null;
}

export interface Candidate {
  id: number;
  instahyre_profile_url: string;
  instahyre_external_id?: string | null;
  name: string;
  github_url?: string | null;
  gitroll_rating?: number | null;
  actual_gitroll_score?: number | null;
  gitroll_grade?: string | null;
  gitroll_profile_url?: string | null;
  gitroll_scanned_at?: string | null;
  gitroll_note_status?: string | null;
  current_salary?: string | null;
  location?: string | null;
  experience?: string | null;
  coding_profiles?: string | null;
  languages_found?: string | null;
  created_at: string;
  updated_at: string;
  last_seen_at: string;
  screening_results: ScreeningResult[];
  note_actions: NoteAction[];
}

export interface CandidateListResponse {
  items: Candidate[];
  total: number;
  limit: number;
  offset: number;
}

export interface ScreeningRun {
  id: number;
  status: string;
  started_at: string;
  finished_at?: string | null;
  last_checkpoint?: string | null;
  processed_count: number;
  error_count: number;
  configuration_snapshot?: string | null;
}

export interface ActivityEvent {
  id: number;
  run_id?: number | null;
  candidate_id?: number | null;
  event_type: string;
  message: string;
  created_at: string;
  metadata_json?: string | null;
}
