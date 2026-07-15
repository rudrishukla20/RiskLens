
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from '@/hooks/auth-context';
import { ProtectedRoute, RoleGuard, GuestRoute } from '@/components/route-guards';
import { LayoutShell, NavItem } from '@/components/layout-shell';
import { Login } from '@/pages/login';

// Admin Page Imports
import { AdminDashboard } from '@/pages/admin/dashboard';
import { UserManagement } from '@/pages/admin/users';
import { DatasetRegistry } from '@/pages/admin/datasets';
import { ReportRegistry } from '@/pages/admin/reports';
import { AuditLogs } from '@/pages/admin/audit-logs';
import { SettingsPage } from '@/pages/admin/settings';

// Governance Page Imports
import { DatasetsPage } from '@/pages/governance/datasets';
import { DocumentsPage } from '@/pages/governance/documents';
import { DatasetDetails } from '@/pages/governance/dataset-details';
import { Dashboard } from '@/pages/governance/dashboard';
import { BorrowerRisk } from '@/pages/governance/borrowers';
import { LoanExposure } from '@/pages/governance/loans';
import { PortfolioAnalytics } from '@/pages/governance/portfolio';
import { ConcentrationAnalysis } from '@/pages/governance/concentration';
import { TrendAnalysis } from '@/pages/governance/trends';
import { DiagnosticAnalytics } from '@/pages/governance/diagnostics';
import { AIInsightsPage } from '@/pages/governance/ai-insights';
import { ReportsPage } from '@/pages/governance/reports';

import {
  Users,
  BarChart3,
  Settings,
  ShieldAlert,
  Database,
  FileText,
  BrainCircuit,
  FileSpreadsheet,
  Activity,
  Layers,
  Compass,
  TrendingUp
} from 'lucide-react';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// Sidebar navigation structures
const adminNavItems: NavItem[] = [
  { label: 'System Overview', to: '/admin/dashboard', icon: BarChart3 },
  { label: 'User Provisioning', to: '/admin/users', icon: Users },
  { label: 'Dataset Registry', to: '/admin/datasets', icon: Database },
  { label: 'Report Registry', to: '/admin/reports', icon: FileSpreadsheet },
  { label: 'System Audit Logs', to: '/admin/audit-logs', icon: ShieldAlert },
  { label: 'System Settings', to: '/admin/settings', icon: Settings },
];

const governanceNavItems: NavItem[] = [
  { label: 'Risk Dashboard', to: '/governance/dashboard', icon: BarChart3 },
  { label: 'Data Catalogs', to: '/governance/datasets', icon: Database },
  { label: 'Borrower Risk', to: '/governance/borrowers', icon: Users },
  { label: 'Loan Exposure', to: '/governance/loans', icon: Activity },
  { label: 'Portfolio Analytics', to: '/governance/portfolio', icon: Layers },
  { label: 'Concentration', to: '/governance/concentration', icon: Compass },
  { label: 'Trend Analysis', to: '/governance/trends', icon: TrendingUp },
  { label: 'Diagnostics', to: '/governance/diagnostics', icon: ShieldAlert },
  { label: 'Compliance Docs', to: '/governance/documents', icon: FileText },
  { label: 'AI Commentary', to: '/governance/ai-insights', icon: BrainCircuit },
  { label: 'Export Reports', to: '/governance/reports', icon: FileSpreadsheet },
];

const DefaultRedirect = () => {
  const { user } = useAuth();
  if (user) {
    return <Navigate to={user.role === 'ADMIN' ? '/admin/dashboard' : '/governance/dashboard'} replace />;
  }
  return <Navigate to="/login" replace />;
};

export const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public guest routes (unauthenticated) */}
            <Route element={<GuestRoute />}>
              <Route path="/login" element={<Login />} />
            </Route>

            {/* Protected authenticated routes */}
            <Route element={<ProtectedRoute />}>
              {/* Admin Workspace */}
              <Route element={<RoleGuard allowedRoles={['ADMIN']} />}>
                <Route element={<LayoutShell navItems={adminNavItems} />}>
                  <Route path="/admin/dashboard" element={<AdminDashboard />} />
                  <Route path="/admin/users" element={<UserManagement />} />
                  <Route path="/admin/datasets" element={<DatasetRegistry />} />
                  <Route path="/admin/reports" element={<ReportRegistry />} />
                  <Route path="/admin/audit-logs" element={<AuditLogs />} />
                  <Route path="/admin/settings" element={<SettingsPage />} />
                </Route>
              </Route>

              {/* Credit Risk Governance Officer Workspace */}
              <Route element={<RoleGuard allowedRoles={['CREDIT_RISK_GOVERNANCE_OFFICER']} />}>
                <Route element={<LayoutShell navItems={governanceNavItems} />}>
                  <Route path="/governance/dashboard" element={<Dashboard />} />
                  <Route path="/governance/datasets" element={<DatasetsPage />} />
                  <Route path="/governance/datasets/:id" element={<DatasetDetails />} />
                  <Route path="/governance/borrowers" element={<BorrowerRisk />} />
                  <Route path="/governance/loans" element={<LoanExposure />} />
                  <Route path="/governance/portfolio" element={<PortfolioAnalytics />} />
                  <Route path="/governance/concentration" element={<ConcentrationAnalysis />} />
                  <Route path="/governance/trends" element={<TrendAnalysis />} />
                  <Route path="/governance/diagnostics" element={<DiagnosticAnalytics />} />
                  <Route path="/governance/documents" element={<DocumentsPage />} />
                  <Route path="/governance/ai-insights" element={<AIInsightsPage />} />
                  <Route path="/governance/reports" element={<ReportsPage />} />
                </Route>
              </Route>

              {/* Default fallback route */}
              <Route path="/" element={<DefaultRedirect />} />
            </Route>

            {/* Catch-all redirects */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};
export default App;
