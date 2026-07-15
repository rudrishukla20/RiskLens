import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import apiClient from '@/lib/api-client';
import { Plus, Edit2, ShieldAlert, Check, X, Shield } from 'lucide-react';

const userSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Invalid email address'),
  full_name: z.string().min(1, 'Full name is required'),
  password: z.string()
    .min(12, 'Password must be at least 12 characters')
    .refine((val) => /[A-Z]/.test(val), { message: 'Password must contain at least one uppercase letter' })
    .refine((val) => /[a-z]/.test(val), { message: 'Password must contain at least one lowercase letter' })
    .refine((val) => /\d/.test(val), { message: 'Password must contain at least one digit' })
    .refine((val) => /[!@#$%^&*()_\-+=\[\]{}|;:',.<>?/~`]/.test(val), {
      message: 'Password must contain at least one special character'
    }),
  role_code: z.enum(['ADMIN', 'CREDIT_RISK_GOVERNANCE_OFFICER']),
});

const userUpdateSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Invalid email address'),
  full_name: z.string().min(1, 'Full name is required'),
  password: z.string().optional().or(z.literal('')),
  role_code: z.enum(['ADMIN', 'CREDIT_RISK_GOVERNANCE_OFFICER']),
  status: z.enum(['ACTIVE', 'DEACTIVATED']),
}).refine(
  (data) => {
    if (!data.password) return true;
    return (
      data.password.length >= 12 &&
      /[A-Z]/.test(data.password) &&
      /[a-z]/.test(data.password) &&
      /\d/.test(data.password) &&
      /[!@#$%^&*()_\-+=\[\]{}|;:',.<>?/~`]/.test(data.password)
    );
  },
  {
    message: 'Password must be at least 12 characters, and include at least one uppercase letter, one lowercase letter, one number, and one special character.',
    path: ['password'],
  }
);

type UserFormValues = z.infer<typeof userSchema>;
type UserUpdateFormValues = z.infer<typeof userUpdateSchema>;

export const UserManagement = () => {
  const queryClient = useQueryClient();
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deactivateConfirmOpen, setDeactivateConfirmOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<any | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Fetch Users
  const { data, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const res = await apiClient.get('/users');
      return res.data;
    },
  });

  // Create User Mutation
  const createMutation = useMutation({
    mutationFn: async (values: UserFormValues) => {
      return await apiClient.post('/users', values);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setCreateModalOpen(false);
    },
    onError: (err: any) => {
      setErrorMsg(err.message || 'Failed to create user account.');
    },
  });

  // Update User Mutation
  const updateMutation = useMutation({
    mutationFn: async ({ id, values }: { id: string; values: UserUpdateFormValues }) => {
      const payload: any = { ...values };
      if (!payload.password) delete payload.password;
      return await apiClient.patch(`/users/${id}`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setEditModalOpen(false);
    },
    onError: (err: any) => {
      setErrorMsg(err.message || 'Failed to update user account details.');
    },
  });

  // Deactivate User Mutation
  const deactivateMutation = useMutation({
    mutationFn: async (id: string) => {
      return await apiClient.patch(`/users/${id}/deactivate`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setDeactivateConfirmOpen(false);
    },
    onError: (err: any) => {
      setErrorMsg(err.message || 'Failed to deactivate user.');
    },
  });

  // Forms hook setup
  const {
    register: registerCreate,
    handleSubmit: handleSubmitCreate,
    reset: resetCreate,
    formState: { errors: errorsCreate },
  } = useForm<UserFormValues>({
    resolver: zodResolver(userSchema),
  });

  const {
    register: registerEdit,
    handleSubmit: handleSubmitEdit,
    reset: resetEdit,
    formState: { errors: errorsEdit },
  } = useForm<UserUpdateFormValues>({
    resolver: zodResolver(userUpdateSchema),
  });

  const handleOpenEdit = (user: any) => {
    setSelectedUser(user);
    resetEdit({
      email: user.email,
      full_name: user.full_name,
      password: '',
      role_code: user.role,
      status: user.status,
    });
    setErrorMsg(null);
    setEditModalOpen(true);
  };

  const handleOpenDeactivate = (user: any) => {
    setSelectedUser(user);
    setErrorMsg(null);
    setDeactivateConfirmOpen(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight">User Account Provisioning</h2>
          <p className="text-sm text-muted-foreground">Manage identity access accounts and system roles.</p>
        </div>
        <button
          onClick={() => {
            resetCreate();
            setErrorMsg(null);
            setCreateModalOpen(true);
          }}
          className="flex items-center gap-2 rounded bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/95"
        >
          <Plus className="h-4 w-4" />
          <span>Create Account</span>
        </button>
      </div>

      {error && (
        <div className="rounded border border-destructive/20 bg-destructive/10 p-4 text-destructive">
          Failed to fetch registered platform accounts.
        </div>
      )}

      {/* Users Data Table */}
      {isLoading ? (
        <div className="flex h-32 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-card shadow-sm">
          <table className="w-full text-left border-collapse" aria-label="User Accounts">
            <thead>
              <tr className="border-b border-border bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                <th className="px-6 py-3">Full Name</th>
                <th className="px-6 py-3">Email Address</th>
                <th className="px-6 py-3">Assigned Role</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Last Logged In</th>
                <th className="px-6 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="text-sm divide-y divide-border">
              {data?.items?.map((user: any) => (
                <tr key={user.id} className="hover:bg-muted/10 transition-colors">
                  <td className="px-6 py-4 font-medium">{user.full_name}</td>
                  <td className="px-6 py-4 text-muted-foreground">{user.email}</td>
                  <td className="px-6 py-4">
                    <span className="inline-flex items-center gap-1 rounded bg-primary/5 px-2.5 py-0.5 text-xs font-semibold text-primary border border-primary/10">
                      <Shield className="h-3.5 w-3.5" />
                      {user.role?.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold border ${
                        user.status === 'ACTIVE'
                          ? 'bg-green-500/10 text-green-500 border-green-500/20'
                          : 'bg-red-500/10 text-red-500 border-red-500/20'
                      }`}
                    >
                      {user.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-muted-foreground text-xs">
                    {user.last_login_at ? new Date(user.last_login_at).toLocaleString() : 'Never'}
                  </td>
                  <td className="px-6 py-4 text-right space-x-2">
                    <button
                      onClick={() => handleOpenEdit(user)}
                      className="inline-flex items-center gap-1.5 rounded border border-border px-2.5 py-1 text-xs font-medium hover:bg-muted"
                    >
                      <Edit2 className="h-3 w-3" />
                      <span>Edit</span>
                    </button>
                    {user.status === 'ACTIVE' && (
                      <button
                        onClick={() => handleOpenDeactivate(user)}
                        className="inline-flex items-center gap-1.5 rounded border border-destructive/20 text-destructive bg-destructive/5 px-2.5 py-1 text-xs font-medium hover:bg-destructive hover:text-white"
                      >
                        <ShieldAlert className="h-3 w-3" />
                        <span>Deactivate</span>
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal: Create User */}
      {createModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md bg-card rounded-lg border border-border p-6 shadow-lg">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-lg font-bold">Create User Account</h3>
              <button onClick={() => setCreateModalOpen(false)} aria-label="Close modal">
                <X className="h-5 w-5 text-muted-foreground" />
              </button>
            </div>
            {errorMsg && <div className="mt-3 text-xs text-destructive bg-destructive/10 p-2 rounded">{errorMsg}</div>}
            <form onSubmit={handleSubmitCreate((values) => createMutation.mutate(values))} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-medium text-muted-foreground">Full Name</label>
                <input
                  type="text"
                  {...registerCreate('full_name')}
                  className="mt-1 block w-full rounded border border-border bg-transparent px-3 py-1.5 text-sm"
                />
                {errorsCreate.full_name && <p className="text-xs text-destructive mt-1">{errorsCreate.full_name.message}</p>}
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground">Email</label>
                <input
                  type="email"
                  {...registerCreate('email')}
                  className="mt-1 block w-full rounded border border-border bg-transparent px-3 py-1.5 text-sm"
                />
                {errorsCreate.email && <p className="text-xs text-destructive mt-1">{errorsCreate.email.message}</p>}
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground">Password</label>
                <input
                  type="password"
                  {...registerCreate('password')}
                  className="mt-1 block w-full rounded border border-border bg-transparent px-3 py-1.5 text-sm"
                />
                <p className="text-[10px] text-muted-foreground mt-1 leading-tight">Must be at least 12 characters, including one uppercase, one lowercase, one digit, and one special character.</p>
                {errorsCreate.password && <p className="text-xs text-destructive mt-1">{errorsCreate.password.message}</p>}
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground">Role</label>
                <select
                  {...registerCreate('role_code')}
                  className="mt-1 block w-full rounded border border-border bg-card px-3 py-1.5 text-sm"
                >
                  <option value="CREDIT_RISK_GOVERNANCE_OFFICER">Credit Risk Governance Officer</option>
                  <option value="ADMIN">System Administrator</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 border-t border-border pt-4 mt-6">
                <button
                  type="button"
                  onClick={() => setCreateModalOpen(false)}
                  className="rounded border border-border px-4 py-2 text-xs font-semibold hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="rounded bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/95"
                >
                  Save
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Edit User */}
      {editModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md bg-card rounded-lg border border-border p-6 shadow-lg">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-lg font-bold">Edit User Details</h3>
              <button onClick={() => setEditModalOpen(false)} aria-label="Close modal">
                <X className="h-5 w-5 text-muted-foreground" />
              </button>
            </div>
            {errorMsg && <div className="mt-3 text-xs text-destructive bg-destructive/10 p-2 rounded">{errorMsg}</div>}
            <form onSubmit={handleSubmitEdit((values) => updateMutation.mutate({ id: selectedUser.id, values }))} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-medium text-muted-foreground">Full Name</label>
                <input
                  type="text"
                  {...registerEdit('full_name')}
                  className="mt-1 block w-full rounded border border-border bg-transparent px-3 py-1.5 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground">Email</label>
                <input
                  type="email"
                  {...registerEdit('email')}
                  className="mt-1 block w-full rounded border border-border bg-transparent px-3 py-1.5 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground">Reset Password (Optional)</label>
                <input
                  type="password"
                  placeholder="Leave blank to keep current"
                  {...registerEdit('password')}
                  className="mt-1 block w-full rounded border border-border bg-transparent px-3 py-1.5 text-sm"
                />
                <p className="text-[10px] text-muted-foreground mt-1 leading-tight">If resetting, must be at least 12 characters, including one uppercase, one lowercase, one digit, and one special character.</p>
                {errorsEdit.password && <p className="text-xs text-destructive mt-1">{errorsEdit.password.message}</p>}
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground">Role</label>
                <select
                  {...registerEdit('role_code')}
                  className="mt-1 block w-full rounded border border-border bg-card px-3 py-1.5 text-sm"
                >
                  <option value="CREDIT_RISK_GOVERNANCE_OFFICER">Credit Risk Governance Officer</option>
                  <option value="ADMIN">System Administrator</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground">Status</label>
                <select
                  {...registerEdit('status')}
                  className="mt-1 block w-full rounded border border-border bg-card px-3 py-1.5 text-sm"
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="DEACTIVATED">DEACTIVATED</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 border-t border-border pt-4 mt-6">
                <button
                  type="button"
                  onClick={() => setEditModalOpen(false)}
                  className="rounded border border-border px-4 py-2 text-xs font-semibold hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateMutation.isPending}
                  className="rounded bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/95"
                >
                  Apply Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Deactivate Confirmation */}
      {deactivateConfirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-sm bg-card rounded-lg border border-border p-6 shadow-lg">
            <div className="flex items-center gap-3 text-destructive border-b border-border pb-3">
              <ShieldAlert className="h-6 w-6" />
              <h3 className="text-lg font-bold">Deactivate Account</h3>
            </div>
            <p className="text-sm mt-4 text-muted-foreground">
              Are you sure you want to deactivate <strong>{selectedUser?.full_name}</strong>? They will be signed out immediately and denied platform access.
            </p>
            <div className="flex justify-end gap-2 pt-6 mt-6 border-t border-border">
              <button
                onClick={() => setDeactivateConfirmOpen(false)}
                className="rounded border border-border px-4 py-2 text-xs font-semibold hover:bg-muted"
              >
                Cancel
              </button>
              <button
                onClick={() => deactivateMutation.mutate(selectedUser.id)}
                disabled={deactivateMutation.isPending}
                className="rounded bg-destructive px-4 py-2 text-xs font-semibold text-white hover:bg-destructive/90"
              >
                Deactivate
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default UserManagement;
