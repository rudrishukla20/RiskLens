import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { formatLabel, formatCurrencyINR } from '@/lib/formatter';
import {
  ArrowLeft,
  Database,
  CheckCircle,
  AlertTriangle,
  Play,
  Table,
  BarChart,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Search,
  Filter,
  Check,
  Layers,
  History,
  Upload
} from 'lucide-react';

// Standard list of canonical schema fields
const CANONICAL_FIELDS = [
  { value: 'borrower_id', label: 'Borrower ID (borrower_id)' },
  { value: 'age', label: 'Age (age)' },
  { value: 'gender', label: 'Gender (gender)' },
  { value: 'income', label: 'Annual Income (income)' },
  { value: 'employment_type', label: 'Employment Type (employment_type)' },
  { value: 'education_level', label: 'Education Level (education_level)' },
  { value: 'marital_status', label: 'Marital Status (marital_status)' },
  { value: 'region', label: 'Region (region)' },
  { value: 'occupation', label: 'Occupation (occupation)' },
  { value: 'housing_type', label: 'Housing Type (housing_type)' },
  { value: 'family_size', label: 'Family Size (family_size)' },
  { value: 'loan_amount', label: 'Loan Amount (loan_amount)' },
  { value: 'loan_purpose', label: 'Loan Purpose (loan_purpose)' },
  { value: 'interest_rate', label: 'Interest Rate (interest_rate)' },
  { value: 'loan_term', label: 'Loan Term (loan_term)' },
  { value: 'loan_status', label: 'Repayment Status / Default Flag (loan_status)' },
  { value: 'disbursement_date', label: 'Disbursement Date (disbursement_date)' },
  { value: 'outstanding_amount', label: 'Outstanding Amount (outstanding_amount)' },
  { value: 'annuity_amount', label: 'Annuity Amount (annuity_amount)' },
  { value: 'delinquency_days', label: 'Delinquency Days (delinquency_days)' },
  { value: 'historical_default_flag', label: 'Historical Default Flag (historical_default_flag)' },
  { value: 'asset_value', label: 'Asset Value (asset_value)' },
  { value: 'credit_burden', label: 'Credit Burden (credit_burden)' }
];

