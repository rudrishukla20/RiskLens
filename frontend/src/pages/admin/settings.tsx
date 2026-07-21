import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { Settings, Save, CheckCircle2, AlertCircle, Sun, Moon, Monitor } from 'lucide-react';
import { useAuth } from '@/hooks/auth-context';

export const SettingsPage = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';
  const queryClient = useQueryClient();
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState<string>('');

  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>(
    () => (localStorage.getItem('theme') as 'light' | 'dark' | 'system') || 'light'
  );

  const handleThemeChange = (newTheme: 'light' | 'dark' | 'system') => {
    setTheme(newTheme);
    const root = window.document.documentElement;
    let activeTheme = newTheme;
    if (newTheme === 'system') {
      activeTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    if (activeTheme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('theme', newTheme);
  };

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
        <p className="text-sm text-muted-foreground">
          {isAdmin 
            ? "Adjust global platform operational variables, path directories, and security constants." 
            : "View global platform operational variables, path directories, and security constants."}
        </p>
      </div>

      {/* Theme Preferences Card */}
      <div className="rounded-lg border border-border bg-card p-6 shadow-sm space-y-4">
        <div>
          <h3 className="text-sm font-semibold tracking-tight text-primary dark:text-primary">Theme Preferences</h3>
          <p className="text-xs text-muted-foreground">Select your preferred interface display appearance.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          {/* Light Mode */}
          <button
            onClick={() => handleThemeChange('light')}
            className={`flex flex-col items-center justify-center p-4 rounded-lg border text-center transition-all hover:bg-muted/50 ${
              theme === 'light'
                ? 'border-primary bg-primary/5 text-primary'
                : 'border-border bg-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            <Sun className="h-5 w-5 mb-2" />
            <span className="text-xs font-semibold">Light Mode</span>
          </button>

          {/* Dark Mode */}
          <button
            onClick={() => handleThemeChange('dark')}
            className={`flex flex-col items-center justify-center p-4 rounded-lg border text-center transition-all hover:bg-muted/50 ${
              theme === 'dark'
                ? 'border-primary bg-primary/5 text-primary'
                : 'border-border bg-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            <Moon className="h-5 w-5 mb-2" />
            <span className="text-xs font-semibold">Dark Mode</span>
          </button>

          {/* System Default */}
          <button
            onClick={() => handleThemeChange('system')}
            className={`flex flex-col items-center justify-center p-4 rounded-lg border text-center transition-all hover:bg-muted/50 ${
              theme === 'system'
                ? 'border-primary bg-primary/5 text-primary'
                : 'border-border bg-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            <Monitor className="h-5 w-5 mb-2" />
            <span className="text-xs font-semibold">System Default</span>
          </button>
        </div>
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
                    {isAdmin && (
                      <button
                        onClick={() => handleStartEdit(setting.setting_key, setting.setting_value || '')}
                        className="rounded border border-border px-3 py-1.5 text-xs font-semibold hover:bg-muted"
                      >
                        Edit
                      </button>
                    )}
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
