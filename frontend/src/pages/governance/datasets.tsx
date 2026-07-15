import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import apiClient from '@/lib/api-client';
import {
  Database,
  Upload,
  Archive,
  AlertTriangle,
  FileSpreadsheet,
  FileJson,
  FileIcon,
  Plus,
  ExternalLink,
  ChevronRight,
  Sparkles,
  Info
} from 'lucide-react';

export const DatasetsPage = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  
  const [uploadOpen, setUploadOpen] = useState(false);
  const [archiveConfirmOpen, setArchiveConfirmOpen] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState<any | null>(null);
  
  // Form states
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Fetch structured datasets list
  const { data: datasetData, isLoading: isDatasetsLoading, error: datasetsError } = useQuery({
    queryKey: ['datasets'],
    queryFn: async () => {
      const res = await apiClient.get('/datasets');
      return res.data;
    },
  });

  // Fetch public reference dataset sources
  const { data: publicSources, isLoading: isSourcesLoading } = useQuery({
    queryKey: ['public-sources'],
    queryFn: async () => {
      const res = await apiClient.get('/public-dataset-sources');
      return res.data;
    },
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async (formData: FormData) => {
      return await apiClient.post('/datasets/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
      setSuccessMsg('Dataset uploaded and queued for parsing successfully!');
      setName('');
      setDescription('');
      setSelectedFile(null);
      setUploadError(null);
      setTimeout(() => {
        setUploadOpen(false);
        setSuccessMsg(null);
      }, 2000);
    },
    onError: (err: any) => {
      setUploadError(err.message || 'Failed to upload dataset. Please verify format/rules.');
    },
  });

  // Archive/Delete mutation
  const archiveMutation = useMutation({
    mutationFn: async (id: string) => {
      return await apiClient.delete(`/datasets/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
      setArchiveConfirmOpen(false);
    },
    onError: (err: any) => {
      alert(err.message || 'Failed to archive dataset.');
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setUploadError(null);
    }
  };

  const handleUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setUploadError('Dataset display name is required.');
      return;
    }
    if (!selectedFile) {
      setUploadError('Please select a file to upload.');
      return;
    }
    
    // Check file extension
    const ext = selectedFile.name.substring(selectedFile.name.lastIndexOf('.')).toLowerCase();
    if (!['.csv', '.xlsx', '.json'].includes(ext)) {
      setUploadError('Only structured data formats (.csv, .xlsx, .json) are allowed.');
      return;
    }

    const formData = new FormData();
    formData.append('name', name);
    formData.append('description', description);
    formData.append('file', selectedFile);

    uploadMutation.mutate(formData);
  };

  const getFileIcon = (fileType: string) => {
    switch (fileType?.toUpperCase()) {
      case 'CSV':
      case 'XLSX':
        return <FileSpreadsheet className="h-5 w-5 text-emerald-500" />;
      case 'JSON':
        return <FileJson className="h-5 w-5 text-indigo-500" />;
      default:
        return <FileIcon className="h-5 w-5 text-muted-foreground" />;
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">Structured Data Catalogs</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Manage credit risk data tables, upload files, configure schema alignments, and view profiling metrics.
          </p>
        </div>
        <button
          onClick={() => {
            setUploadOpen(true);
            setUploadError(null);
            setSuccessMsg(null);
          }}
          className="inline-flex items-center gap-2 rounded bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/95 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        >
          <Plus className="h-4 w-4" />
          <span>Upload Dataset</span>
        </button>
      </div>

      {/* Datasets Table */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold tracking-tight">Active Ingested Catalogs</h3>
        
        {datasetsError && (
          <div className="flex items-center gap-2 rounded border border-destructive/20 bg-destructive/10 p-4 text-destructive">
            <AlertTriangle className="h-5 w-5" />
            <span>Failed to load active datasets. Ensure the backend api server is running.</span>
          </div>
        )}

        {isDatasetsLoading ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((n) => (
              <div key={n} className="h-40 rounded-lg border border-border bg-card p-6 animate-pulse space-y-4">
                <div className="h-4 bg-muted rounded w-3/4"></div>
                <div className="h-4 bg-muted rounded w-1/2"></div>
                <div className="h-4 bg-muted rounded w-1/4"></div>
              </div>
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-border bg-card shadow-sm">
            <table className="w-full text-left border-collapse" aria-label="Structured Datasets">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  <th className="px-6 py-3">Dataset Details</th>
                  <th className="px-6 py-3">Source Properties</th>
                  <th className="px-6 py-3">Rows / Columns</th>
                  <th className="px-6 py-3">Processing Status</th>
                  <th className="px-6 py-3">Ingested At</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="text-sm divide-y divide-border">
                {datasetData?.items?.filter((ds: any) => !ds.archived_at).map((ds: any) => (
                  <tr key={ds.id} className="hover:bg-muted/10 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-semibold text-foreground text-base">{ds.name}</div>
                      {ds.description && <div className="text-xs text-muted-foreground line-clamp-1">{ds.description}</div>}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {getFileIcon(ds.file_type)}
                        <span className="truncate max-w-[150px] font-mono text-xs text-muted-foreground" title={ds.original_file_name}>
                          {ds.original_file_name}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="font-medium text-foreground">{ds.record_count?.toLocaleString() || 0} rows</div>
                      <div className="text-xs text-muted-foreground">{ds.column_count || 0} columns</div>
                    </td>
                    <td className="px-6 py-4 space-y-1.5">
                      <div className="flex flex-wrap gap-1">
                        <span
                          className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-semibold border ${
                            ds.upload_status === 'COMPLETED'
                              ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                              : 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'
                          }`}
                        >
                          Parsed: {ds.upload_status}
                        </span>
                        <span
                          className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-semibold border ${
                            ds.validation_status === 'PASSED'
                              ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                              : ds.validation_status === 'FAILED'
                              ? 'bg-red-500/10 text-red-500 border-red-500/20'
                              : 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'
                          }`}
                        >
                          Validation: {ds.validation_status}
                        </span>
                        <span
                          className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-semibold border ${
                            ds.profiling_status === 'COMPLETED'
                              ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                              : 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'
                          }`}
                        >
                          Profile: {ds.profiling_status}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-xs text-muted-foreground font-mono">
                      {new Date(ds.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => navigate(`/governance/datasets/${ds.id}`)}
                          className="inline-flex items-center gap-1.5 rounded border border-border px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-muted hover:text-foreground transition-colors"
                        >
                          <span>Analyze Details</span>
                          <ChevronRight className="h-3 w-3" />
                        </button>
                        <button
                          onClick={() => {
                            setSelectedDataset(ds);
                            setArchiveConfirmOpen(true);
                          }}
                          className="inline-flex items-center gap-1 rounded border border-destructive/20 text-destructive bg-destructive/5 p-1.5 text-xs font-semibold hover:bg-destructive hover:text-destructive-foreground transition-colors"
                          title="Archive Catalog"
                          aria-label="Archive Catalog"
                        >
                          <Archive className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {(datasetData?.items?.filter((ds: any) => !ds.archived_at).length === 0 || !datasetData?.items) && (
                  <tr>
                    <td colSpan={6} className="text-center py-12">
                      <div className="flex flex-col items-center justify-center space-y-3">
                        <div className="rounded-full bg-muted p-3">
                          <Database className="h-8 w-8 text-muted-foreground" />
                        </div>
                        <div className="font-semibold text-foreground">No Structured Datasets Uploaded</div>
                        <p className="text-xs text-muted-foreground max-w-sm">
                          Ingest files containing borrowing details or portfolio risk metrics to run mapping, quality validation, and analytics.
                        </p>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Reference Public Datasets Section */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-indigo-500" />
          <h3 className="text-lg font-semibold tracking-tight">Active Reference & Public Benchmarks</h3>
        </div>
        <p className="text-sm text-muted-foreground">
          Browse third-party catalogs and reference sources compiled inside RiskLens for validation rules & portfolio benchmarks.
        </p>

        {isSourcesLoading ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 animate-pulse">
            {[1, 2].map((i) => (
              <div key={i} className="h-32 rounded border border-border bg-card p-4 space-y-3">
                <div className="h-3 bg-muted rounded w-2/3"></div>
                <div className="h-3 bg-muted rounded w-1/2"></div>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {publicSources?.map((source: any) => (
              <div
                key={source.id}
                className="flex flex-col justify-between rounded-lg border border-border bg-card p-5 hover:border-indigo-500/40 hover:shadow-sm transition-all"
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="inline-flex rounded-full bg-indigo-500/10 px-2.5 py-0.5 text-2xs font-semibold text-indigo-500 dark:text-indigo-400 border border-indigo-500/20">
                      {source.dataset_category || 'Credit Risk'}
                    </span>
                    {source.provider && (
                      <span className="text-[10px] font-mono text-muted-foreground">
                        {source.provider}
                      </span>
                    )}
                  </div>
                  <h4 className="mt-3 font-semibold text-foreground text-base leading-snug">{source.name}</h4>
                  {source.recommended_use && (
                    <p className="mt-2 text-xs text-muted-foreground line-clamp-2" title={source.recommended_use}>
                      {source.recommended_use}
                    </p>
                  )}
                  {source.notes && (
                    <div className="mt-3 flex items-start gap-1.5 rounded bg-muted/50 p-2 text-[10px] text-muted-foreground leading-normal">
                      <Info className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      <span>{source.notes}</span>
                    </div>
                  )}
                </div>
                {source.source_url && (
                  <div className="mt-4 pt-3 border-t border-border/60">
                    <a
                      href={source.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
                    >
                      <span>Explore URL Link</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal: Upload Dataset */}
      {uploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md bg-card rounded-lg border border-border p-6 shadow-xl animate-scale-in">
            <h3 className="text-lg font-bold text-foreground">Upload Structured Dataset</h3>
            <p className="text-xs text-muted-foreground mt-1">
              Ingest a structured database file. Files will run schema validation checks upon ingestion.
            </p>

            <form onSubmit={handleUploadSubmit} className="mt-4 space-y-4">
              {uploadError && (
                <div className="rounded border border-destructive/20 bg-destructive/10 p-3 text-xs text-destructive flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>{uploadError}</span>
                </div>
              )}
              {successMsg && (
                <div className="rounded border border-emerald-500/20 bg-emerald-500/10 p-3 text-xs text-emerald-500">
                  {successMsg}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Dataset Display Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="mt-1 block w-full rounded border border-border bg-transparent px-3 py-2 text-sm text-foreground focus:border-primary focus:ring-1 focus:ring-primary"
                  placeholder="e.g. Portfolio Credit Q2 2026"
                  disabled={uploadMutation.isPending}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Description (Optional)
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  className="mt-1 block w-full rounded border border-border bg-transparent px-3 py-2 text-sm text-foreground focus:border-primary focus:ring-1 focus:ring-primary"
                  placeholder="Summarize rows metadata, dates bounds, or cohorts properties..."
                  disabled={uploadMutation.isPending}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                  Attach Structured File
                </label>
                <div className="flex items-center justify-center rounded-lg border-2 border-dashed border-border p-6 hover:bg-muted/10 transition-colors">
                  <div className="text-center space-y-1.5">
                    <Upload className="mx-auto h-8 w-8 text-muted-foreground" />
                    <div className="text-xs text-muted-foreground">
                      <label className="relative cursor-pointer rounded-md font-semibold text-primary focus-within:outline-hidden hover:underline">
                        <span>Upload a file</span>
                        <input
                          type="file"
                          accept=".csv,.xlsx,.json"
                          className="sr-only"
                          onChange={handleFileChange}
                          disabled={uploadMutation.isPending}
                        />
                      </label>
                      <span> or drag and drop</span>
                    </div>
                    <p className="text-[10px] text-muted-foreground">CSV, XLSX, or JSON formats up to 50MB</p>
                    {selectedFile && (
                      <p className="mt-2 text-xs font-medium text-emerald-500 truncate max-w-[280px]">
                        Selected: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                      </p>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-border">
                <button
                  type="button"
                  onClick={() => setUploadOpen(false)}
                  className="rounded border border-border px-4 py-2 text-xs font-semibold hover:bg-muted text-foreground"
                  disabled={uploadMutation.isPending}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploadMutation.isPending}
                  className="rounded bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/90 flex items-center gap-1.5"
                >
                  {uploadMutation.isPending ? 'Uploading...' : 'Ingest Catalog'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Confirm Archive */}
      {archiveConfirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
          <div className="w-full max-w-sm bg-card rounded-lg border border-border p-6 shadow-xl">
            <div className="flex items-center gap-3 text-destructive border-b border-border pb-3">
              <AlertTriangle className="h-6 w-6" />
              <h3 className="text-lg font-bold">Archive Catalog</h3>
            </div>
            <p className="text-sm mt-4 text-muted-foreground">
              Are you sure you want to archive <strong>{selectedDataset?.name}</strong>?
              This hides it from your primary structured catalog dashboards.
            </p>
            <div className="flex justify-end gap-2 pt-6 mt-6 border-t border-border">
              <button
                onClick={() => setArchiveConfirmOpen(false)}
                className="rounded border border-border px-4 py-2 text-xs font-semibold hover:bg-muted text-foreground"
              >
                Cancel
              </button>
              <button
                onClick={() => archiveMutation.mutate(selectedDataset.id)}
                disabled={archiveMutation.isPending}
                className="rounded bg-destructive px-4 py-2 text-xs font-semibold text-white hover:bg-destructive/90"
              >
                Confirm Archive
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default DatasetsPage;