export const DatasetDetails = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'mapping' | 'validation' | 'profiling' | 'versions'>('mapping');
  
  // Tab 1: Mapping States
  const [mappings, setMappings] = useState<Record<string, string>>({});
  const [mappingSuccess, setMappingSuccess] = useState<string | null>(null);
  const [mappingError, setMappingError] = useState<string | null>(null);

  // Tab 4: Versions States
  const [selectedVersionFile, setSelectedVersionFile] = useState<File | null>(null);
  const [versionUploadError, setVersionUploadError] = useState<string | null>(null);
  const [versionSuccess, setVersionSuccess] = useState<string | null>(null);

  // Tab 2: Validation States
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [issueSearch, setIssueSearch] = useState<string>('');

  // Tab 3: Profiling States (expanded columns)
  const [expandedColumns, setExpandedColumns] = useState<Record<string, boolean>>({});

  // 1. Fetch Dataset Metadata
  const { data: dataset, isLoading: isDatasetLoading } = useQuery({
    queryKey: ['dataset', id],
    queryFn: async () => {
      const res = await apiClient.get(`/datasets/${id}`);
      return res.data;
    },
    enabled: !!id,
  });

  // 2. Fetch Columns
  const { data: columns, isLoading: isColumnsLoading } = useQuery({
    queryKey: ['dataset-columns', id],
    queryFn: async () => {
      const res = await apiClient.get(`/datasets/${id}/columns`);
      return res.data;
    },
    enabled: !!id,
  });

  // Effect to pre-populate mapping choices from current db mappings
  useEffect(() => {
    if (columns) {
      const initial: Record<string, string> = {};
      columns.forEach((col: any) => {
        if (col.is_mapped && col.canonical_column_name) {
          initial[col.original_column_name] = col.canonical_column_name;
        }
      });
      setMappings(initial);
    }
  }, [columns]);

  // 4. Fetch Latest Validation Run
  const { 
    data: latestValidation, 
    refetch: refetchVal 
  } = useQuery({
    queryKey: ['latest-validation', id],
    queryFn: async () => {
      const res = await apiClient.get(`/datasets/${id}/validation/latest`);
      return res.data;
    },
    enabled: !!id,
    // Poll if status is active (RUNNING or PENDING)
    refetchInterval: (query) => {
      const runStatus = query.state.data?.status;
      return (runStatus === 'RUNNING' || runStatus === 'PENDING') ? 3000 : false;
    }
  });

  // 5. Fetch Validation Issues
  const { data: valIssues } = useQuery({
    queryKey: ['validation-issues', id, latestValidation?.id],
    queryFn: async () => {
      if (!latestValidation?.id) return [];
      const res = await apiClient.get(`/datasets/${id}/validation/issues`, {
        params: { run_id: latestValidation.id }
      });
      return res.data;
    },
    enabled: !!id && !!latestValidation?.id,
  });

  // 6. Fetch Latest Profiling Run
  const { 
    data: latestProfiling, 
    refetch: refetchProf 
  } = useQuery({
    queryKey: ['latest-profiling', id],
    queryFn: async () => {
      const res = await apiClient.get(`/datasets/${id}/profile/latest`);
      return res.data;
    },
    enabled: !!id,
    refetchInterval: (query) => {
      const runStatus = query.state.data?.status;
      return (runStatus === 'RUNNING' || runStatus === 'PENDING') ? 3000 : false;
    }
  });

  // 7. Fetch Column Profiles
  const { data: colProfiles } = useQuery({
    queryKey: ['column-profiles', id, latestProfiling?.id],
    queryFn: async () => {
      if (!latestProfiling?.id) return [];
      const res = await apiClient.get(`/datasets/${id}/profile/columns`, {
        params: { run_id: latestProfiling.id }
      });
      return res.data;
    },
    enabled: !!id && !!latestProfiling?.id,
  });

  // --- MUTATIONS ---

  // Confirm Mappings
  const confirmMappingMutation = useMutation({
    mutationFn: async (mappingsList: { original_column_name: string; canonical_field: string }[]) => {
      return await apiClient.post(`/datasets/${id}/schema-mapping/confirm`, {
        mappings: mappingsList
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataset-columns', id] });
      queryClient.invalidateQueries({ queryKey: ['dataset-mappings', id] });
      setMappingSuccess('Schema mapping rules saved and confirmed!');
      setMappingError(null);
      setTimeout(() => setMappingSuccess(null), 3000);
    },
    onError: (err: any) => {
      setMappingError(err.message || 'Failed to save schema mapping configuration.');
    }
  });

  // Run Validation Mutation
  const triggerValidationMutation = useMutation({
    mutationFn: async () => {
      return await apiClient.post(`/datasets/${id}/validate`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['latest-validation', id] });
      refetchVal();
    },
    onError: (err: any) => {
      alert(err.message || 'Failed to trigger validation.');
    }
  });

  // Run Profiling Mutation
  const triggerProfilingMutation = useMutation({
    mutationFn: async () => {
      return await apiClient.post(`/datasets/${id}/profile`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['latest-profiling', id] });
      refetchProf();
    },
    onError: (err: any) => {
      alert(err.message || 'Failed to trigger profiling.');
    }
  });

  // Fetch dataset versions
  const { data: versionsData, isLoading: isVersionsLoading, refetch: refetchVersions } = useQuery({
    queryKey: ['dataset-versions', id],
    queryFn: async () => {
      const res = await apiClient.get(`/datasets/${id}/versions`);
      return res.data;
    },
    enabled: !!id,
  });

  // Upload version mutation
  const uploadVersionMutation = useMutation({
    mutationFn: async (formData: FormData) => {
      return await apiClient.post(`/datasets/${id}/versions/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataset', id] });
      queryClient.invalidateQueries({ queryKey: ['dataset-versions', id] });
      queryClient.invalidateQueries({ queryKey: ['latest-validation', id] });
      queryClient.invalidateQueries({ queryKey: ['latest-profiling', id] });
      setVersionSuccess('New dataset version uploaded and processed successfully!');
      setSelectedVersionFile(null);
      setVersionUploadError(null);
      refetchVersions();
      setTimeout(() => setVersionSuccess(null), 3000);
    },
    onError: (err: any) => {
      setVersionUploadError(err.message || 'Failed to upload new version.');
    },
  });

  // Mapping Handlers
  const handleSelectMapping = (colName: string, value: string) => {
    setMappings((prev) => ({
      ...prev,
      [colName]: value,
    }));
  };

  const handleSaveMappings = () => {
    const list = Object.entries(mappings)
      .filter(([_, value]) => value !== '')
      .map(([original_column_name, canonical_field]) => ({
        original_column_name,
        canonical_field
      }));
    
    confirmMappingMutation.mutate(list);
  };

  const toggleColumnExpand = (colName: string) => {
    setExpandedColumns((prev) => ({
      ...prev,
      [colName]: !prev[colName]
    }));
  };

  const handleVersionFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedVersionFile(e.target.files[0]);
      setVersionUploadError(null);
    }
  };

  const handleVersionUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedVersionFile) {
      setVersionUploadError('Please select a file to upload.');
      return;
    }
    const ext = selectedVersionFile.name.substring(selectedVersionFile.name.lastIndexOf('.')).toLowerCase();
    if (!['.csv', '.xlsx', '.json'].includes(ext)) {
      setVersionUploadError('Only structured formats (.csv, .xlsx, .json) are allowed.');
      return;
    }
    const formData = new FormData();
    formData.append('file', selectedVersionFile);
    uploadVersionMutation.mutate(formData);
  };

  // Filters for validation issues
  const filteredIssues = valIssues?.filter((issue: any) => {
    const matchesSeverity = severityFilter === 'ALL' || issue.severity === severityFilter;
    const matchesSearch =
      issue.column_name?.toLowerCase().includes(issueSearch.toLowerCase()) ||
      issue.message?.toLowerCase().includes(issueSearch.toLowerCase());
    return matchesSeverity && matchesSearch;
  });

  if (isDatasetLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <span className="text-sm font-medium text-muted-foreground text-center">Loading dataset workspace...</span>
        </div>
      </div>
    );
  }

  if (!dataset) {
    return (
      <div className="flex h-64 flex-col items-center justify-center space-y-4">
        <AlertTriangle className="h-12 w-12 text-destructive" />
        <h3 className="text-lg font-bold">Dataset Not Found</h3>
        <p className="text-sm text-muted-foreground">The dataset may have been archived or deleted.</p>
        <Link to="/governance/datasets" className="text-primary hover:underline text-sm font-medium">
          Back to structured catalogs
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back link & breadcrumbs */}
      <div>
        <Link
          to="/governance/datasets"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to structured catalogs</span>
        </Link>
      </div>

      {/* Dataset Identity Header */}
      <div className="flex flex-col gap-4 border-b border-border bg-card p-6 rounded-lg shadow-2xs sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Database className="h-5 w-5" />
            </span>
            <h2 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">{dataset.name}</h2>
          </div>
          <p className="text-sm text-muted-foreground max-w-2xl">{dataset.description || 'No description provided.'}</p>
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            <span className="bg-muted px-2 py-0.5 rounded text-muted-foreground font-mono">Format: {dataset.file_type}</span>
            <span className="bg-muted px-2 py-0.5 rounded text-muted-foreground">Rows: {dataset.record_count?.toLocaleString()}</span>
            <span className="bg-muted px-2 py-0.5 rounded text-muted-foreground">Columns: {dataset.column_count}</span>
          </div>
        </div>

        {/* Big status widgets */}
        <div className="flex flex-wrap gap-3">
          <div className="rounded border border-border bg-background p-3 text-center min-w-[100px]">
            <div className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Validation</div>
            <div
              className={`mt-1 text-sm font-bold ${
                dataset.validation_status === 'PASSED'
                  ? 'text-emerald-500'
                  : dataset.validation_status === 'FAILED'
                  ? 'text-red-500'
                  : 'text-yellow-500'
              }`}
            >
              {dataset.validation_status || 'UNKNOWN'}
            </div>
          </div>
          <div className="rounded border border-border bg-background p-3 text-center min-w-[100px]">
            <div className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Profiling</div>
            <div
              className={`mt-1 text-sm font-bold ${
                dataset.profiling_status === 'COMPLETED' ? 'text-emerald-500' : 'text-yellow-500'
              }`}
            >
              {dataset.profiling_status || 'UNKNOWN'}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs Layout Navigation */}
      <div className="flex border-b border-border bg-card p-1 rounded-md w-fit">
        <button
          onClick={() => setActiveTab('mapping')}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded transition-colors ${
            activeTab === 'mapping'
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground'
          }`}
        >
          <Table className="h-4 w-4" />
          <span>Schema Mapping</span>
        </button>
        <button
          onClick={() => setActiveTab('validation')}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded transition-colors ${
            activeTab === 'validation'
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground'
          }`}
        >
          <ShieldCheck className="h-4 w-4" />
          <span>Data Validation</span>
        </button>
        <button
          onClick={() => setActiveTab('profiling')}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded transition-colors ${
            activeTab === 'profiling'
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground'
          }`}
        >
          <BarChart className="h-4 w-4" />
          <span>Data Profiling</span>
        </button>
        <button
          onClick={() => setActiveTab('versions')}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded transition-colors ${
            activeTab === 'versions'
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground'
          }`}
        >
          <History className="h-4 w-4" />
          <span>Versions History</span>
        </button>
      </div>

      {/* Workspace Pages Body */}
      <div className="bg-card border border-border rounded-lg p-6 shadow-2xs">
        
        {/* TAB 1: SCHEMA MAPPING */}
        {activeTab === 'mapping' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-4">
              <div>
                <h3 className="text-lg font-bold">Canonical Schema Mapping</h3>
                <p className="text-xs text-muted-foreground">
                  Map and align headers in the raw dataset to standard catalog variables inside RiskLens (required for running validation rules).
                </p>
              </div>
              <button
                onClick={handleSaveMappings}
                disabled={confirmMappingMutation.isPending || isColumnsLoading}
                className="rounded bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/95 disabled:opacity-50 transition-colors"
              >
                {confirmMappingMutation.isPending ? 'Saving...' : 'Confirm Schema Mapping'}
              </button>
            </div>

            {mappingSuccess && (
              <div className="flex items-center gap-2 rounded border border-emerald-500/20 bg-emerald-500/10 p-3 text-sm text-emerald-500">
                <CheckCircle className="h-5 w-5" />
                <span>{mappingSuccess}</span>
              </div>
            )}
            {mappingError && (
              <div className="flex items-center gap-2 rounded border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">
                <AlertTriangle className="h-5 w-5" />
                <span>{mappingError}</span>
              </div>
            )}

            {isColumnsLoading ? (
              <div className="space-y-3 animate-pulse">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-14 bg-muted rounded"></div>
                ))}
              </div>
            ) : (
              <div className="overflow-x-auto rounded border border-border">
                <table className="w-full text-left border-collapse" aria-label="Column Mapping Table">
                  <thead>
                    <tr className="border-b border-border bg-muted/30 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      <th className="px-6 py-3">Raw Column Header</th>
                      <th className="px-6 py-3">Inferred Type</th>
                      <th className="px-6 py-3">Sample Values</th>
                      <th className="px-6 py-3">Target Canonical Field</th>
                      <th className="px-6 py-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="text-sm divide-y divide-border">
                    {columns?.map((col: any) => {
                      const isMapped = !!mappings[col.original_column_name];
                      return (
                        <tr key={col.id} className="hover:bg-muted/10">
                          <td className="px-6 py-4 font-semibold text-foreground">{col.original_column_name}</td>
                          <td className="px-6 py-4">
                            <span className="font-mono text-2xs bg-muted px-1.5 py-0.5 rounded text-muted-foreground uppercase">
                              {col.inferred_data_type}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <span className="text-xs text-muted-foreground truncate max-w-[200px] block" title={JSON.stringify(col.sample_values)}>
                              {Array.isArray(col.sample_values) ? col.sample_values.join(', ') : String(col.sample_values || '')}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <select
                              value={mappings[col.original_column_name] || ''}
                              onChange={(e) => handleSelectMapping(col.original_column_name, e.target.value)}
                              className="block w-full rounded border border-border bg-transparent px-3 py-1.5 text-xs text-foreground focus:border-primary focus:ring-1 focus:ring-primary"
                            >
                              <option value="" className="bg-card">-- Ignore / Unmapped --</option>
                              {CANONICAL_FIELDS.map((field) => (
                                <option key={field.value} value={field.value} className="bg-card">
                                  {field.label}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td className="px-6 py-4 text-center">
                            {isMapped ? (
                              <span className="inline-flex rounded-full bg-emerald-500/10 p-1 text-emerald-500 border border-emerald-500/20" title="Mapped">
                                <Check className="h-4 w-4" />
                              </span>
                            ) : (
                              <span className="text-2xs text-muted-foreground italic">Ignored</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: DATA VALIDATION */}
        {activeTab === 'validation' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-4">
              <div>
                <h3 className="text-lg font-bold">Data Quality Validation</h3>
                <p className="text-xs text-muted-foreground">
                  Run validation rules to flag missing values, outliers, type violations, or credit default logic anomalies.
                </p>
              </div>
              <button
                onClick={() => triggerValidationMutation.mutate()}
                disabled={triggerValidationMutation.isPending || (latestValidation?.status === 'RUNNING' || latestValidation?.status === 'PENDING')}
                className="inline-flex items-center gap-1.5 rounded bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/95 disabled:opacity-50 transition-colors"
              >
                {(latestValidation?.status === 'RUNNING' || latestValidation?.status === 'PENDING') ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    <span>Validating...</span>
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4" />
                    <span>Run Quality Validation</span>
                  </>
                )}
              </button>
            </div>

            {/* Validation Pending/Running Alert */}
            {(latestValidation?.status === 'RUNNING' || latestValidation?.status === 'PENDING') && (
              <div className="flex items-center gap-3 rounded-lg border border-yellow-500/20 bg-yellow-500/10 p-4 text-sm text-yellow-600 dark:text-yellow-400">
                <RefreshCw className="h-5 w-5 animate-spin" />
                <div>
                  <span className="font-semibold">Validation run is in progress ({latestValidation.status}).</span> Checking for updates automatically...
                </div>
              </div>
            )}

            {latestValidation ? (
              <div className="space-y-6">
                {/* Stats Widgets Grid */}
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-7">
                  <div className="rounded-lg border border-border p-4 bg-muted/20 text-center col-span-2 sm:col-span-2">
                    <div className="text-2xs font-bold text-muted-foreground uppercase tracking-wider">Quality Score</div>
                    <div className="mt-1 text-3xl font-black text-foreground">
                      {latestValidation.validation_score !== undefined && latestValidation.validation_score !== null ? `${latestValidation.validation_score}/100` : 'N/A'}
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-1">Weighted metric based on exceptions</p>
                  </div>
                  <div className="rounded-lg border border-border p-4 bg-card text-center">
                    <div className="text-2xs font-semibold text-muted-foreground uppercase">Valid Records</div>
                    <div className="mt-1 text-xl font-bold text-emerald-500">
                      {latestValidation.valid_records?.toLocaleString() || 0}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border p-4 bg-card text-center">
                    <div className="text-2xs font-semibold text-muted-foreground uppercase">Invalid Records</div>
                    <div className="mt-1 text-xl font-bold text-red-500">
                      {latestValidation.invalid_records?.toLocaleString() || 0}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border p-4 bg-card text-center">
                    <div className="text-2xs font-semibold text-muted-foreground uppercase">Errors</div>
                    <div className="mt-1 text-xl font-bold text-red-500">
                      {latestValidation.error_count?.toLocaleString() || 0}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border p-4 bg-card text-center">
                    <div className="text-2xs font-semibold text-muted-foreground uppercase">Warnings</div>
                    <div className="mt-1 text-xl font-bold text-yellow-500">
                      {latestValidation.warning_count?.toLocaleString() || 0}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border p-4 bg-card text-center col-span-2 sm:col-span-1 lg:col-span-1">
                    <div className="text-2xs font-semibold text-muted-foreground uppercase">Info Messages</div>
                    <div className="mt-1 text-xl font-bold text-blue-500">
                      {latestValidation.info_count?.toLocaleString() || 0}
                    </div>
                  </div>
                </div>

                {/* Filter and issues list */}
                <div className="space-y-4 pt-4 border-t border-border">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <h4 className="font-bold text-base">Granular Validation Exceptions</h4>
                    
                    <div className="flex flex-wrap items-center gap-2">
                      {/* Search */}
                      <div className="relative">
                        <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                        <input
                          type="text"
                          value={issueSearch}
                          onChange={(e) => setIssueSearch(e.target.value)}
                          placeholder="Search column or message..."
                          className="pl-8 rounded border border-border bg-transparent px-3 py-1.5 text-xs text-foreground focus:ring-1 focus:ring-primary w-48"
                        />
                      </div>

                      {/* Severity Dropdown */}
                      <div className="flex items-center gap-1">
                        <Filter className="h-3.5 w-3.5 text-muted-foreground" />
                        <select
                          value={severityFilter}
                          onChange={(e) => setSeverityFilter(e.target.value)}
                          className="rounded border border-border bg-transparent px-3 py-1.5 text-xs text-foreground focus:ring-1 focus:ring-primary"
                        >
                          <option value="ALL" className="bg-card">All Severities</option>
                          <option value="ERROR" className="bg-card">Critical</option>
                          <option value="WARNING" className="bg-card">Warning</option>
                          <option value="INFO" className="bg-card">Info</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* Issues Table */}
                  <div className="overflow-x-auto rounded border border-border">
                    <table className="w-full text-left border-collapse" aria-label="Validation Exceptions List">
                      <thead>
                        <tr className="border-b border-border bg-muted/30 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                          <th className="px-6 py-3">Row #</th>
                          <th className="px-6 py-3">Column Name</th>
                          <th className="px-6 py-3">Exception Category</th>
                          <th className="px-6 py-3">Severity</th>
                          <th className="px-6 py-3">Violation Message</th>
                          <th className="px-6 py-3">Observed Value</th>
                        </tr>
                      </thead>
                      <tbody className="text-sm divide-y divide-border">
                        {filteredIssues?.map((issue: any) => (
                          <tr key={issue.id} className="hover:bg-muted/10">
                            <td className="px-6 py-4 font-mono text-xs text-muted-foreground">{issue.source_row_number}</td>
                            <td className="px-6 py-4 font-semibold text-foreground">{issue.column_name || 'N/A'}</td>
                            <td className="px-6 py-4 text-xs font-mono">{issue.issue_type}</td>
                            <td className="px-6 py-4">
                              <span
                                className={`inline-flex rounded px-2 py-0.5 text-2xs font-semibold border ${
                                  (issue.severity === 'ERROR' || issue.severity === 'CRITICAL')
                                    ? 'bg-red-500/10 text-red-500 border-red-500/20'
                                    : issue.severity === 'WARNING'
                                    ? 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'
                                    : 'bg-indigo-500/10 text-indigo-500 border-indigo-500/20'
                                }`}
                              >
                                {issue.severity}
                              </span>
                            </td>
                            <td className="px-6 py-4 text-xs">{formatLabel(issue.message)}</td>
                            <td className="px-6 py-4 font-mono text-xs text-muted-foreground truncate max-w-[120px]" title={formatLabel(issue.observed_value)}>
                              {formatLabel(issue.observed_value) || 'None'}
                            </td>
                          </tr>
                        ))}
                        {filteredIssues?.length === 0 && (
                          <tr>
                            <td colSpan={6} className="text-center py-8 text-muted-foreground text-xs italic">
                              No validation issues match current filters.
                            </td>
                          </tr>
                        )}
                        {valIssues?.length === 0 && (
                          <tr>
                            <td colSpan={6} className="text-center py-8 text-muted-foreground text-xs">
                              No issues flagged for this run. Perfect schema health!
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center border-2 border-dashed border-border rounded-lg bg-muted/10">
                <ShieldCheck className="h-10 w-10 text-muted-foreground mb-2" />
                <h4 className="font-semibold text-base">No Quality Validation Runs Logged</h4>
                <p className="text-xs text-muted-foreground max-w-sm mt-1 mb-4">
                  Run standard quality schemas checks to calculate validation score, nulls percentages, and detect outliers.
                </p>
                <button
                  onClick={() => triggerValidationMutation.mutate()}
                  disabled={triggerValidationMutation.isPending}
                  className="rounded bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/95 transition-colors"
                >
                  Run Validation First
                </button>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: DATA PROFILING */}
        {activeTab === 'profiling' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-4">
              <div>
                <h3 className="text-lg font-bold">Statistical Data Profiling</h3>
                <p className="text-xs text-muted-foreground">
                  View structural overview, duplicates density, variables ranges, variance, and sample distributions.
                </p>
              </div>
              <button
                onClick={() => triggerProfilingMutation.mutate()}
                disabled={triggerProfilingMutation.isPending || (latestProfiling?.status === 'RUNNING' || latestProfiling?.status === 'PENDING')}
                className="inline-flex items-center gap-1.5 rounded bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/95 disabled:opacity-50 transition-colors"
              >
                {(latestProfiling?.status === 'RUNNING' || latestProfiling?.status === 'PENDING') ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    <span>Profiling...</span>
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4" />
                    <span>Run Data Profiling</span>
                  </>
                )}
              </button>
            </div>

            {/* Profiling Pending/Running Alert */}
            {(latestProfiling?.status === 'RUNNING' || latestProfiling?.status === 'PENDING') && (
              <div className="flex items-center gap-3 rounded-lg border border-yellow-500/20 bg-yellow-500/10 p-4 text-sm text-yellow-600 dark:text-yellow-400">
                <RefreshCw className="h-5 w-5 animate-spin" />
                <div>
                  <span className="font-semibold">Profiling run is in progress ({latestProfiling.status}).</span> Checking for updates automatically...
                </div>
              </div>
            )}

            {latestProfiling ? (
              <div className="space-y-6 animate-fade-in">
                {/* Stats overview cards */}
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                  <div className="rounded-lg border border-border p-4 bg-muted/20 text-center">
                    <div className="text-2xs font-bold text-muted-foreground uppercase tracking-wider">Health Score</div>
                    <div className="mt-1 text-2xl font-black text-foreground">
                      {latestProfiling.dataset_health_score !== undefined && latestProfiling.dataset_health_score !== null ? `${latestProfiling.dataset_health_score}%` : 'N/A'}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border p-4 bg-card text-center">
                    <div className="text-2xs font-semibold text-muted-foreground uppercase">Ingested Rows</div>
                    <div className="mt-1 text-lg font-bold text-foreground">
                      {latestProfiling.row_count?.toLocaleString() || 0}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border p-4 bg-card text-center">
                    <div className="text-2xs font-semibold text-muted-foreground uppercase">Missing Density</div>
                    <div className="mt-1 text-lg font-bold text-foreground">
                      {latestProfiling.missing_percentage ? `${latestProfiling.missing_percentage.toFixed(2)}%` : '0%'}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border p-4 bg-card text-center">
                    <div className="text-2xs font-semibold text-muted-foreground uppercase">Duplicate Rows</div>
                    <div className="mt-1 text-lg font-bold text-foreground">
                      {latestProfiling.duplicate_percentage ? `${latestProfiling.duplicate_percentage.toFixed(2)}%` : '0%'}
                    </div>
                  </div>
                </div>

                {/* Granular column statistics cards */}
                <div className="space-y-4 pt-4 border-t border-border">
                  <h4 className="font-bold text-base">Variables Statistical Profiling</h4>
                  <div className="grid grid-cols-1 gap-4">
                    {colProfiles?.map((col: any) => {
                      const isExpanded = !!expandedColumns[col.column_name];
                      const hasStats = col.mean_value !== null || col.min_value !== null || col.max_value !== null;
                      return (
                        <div key={col.id} className="rounded-lg border border-border bg-card overflow-hidden hover:border-border/120 transition-colors">
                          <button
                            onClick={() => toggleColumnExpand(col.column_name)}
                            className="flex items-center justify-between w-full p-4 text-left hover:bg-muted/10 transition-colors"
                          >
                            <div className="flex flex-wrap items-center gap-3">
                              <span className="font-semibold text-base text-foreground">{col.column_name}</span>
                              <span className="font-mono text-2xs bg-muted px-1.5 py-0.5 rounded text-muted-foreground uppercase">
                                {col.data_type}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                Nulls: {col.missing_count?.toLocaleString()} ({col.missing_percentage?.toFixed(2)}%)
                              </span>
                              <span className="text-xs text-muted-foreground">
                                Unique values: {col.unique_count?.toLocaleString()}
                              </span>
                            </div>
                            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          </button>

                          {isExpanded && (
                            <div className="border-t border-border p-4 bg-muted/10 space-y-4 animate-slide-down">
                              
                              {/* Statistics metrics grid */}
                              {hasStats ? (
                                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-7">
                                  <div className="bg-card border border-border/80 p-2.5 rounded text-center">
                                    <div className="text-3xs uppercase font-bold text-muted-foreground">Mean</div>
                                    <div className="text-xs font-semibold mt-1 truncate">{col.mean_value?.toFixed(4)}</div>
                                  </div>
                                  <div className="bg-card border border-border/80 p-2.5 rounded text-center">
                                    <div className="text-3xs uppercase font-bold text-muted-foreground">Median</div>
                                    <div className="text-xs font-semibold mt-1 truncate">{col.median_value?.toFixed(4)}</div>
                                  </div>
                                  <div className="bg-card border border-border/80 p-2.5 rounded text-center">
                                    <div className="text-3xs uppercase font-bold text-muted-foreground">Min</div>
                                    <div className="text-xs font-semibold mt-1 truncate">{col.min_value}</div>
                                  </div>
                                  <div className="bg-card border border-border/80 p-2.5 rounded text-center">
                                    <div className="text-3xs uppercase font-bold text-muted-foreground">Max</div>
                                    <div className="text-xs font-semibold mt-1 truncate">{col.max_value}</div>
                                  </div>
                                  <div className="bg-card border border-border/80 p-2.5 rounded text-center">
                                    <div className="text-3xs uppercase font-bold text-muted-foreground">Std Dev</div>
                                    <div className="text-xs font-semibold mt-1 truncate">{col.std_dev?.toFixed(4)}</div>
                                  </div>
                                  <div className="bg-card border border-border/80 p-2.5 rounded text-center">
                                    <div className="text-3xs uppercase font-bold text-muted-foreground">25th %</div>
                                    <div className="text-xs font-semibold mt-1 truncate">{col.percentile_25?.toFixed(4)}</div>
                                  </div>
                                  <div className="bg-card border border-border/80 p-2.5 rounded text-center">
                                    <div className="text-3xs uppercase font-bold text-muted-foreground">75th %</div>
                                    <div className="text-xs font-semibold mt-1 truncate">{col.percentile_75?.toFixed(4)}</div>
                                  </div>
                                </div>
                              ) : (
                                <div className="text-xs text-muted-foreground italic">
                                  No numerical stats for this type of column variable.
                                </div>
                              )}

                              {/* Distribution bars */}
                              {col.distribution && typeof col.distribution === 'object' && Object.keys(col.distribution as object).length > 0 && (
                                <div className="space-y-2 pt-2 border-t border-border/60">
                                  <div className="text-xs font-bold text-foreground flex items-center gap-1">
                                    <Layers className="h-3.5 w-3.5 text-primary" />
                                    <span>Variable Value Distributions (Top Categories / Intervals)</span>
                                  </div>
                                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                                    {Object.entries(col.distribution as Record<string, any>).slice(0, 8).map(([val, count]: [string, any]) => {
                                      const rowTotal = latestProfiling.row_count || 1;
                                      const pct = ((count / rowTotal) * 100).toFixed(1);
                                      return (
                                        <div key={val} className="space-y-1">
                                          <div className="flex justify-between text-2xs font-medium">
                                            <span className="truncate max-w-[200px] text-foreground font-mono" title={val}>{val || 'NULL / Empty'}</span>
                                            <span className="text-muted-foreground">{count?.toLocaleString()} ({pct}%)</span>
                                          </div>
                                          <div className="w-full bg-muted rounded-full h-1.5">
                                            <div
                                              className="bg-primary h-1.5 rounded-full"
                                              style={{ width: `${Math.min(100, Math.max(1, parseFloat(pct)))}%` }}
                                            ></div>
                                          </div>
                                        </div>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {/* Outliers Warning */}
                              {col.outlier_count > 0 && (
                                <div className="flex items-center gap-2 rounded bg-red-500/10 border border-red-500/20 p-2.5 text-2xs text-red-500">
                                  <AlertTriangle className="h-4 w-4 shrink-0" />
                                  <span>
                                    Detected <strong>{col.outlier_count} potential outlier values</strong> in this variable distribution. Ensure mappings/bounds are correct.
                                  </span>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center border-2 border-dashed border-border rounded-lg bg-muted/10">
                <BarChart className="h-10 w-10 text-muted-foreground mb-2" />
                <h4 className="font-semibold text-base">No Dataset Profiling Logs found</h4>
                <p className="text-xs text-muted-foreground max-w-sm mt-1 mb-4">
                  Generate descriptive statistics profiles including variance, std dev, uniques density, and category distributions.
                </p>
                <button
                  onClick={() => triggerProfilingMutation.mutate()}
                  disabled={triggerProfilingMutation.isPending}
                  className="rounded bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/95 transition-colors"
                >
                  Run Profiling First
                </button>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: VERSION HISTORY */}
        {activeTab === 'versions' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-6 border-b border-border pb-6">
              <div>
                <h3 className="text-lg font-bold">Dataset Version Management</h3>
                <p className="text-xs text-muted-foreground">
                  Upload a new snapshot file of the same schema to add a version. Risk Migration will compare version assessments dynamically.
                </p>
              </div>

              {/* Upload Form */}
              <form onSubmit={handleVersionUploadSubmit} className="flex flex-col sm:flex-row items-end gap-3 max-w-md w-full bg-muted/30 p-4 rounded-lg border border-border">
                <div className="w-full">
                  <label className="block text-2xs font-bold text-muted-foreground uppercase tracking-wider mb-1.5">
                    Select new version file (.csv, .xlsx, .json)
                  </label>
                  <input
                    type="file"
                    accept=".csv,.xlsx,.json"
                    onChange={handleVersionFileChange}
                    className="block w-full text-xs text-muted-foreground file:mr-4 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20"
                    disabled={uploadVersionMutation.isPending}
                  />
                </div>
                <button
                  type="submit"
                  disabled={uploadVersionMutation.isPending || !selectedVersionFile}
                  className="rounded bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/95 disabled:opacity-50 transition-colors shrink-0"
                >
                  {uploadVersionMutation.isPending ? 'Uploading...' : 'Upload Version'}
                </button>
              </form>
            </div>

            {versionSuccess && (
              <div className="flex items-center gap-2 rounded border border-emerald-500/20 bg-emerald-500/10 p-3 text-sm text-emerald-500">
                <CheckCircle className="h-5 w-5" />
                <span>{versionSuccess}</span>
              </div>
            )}
            {versionUploadError && (
              <div className="flex items-center gap-2 rounded border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">
                <AlertTriangle className="h-5 w-5" />
                <span>{versionUploadError}</span>
              </div>
            )}

            {isVersionsLoading ? (
              <div className="h-32 bg-muted/10 border border-border rounded animate-pulse"></div>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-border bg-card">
                <table className="w-full text-left border-collapse" aria-label="Dataset Versions">
                  <thead>
                    <tr className="border-b border-border bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      <th className="px-6 py-3">Version</th>
                      <th className="px-6 py-3">File Reference</th>
                      <th className="px-6 py-3">Rows / Columns</th>
                      <th className="px-6 py-3">Ingested At</th>
                      <th className="px-6 py-3 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="text-sm divide-y divide-border">
                    {versionsData?.map((v: any) => {
                      const isActive = dataset.active_version_id === v.id;
                      return (
                        <tr key={v.id} className={`hover:bg-muted/5 transition-colors ${isActive ? 'bg-primary/5' : ''}`}>
                          <td className="px-6 py-4 font-mono font-bold text-foreground">
                            v{v.version_number}
                          </td>
                          <td className="px-6 py-4">
                            <span className="font-mono text-xs text-muted-foreground" title={v.storage_path}>
                              {v.storage_path?.substring(v.storage_path.lastIndexOf('/') + 1) || v.storage_path?.substring(v.storage_path.lastIndexOf('\\') + 1)}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <span className="font-semibold text-foreground">{v.row_count?.toLocaleString()} rows</span>
                            <span className="text-xs text-muted-foreground block">{v.column_count} columns</span>
                          </td>
                          <td className="px-6 py-4 text-xs text-muted-foreground font-mono">
                            {new Date(v.created_at).toLocaleString()}
                          </td>
                          <td className="px-6 py-4 text-right">
                            {isActive ? (
                              <span className="inline-flex rounded-full bg-emerald-500/10 px-2 py-0.5 text-2xs font-semibold text-emerald-500 border border-emerald-500/20">
                                Active Version
                              </span>
                            ) : (
                              <span className="inline-flex rounded-full bg-muted px-2 py-0.5 text-2xs font-semibold text-muted-foreground border border-border">
                                Archive Baseline
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
export default DatasetDetails;
