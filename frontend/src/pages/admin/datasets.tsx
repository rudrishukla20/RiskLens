import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { Database, Archive, AlertTriangle, FileSpreadsheet, FileJson, FileIcon, X } from 'lucide-react';

export const DatasetRegistry = () => {
  const queryClient = useQueryClient();
  const [archiveConfirmOpen, setArchiveConfirmOpen] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState<any | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Fetch Datasets Registry
  const { data, isLoading, error } = useQuery({
    queryKey: ['admin-datasets'],
    queryFn: async () => {
      const res = await apiClient.get('/admin/datasets');
      return res.data;
    },
  });

  // Archive Dataset Mutation
  const archiveMutation = useMutation({
    mutationFn: async (id: string) => {
      return await apiClient.delete(`/datasets/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-datasets'] });
      setArchiveConfirmOpen(false);
    },
    onError: (err: any) => {
      setErrorMsg(err.message || 'Failed to archive dataset.');
    },
  });

  const handleOpenArchive = (dataset: any) => {
    setSelectedDataset(dataset);
    setErrorMsg(null);
    setArchiveConfirmOpen(true);
  };

  const getFileIcon = (fileType: string) => {
    switch (fileType?.toUpperCase()) {
      case 'CSV':
      case 'XLSX':
        return <FileSpreadsheet className="h-5 w-5 text-green-600" />;
      case 'JSON':
        return <FileJson className="h-5 w-5 text-orange-600" />;
      default:
        return <FileIcon className="h-5 w-5 text-gray-500" />;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold tracking-tight">Structured Dataset Registry</h2>
        <p className="text-sm text-muted-foreground">Monitor and manage all uploaded structured catalogs in the platform.</p>
      </div>

      {error && (
        <div className="rounded border border-destructive/20 bg-destructive/10 p-4 text-destructive">
          Failed to load dataset registry.
        </div>
      )}

      {isLoading ? (
        <div className="flex h-32 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-card shadow-sm">
          <table className="w-full text-left border-collapse" aria-label="Dataset Registry">
            <thead>
              <tr className="border-b border-border bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                <th className="px-6 py-3">Dataset Name</th>
                <th className="px-6 py-3">File Name</th>
                <th className="px-6 py-3">Format</th>
                <th className="px-6 py-3">Records Count</th>
                <th className="px-6 py-3">Columns</th>
                <th className="px-6 py-3">Uploaded By</th>
                <th className="px-6 py-3">Archived Status</th>
                <th className="px-6 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="text-sm divide-y divide-border">
              {data?.items?.map((ds: any) => (
                <tr key={ds.id} className="hover:bg-muted/10 transition-colors">
                  <td className="px-6 py-4 font-semibold">{ds.name}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {getFileIcon(ds.file_type)}
                      <span className="truncate max-w-[150px] text-muted-foreground">{ds.original_file_name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 font-mono text-xs">{ds.file_type}</td>
                  <td className="px-6 py-4">{ds.record_count?.toLocaleString() || 0}</td>
                  <td className="px-6 py-4">{ds.column_count || 0}</td>
                  <td className="px-6 py-4 text-xs font-mono">{ds.uploaded_by}</td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex rounded px-2 py-0.5 text-xs font-medium border ${
                        ds.archived_at
                          ? 'bg-red-500/10 text-red-500 border-red-500/20'
                          : 'bg-green-500/10 text-green-500 border-green-500/20'
                      }`}
                    >
                      {ds.archived_at ? 'Archived' : 'Active'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    {!ds.archived_at && (
                      <button
                        onClick={() => handleOpenArchive(ds)}
                        className="inline-flex items-center gap-1.5 rounded border border-destructive/20 text-destructive bg-destructive/5 px-2.5 py-1.5 text-xs font-semibold hover:bg-destructive hover:text-white transition-colors"
                      >
                        <Archive className="h-3.5 w-3.5" />
                        <span>Archive</span>
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {data?.items?.length === 0 && (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-muted-foreground">
                    No datasets currently registered.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal: Confirm Archive */}
      {archiveConfirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-sm bg-card rounded-lg border border-border p-6 shadow-lg">
            <div className="flex items-center gap-3 text-destructive border-b border-border pb-3">
              <AlertTriangle className="h-6 w-6" />
              <h3 className="text-lg font-bold">Archive Dataset</h3>
            </div>
            {errorMsg && <div className="mt-3 text-xs text-destructive bg-destructive/10 p-2 rounded">{errorMsg}</div>}
            <p className="text-sm mt-4 text-muted-foreground">
              Are you sure you want to archive dataset <strong>{selectedDataset?.name}</strong>? This action will mark the dataset as archived, and prevent it from appearing in standard Credit Risk workspaces.
            </p>
            <div className="flex justify-end gap-2 pt-6 mt-6 border-t border-border">
              <button
                onClick={() => setArchiveConfirmOpen(false)}
                className="rounded border border-border px-4 py-2 text-xs font-semibold hover:bg-muted"
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
export default DatasetRegistry;
