import React from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { Users, Database, HardDrive, ShieldCheck, Activity } from 'lucide-react';

export const AdminDashboard = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['admin-dashboard'],
    queryFn: async () => {
      const res = await apiClient.get('/admin/dashboard');
      return res.data;
    },
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded border border-destructive/20 bg-destructive/10 p-4 text-destructive">
        Failed to load administrative overview dashboard metrics.
      </div>
    );
  }

  const metrics = data?.system_metrics;
  const logs = data?.recent_activity_logs || [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold tracking-tight">Administrative Overview</h2>
        <p className="text-sm text-muted-foreground">Monitor platform resources, user activity, and system status.</p>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Total Users */}
        <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-muted-foreground">Total Users</span>
            <Users className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold">{metrics?.total_users_count}</span>
            <p className="text-xs text-muted-foreground mt-1">Registered platform accounts</p>
          </div>
        </div>

        {/* Active Users */}
        <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-muted-foreground">Active Sessions</span>
            <Activity className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold">{metrics?.active_users_count}</span>
            <p className="text-xs text-muted-foreground mt-1">Currently enabled users</p>
          </div>
        </div>

        {/* Total Datasets */}
        <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-muted-foreground">Datasets Registry</span>
            <Database className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold">{metrics?.total_datasets_uploaded}</span>
            <p className="text-xs text-muted-foreground mt-1">Structured catalogs uploaded</p>
          </div>
        </div>

        {/* Storage Used */}
        <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-muted-foreground">Storage Consumed</span>
            <HardDrive className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold">
              {metrics?.storage_used_bytes !== undefined && metrics?.storage_used_bytes !== null
                ? `${(metrics.storage_used_bytes / (1024 * 1024)).toFixed(2)} MB`
                : 'N/A'}
            </span>
            <p className="text-xs text-muted-foreground mt-1">Temporary and structured storage</p>
          </div>
        </div>
      </div>

      {/* System Status & Activity Feed */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* System Load Status */}
        <div className="rounded-lg border border-border bg-card p-6 shadow-sm lg:col-span-1">
          <h3 className="text-sm font-semibold text-muted-foreground">System Health status</h3>
          <div className="mt-4 flex flex-col items-center justify-center p-6 border border-dashed border-border rounded-lg bg-muted/20">
            <ShieldCheck className="h-12 w-12 text-primary" />
            <span className="mt-3 text-lg font-bold uppercase text-primary tracking-wide">
              {metrics?.system_load_status || 'HEALTHY'}
            </span>
            <p className="mt-1 text-center text-xs text-muted-foreground">All backing services are operational</p>
          </div>
        </div>

        {/* Activity feed */}
        <div className="rounded-lg border border-border bg-card p-6 shadow-sm lg:col-span-2">
          <h3 className="text-sm font-semibold text-muted-foreground mb-4">Recent Audit Log Events</h3>
          <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2">
            {logs.length === 0 ? (
              <p className="text-sm text-muted-foreground">No recent system activities found.</p>
            ) : (
              logs.map((log: any) => (
                <div key={log.id} className="flex items-start justify-between border-b border-border pb-3 last:border-0 last:pb-0">
                  <div>
                    <span className="inline-block rounded bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary dark:text-primary mb-1">
                      {log.action.replace(/_/g, ' ')}
                    </span>
                    <p className="text-xs text-muted-foreground">User ID: {log.user_id || 'System'}</p>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {new Date(log.created_at).toLocaleString()}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
export default AdminDashboard;
