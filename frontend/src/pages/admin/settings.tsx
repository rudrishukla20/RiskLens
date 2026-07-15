import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { Settings, Save, CheckCircle2, AlertCircle } from 'lucide-react';

export const SettingsPage = () => {
  const queryClient = useQueryClient();
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState<string>('');

  // Fetch System Settings
  const { data: settingsList, isLoading, error } = useQuery({
    queryKey: ['admin-settings'],
    queryFn: async () => {
      const res = await apiClient.get('/admin/settings');
      return res.data;
    },
  });

  // Update Setting Mutation
  const updateMutation = useMutation({
    mutationFn: async ({ key, value }: { key: string; value: string }) => {
      return await apiClient.patch(`/admin/settings/${key}`, { setting_value: value });
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['admin-settings'] });
      setEditingKey(null);
      setSuccessMsg(`Setting '${variables.key}' updated successfully.`);
      setTimeout(() => setSuccessMsg(null), 3000);
    },
    onError: (err: any) => {
      setErrorMsg(err.message || 'Failed to update setting.');
      setTimeout(() => setErrorMsg(null), 4000);
    },
  });

  const handleStartEdit = (key: string, currentValue: string) => {
    setEditingKey(key);
    setEditingValue(currentValue);
    setSuccessMsg(null);
    setErrorMsg(null);
  };

  const handleSave = (key: string) => {
    updateMutation.mutate({ key, value: editingValue });
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-xl font-bold tracking-tight">System Settings Configuration</h2>
        <p className="text-sm text-muted-foreground">Adjust global platform operational variables, path directories, and security constants.</p>
      </div>

      {successMsg && (
        <div className="flex items-center gap-2 rounded bg-green-500/10 border border-green-500/20 p-3 text-sm text-green-500" role="alert">
          <CheckCircle2 className="h-5 w-5 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="flex items-center gap-2 rounded bg-destructive/10 border border-destructive/20 p-3 text-sm text-destructive" role="alert">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {error && (
        <div className="rounded border border-destructive/20 bg-destructive/10 p-4 text-destructive">
          Failed to retrieve platform configurations.
        </div>
      )}

      {isLoading ? (
        <div className="flex h-32 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : (
        <div className="space-y-4">
          {settingsList?.map((setting: any) => (
            <div key={setting.id} className="rounded-lg border border-border bg-card p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1 max-w-lg">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm tracking-wide font-mono text-primary dark:text-primary">
                    {setting.setting_key}
                  </span>
                  <span className="inline-block rounded bg-muted px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground border">
                    {setting.setting_type}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">{setting.description || 'No description provided.'}</p>
              </div>

              {/* Edit panel */}
              <div className="flex items-center gap-3 w-full md:w-auto">
                {editingKey === setting.setting_key ? (
                  <div className="flex items-center gap-2 w-full md:w-auto">
                    <input
                      type="text"
                      value={editingValue}
                      onChange={(e) => setEditingValue(e.target.value)}
                      className="rounded border border-border bg-transparent px-3 py-1 text-sm w-full md:w-60 focus:border-ring focus:ring-ring"
                    />
                    <button
                      onClick={() => handleSave(setting.setting_key)}
                      disabled={updateMutation.isPending}
                      className="inline-flex items-center justify-center p-1.5 rounded bg-primary text-primary-foreground hover:bg-primary/95 disabled:opacity-50"
                      aria-label="Save changes"
                    >
                      <Save className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => setEditingKey(null)}
                      className="rounded border border-border px-2.5 py-1 text-xs font-semibold hover:bg-muted"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-4 w-full justify-between md:justify-end">
                    <span className="font-mono text-sm bg-muted/30 px-3 py-1 rounded border border-border">
                      {setting.setting_value ?? 'NULL'}
                    </span>
                    <button
                      onClick={() => handleStartEdit(setting.setting_key, setting.setting_value || '')}
                      className="rounded border border-border px-3 py-1.5 text-xs font-semibold hover:bg-muted"
                    >
                      Edit
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
export default SettingsPage;
