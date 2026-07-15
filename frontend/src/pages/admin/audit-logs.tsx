import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { ShieldAlert, ArrowLeft, ArrowRight, Search, Terminal } from 'lucide-react';

export const AuditLogs = () => {
  const [page, setPage] = useState(1);
  const [limit] = useState(25);
  const [actionFilter, setActionFilter] = useState('');
  const [moduleFilter, setModuleFilter] = useState('');

  const skip = (page - 1) * limit;

  // Fetch System-wide Audit Logs
  const { data, isLoading, error } = useQuery({
    queryKey: ['admin-audit-logs', page, actionFilter, moduleFilter],
    queryFn: async () => {
      const params: any = { skip, limit };
      const res = await apiClient.get('/admin/audit-logs', { params });
      return res.data;
    },
  });

  const logs = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold tracking-tight">System Audit Log Logs</h2>
        <p className="text-sm text-muted-foreground">Monitor platform events, database updates, and authentication audits.</p>
      </div>

      {error && (
        <div className="rounded border border-destructive/20 bg-destructive/10 p-4 text-destructive">
          Failed to load system audit logs.
        </div>
      )}

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-4 bg-card p-4 rounded-lg border border-border">
        <div className="flex items-center gap-2">
          <Search className="h-4 w-4 text-muted-foreground" />
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Filters</span>
        </div>
        
        {/* Action Filter */}
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            placeholder="Search action (e.g. LOGIN)..."
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              setPage(1);
            }}
            className="w-full rounded border border-border bg-transparent px-3 py-1.5 text-xs focus:border-ring focus:ring-ring"
          />
        </div>

        {/* Module Filter */}
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            placeholder="Search module (e.g. auth)..."
            value={moduleFilter}
            onChange={(e) => {
              setModuleFilter(e.target.value);
              setPage(1);
            }}
            className="w-full rounded border border-border bg-transparent px-3 py-1.5 text-xs focus:border-ring focus:ring-ring"
          />
        </div>
      </div>

      {/* Audit Logs Table */}
      {isLoading ? (
        <div className="flex h-32 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : (
        <div className="space-y-4">
          <div className="overflow-x-auto rounded-lg border border-border bg-card shadow-sm">
            <table className="w-full text-left border-collapse" aria-label="System Audit Logs">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  <th className="px-6 py-3">Timestamp</th>
                  <th className="px-6 py-3">Action</th>
                  <th className="px-6 py-3">User ID</th>
                  <th className="px-6 py-3">Module</th>
                  <th className="px-6 py-3">Resource Type</th>
                  <th className="px-6 py-3">Resource ID</th>
                  <th className="px-6 py-3">IP Address</th>
                  <th className="px-6 py-3">Details JSON</th>
                </tr>
              </thead>
              <tbody className="text-sm divide-y divide-border">
                {logs
                  .filter((log: any) => {
                    const matchAction = actionFilter ? log.action.toUpperCase().includes(actionFilter.toUpperCase()) : true;
                    const matchModule = moduleFilter ? log.module_name?.toUpperCase().includes(moduleFilter.toUpperCase()) : true;
                    return matchAction && matchModule;
                  })
                  .map((log: any) => (
                    <tr key={log.id} className="hover:bg-muted/10 transition-colors">
                      <td className="px-6 py-4 text-xs font-mono text-muted-foreground whitespace-nowrap">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4">
                        <span className="inline-flex rounded bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary dark:text-primary">
                          {log.action}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-xs font-mono text-muted-foreground">{log.user_id || 'System'}</td>
                      <td className="px-6 py-4 text-xs font-medium text-muted-foreground">{log.module_name || 'N/A'}</td>
                      <td className="px-6 py-4 text-xs">{log.resource_type || 'N/A'}</td>
                      <td className="px-6 py-4 text-xs font-mono text-muted-foreground">{log.resource_id || 'N/A'}</td>
                      <td className="px-6 py-4 text-xs text-muted-foreground">{log.ip_address || 'N/A'}</td>
                      <td className="px-6 py-4 max-w-[200px]">
                        <div className="flex items-center gap-1 text-xs text-muted-foreground bg-muted/30 p-1.5 rounded border border-border overflow-hidden truncate">
                          <Terminal className="h-3 w-3 shrink-0" />
                          <span className="font-mono text-[10px]">{JSON.stringify(log.details)}</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                {logs.length === 0 && (
                  <tr>
                    <td colSpan={8} className="text-center py-8 text-muted-foreground">
                      No audit events matching criteria found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-border pt-4">
              <span className="text-xs text-muted-foreground">
                Showing page {page} of {totalPages} ({total} entries total)
              </span>
              <div className="flex gap-2">
                <button
                  disabled={page === 1}
                  onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                  className="inline-flex items-center gap-1 rounded border border-border px-3 py-1.5 text-xs font-medium hover:bg-muted disabled:opacity-50"
                >
                  <ArrowLeft className="h-3 w-3" />
                  <span>Previous</span>
                </button>
                <button
                  disabled={page === totalPages}
                  onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                  className="inline-flex items-center gap-1 rounded border border-border px-3 py-1.5 text-xs font-medium hover:bg-muted disabled:opacity-50"
                >
                  <span>Next</span>
                  <ArrowRight className="h-3 w-3" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
export default AuditLogs;
