import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { DatasetSelector } from '@/components/dataset-selector';
import {
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  AreaChart,
  Area
} from 'recharts';
import {
  ShieldAlert,
  AlertTriangle,
  Database,
  BarChart3,
  CheckCircle,
  FileWarning
} from 'lucide-react';
import { EmptyState } from '@/components/empty-state';

const COLORS = ['#10b981', '#f59e0b', '#ef4444'];

export const Dashboard = () => {
  const [activeSubTab, setActiveSubTab] = useState<'portfolio' | 'quality'>('portfolio');
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');

  // 1. Fetch Global Portfolio Dashboard Data
  const { data: dashboard, isLoading: isDashLoading } = useQuery({
    queryKey: ['risk-dashboard'],
    queryFn: async () => {
      const res = await apiClient.get('/analytics/dashboard');
      return res.data;
    },
  });

  // 2. Fetch Data Quality Data (scoped to selected dataset)
  const { data: quality, isLoading: isQualityLoading } = useQuery({
    queryKey: ['data-quality', selectedDatasetId],
    queryFn: async () => {
      if (!selectedDatasetId) return null;
      const res = await apiClient.get('/analytics/data-quality', {
        params: { dataset_id: selectedDatasetId },
      });
      return res.data;
    },
    enabled: activeSubTab === 'quality' && !!selectedDatasetId,
  });

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val);
  };

  // Prepare Risk distribution pie data
  const dist = dashboard?.risk_distribution;
  const pieData = dist
    ? [
        { name: 'Low Risk', value: dist.low_risk_exposure, count: dist.low_risk_count },
        { name: 'Medium Risk', value: dist.medium_risk_exposure, count: dist.medium_risk_count },
        { name: 'High Risk', value: dist.high_risk_exposure, count: dist.high_risk_count },
      ]
    : [];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">Unified Credit Risk Dashboard</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Global portfolio indicators and data quality metrics for active risk monitoring.
          </p>
        </div>

        {/* Sub-tab selection */}
        <div className="flex border border-border bg-card p-1 rounded-md w-fit">
          <button
            onClick={() => setActiveSubTab('portfolio')}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded transition-colors ${
              activeSubTab === 'portfolio'
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-muted'
            }`}
          >
            <BarChart3 className="h-3.5 w-3.5" />
            <span>Portfolio Risk</span>
          </button>
          <button
            onClick={() => setActiveSubTab('quality')}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded transition-colors ${
              activeSubTab === 'quality'
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-muted'
            }`}
          >
            <Database className="h-3.5 w-3.5" />
            <span>Data Quality</span>
          </button>
        </div>
      </div>

      {/* PORTFOLIO TAB */}
      {activeSubTab === 'portfolio' && (
        <div className="space-y-6">
          {isDashLoading ? (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 animate-pulse">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-24 bg-card border border-border rounded-lg"></div>
              ))}
            </div>
          ) : (
            <>
              {/* KPI Cards Grid */}
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div className="rounded-lg border border-border bg-card p-5 shadow-2xs">
                  <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Total Portfolio Exposure</div>
                  <div className="mt-2 text-xl font-black text-foreground sm:text-2xl">
                    {formatCurrency(dashboard?.total_portfolio_exposure || 0)}
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-1">Outstanding aggregate principal sum</p>
                </div>
                <div className="rounded-lg border border-border bg-card p-5 shadow-2xs">
                  <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Weighted Avg Risk Score</div>
                  <div className="mt-2 text-xl font-black text-foreground sm:text-2xl">
                    {dashboard?.weighted_average_risk_score?.toFixed(1) || '0.0'}
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-1">Weighted by loan size exposure</p>
                </div>
                <div className="rounded-lg border border-border bg-card p-5 shadow-2xs">
                  <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Total Delinquency Exposure</div>
                  <div className="mt-2 text-xl font-black text-red-500 sm:text-2xl">
                    {formatCurrency(dashboard?.total_delinquency_exposure || 0)}
                  </div>
                  <p className="text-[10px] text-red-500/80 mt-1">Exposure in arrears &gt; 30 DPD</p>
                </div>
                <div className="rounded-lg border border-border bg-card p-5 shadow-2xs">
                  <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Delinquent Loans Count</div>
                  <div className="mt-2 text-xl font-black text-foreground sm:text-2xl">
                    {dashboard?.delinquent_loans_count?.toLocaleString() || 0}
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-1">Active loan contracts in default</p>
                </div>
              </div>

              {/* Charts grid */}
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                {/* Chart 1: Exposure distribution */}
                <div className="rounded-lg border border-border bg-card p-5 shadow-2xs">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground mb-4">Risk Category Exposure</h3>
                  <div className="h-64 flex items-center justify-center">
                    {pieData.length > 0 && pieData.some(d => d.value > 0) ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={pieData}
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={80}
                            paddingAngle={5}
                            dataKey="value"
                            nameKey="name"
                          >
                            {pieData.map((_entry, index) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip formatter={(value: any) => formatCurrency(value)} />
                          <Legend />
                        </PieChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="text-xs text-muted-foreground italic">No portfolio exposure records to display.</div>
                    )}
                  </div>
                </div>

                {/* Chart 2: Recent Risk trends */}
                <div className="rounded-lg border border-border bg-card p-5 shadow-2xs">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground mb-4">Recent Portfolio Risk Trends</h3>
                  <div className="h-64">
                    {dashboard?.recent_risk_trends && dashboard.recent_risk_trends.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={dashboard.recent_risk_trends}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                          <XAxis dataKey="period" stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                          <YAxis stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                          <Tooltip formatter={(value: any) => [typeof value === 'number' ? value.toFixed(2) : value, 'Risk Score']} />
                          <Line type="monotone" dataKey="average_risk_score" stroke="#6366f1" strokeWidth={3} dot={{ r: 4 }} />
                        </LineChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="flex h-full items-center justify-center text-xs text-muted-foreground italic">
                        No historical risk trends found.
                      </div>
                    )}
                  </div>
                </div>

                {/* Chart 3: Sector concentrations */}
                <div className="rounded-lg border border-border bg-card p-5 shadow-2xs lg:col-span-2">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground mb-4">Sector Exposure Concentration</h3>
                  <div className="overflow-x-auto rounded border border-border">
                    <table className="w-full text-left border-collapse" aria-label="Sector Exposure Concentration Table">
                      <thead>
                        <tr className="border-b border-border bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                          <th className="px-6 py-2.5">Sector (Loan Purpose)</th>
                          <th className="px-6 py-2.5">Total Loans Count</th>
                          <th className="px-6 py-2.5">Outstanding Principal</th>
                          <th className="px-6 py-2.5">Avg Risk Score</th>
                          <th className="px-6 py-2.5">Share %</th>
                        </tr>
                      </thead>
                      <tbody className="text-sm divide-y divide-border">
                        {dashboard?.sector_concentration?.map((sec: any, idx: number) => {
                          const pct = ((sec.exposure_amount / (dashboard.total_portfolio_exposure || 1)) * 100).toFixed(1);
                          return (
                            <tr key={idx} className="hover:bg-muted/10">
                              <td className="px-6 py-3 font-semibold text-foreground">{sec.sector || 'Unassigned'}</td>
                              <td className="px-6 py-3">{sec.loans_count?.toLocaleString()}</td>
                              <td className="px-6 py-3 font-mono text-xs">{formatCurrency(sec.exposure_amount || 0)}</td>
                              <td className="px-6 py-3">{sec.average_risk_score?.toFixed(1) || '0.0'}</td>
                              <td className="px-6 py-3 font-semibold">
                                <div className="flex items-center gap-2">
                                  <span>{pct}%</span>
                                  <div className="w-20 bg-muted rounded-full h-1.5 hidden sm:block">
                                    <div className="bg-primary h-1.5 rounded-full" style={{ width: `${pct}%` }}></div>
                                  </div>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                        {(!dashboard?.sector_concentration || dashboard.sector_concentration.length === 0) && (
                          <tr>
                            <td colSpan={5} className="text-center py-6 text-muted-foreground text-xs italic">
                              No sector metrics compiled.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* DATA QUALITY TAB */}
      {activeSubTab === 'quality' && (
        <div className="space-y-6">
          {/* Dataset Selector header */}
          <div className="flex flex-wrap items-center justify-between gap-4 bg-muted/20 border border-border p-4 rounded-lg">
            <div className="space-y-0.5">
              <h3 className="font-bold text-sm">Select Target Dataset to Analyze Data Quality Scorecard</h3>
              <p className="text-2xs text-muted-foreground">Quality score checks are run against the selected structured database version.</p>
            </div>
            <DatasetSelector selectedId={selectedDatasetId} onSelect={setSelectedDatasetId} />
          </div>

          {!selectedDatasetId ? (
            <EmptyState
              title="No Dataset Selected"
              description="Choose an active ingested structured catalog from the dropdown selector above to see quality scorecards."
              icon={Database}
              variant="solid"
            />
          ) : isQualityLoading ? (
            <div className="space-y-6 animate-pulse">
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="h-20 bg-card border border-border rounded"></div>
                ))}
              </div>
              <div className="h-48 bg-card border border-border rounded"></div>
            </div>
          ) : quality ? (
            <>
              {/* Quality scores scorecard */}
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
                <div className="rounded-lg border border-border bg-card p-4 text-center">
                  <div className="text-3xs uppercase font-bold text-muted-foreground tracking-wider">Overall Quality</div>
                  <div className="mt-1 text-2xl font-black text-foreground">
                    {quality.dataset_health_score !== undefined && quality.dataset_health_score !== null ? `${quality.dataset_health_score}%` : 'N/A'}
                  </div>
                  <div className="mt-1 flex items-center justify-center gap-1 text-2xs text-emerald-500">
                    <CheckCircle className="h-3 w-3" />
                    <span>Scorecard Health</span>
                  </div>
                </div>
                <div className="rounded-lg border border-border bg-card p-4 text-center">
                  <div className="text-3xs uppercase font-semibold text-muted-foreground">Completeness</div>
                  <div className="mt-1 text-xl font-bold text-foreground">
                    {quality.completeness_score !== undefined && quality.completeness_score !== null ? `${quality.completeness_score}%` : 'N/A'}
                  </div>
                  <p className="text-3xs text-muted-foreground mt-0.5">Missing Null density</p>
                </div>
                <div className="rounded-lg border border-border bg-card p-4 text-center">
                  <div className="text-3xs uppercase font-semibold text-muted-foreground">Uniqueness</div>
                  <div className="mt-1 text-xl font-bold text-foreground">
                    {quality.uniqueness_score !== undefined && quality.uniqueness_score !== null ? `${quality.uniqueness_score}%` : 'N/A'}
                  </div>
                  <p className="text-3xs text-muted-foreground mt-0.5">Duplicate records count</p>
                </div>
                <div className="rounded-lg border border-border bg-card p-4 text-center">
                  <div className="text-3xs uppercase font-semibold text-muted-foreground">Validity</div>
                  <div className="mt-1 text-xl font-bold text-foreground">
                    {quality.validity_score !== undefined && quality.validity_score !== null ? `${quality.validity_score}%` : 'N/A'}
                  </div>
                  <p className="text-3xs text-muted-foreground mt-0.5">Types mapping checks</p>
                </div>
                <div className="rounded-lg border border-border bg-card p-4 text-center">
                  <div className="text-3xs uppercase font-semibold text-muted-foreground">Consistency</div>
                  <div className="mt-1 text-xl font-bold text-foreground">
                    {quality.consistency_score !== undefined && quality.consistency_score !== null ? `${quality.consistency_score}%` : 'N/A'}
                  </div>
                  <p className="text-3xs text-muted-foreground mt-0.5">Business rules checks</p>
                </div>
              </div>

              {/* Quality Anomalies & Issue count breakdown */}
              <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
                <div className="bg-card border border-border p-4 rounded-lg flex items-center gap-3">
                  <div className="bg-red-500/10 text-red-500 border border-red-500/20 p-2.5 rounded-lg">
                    <FileWarning className="h-6 w-6" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-muted-foreground">Invalid Types Counts</div>
                    <div className="text-lg font-bold text-foreground mt-0.5">{quality.invalid_datatype_count?.toLocaleString() || 0}</div>
                  </div>
                </div>
                <div className="bg-card border border-border p-4 rounded-lg flex items-center gap-3">
                  <div className="bg-yellow-500/10 text-yellow-500 border border-yellow-500/20 p-2.5 rounded-lg">
                    <AlertTriangle className="h-6 w-6" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-muted-foreground">Missing Values Percentage</div>
                    <div className="text-lg font-bold text-foreground mt-0.5">{quality.missing_value_percentage?.toFixed(2) || '0.0'}%</div>
                  </div>
                </div>
                <div className="bg-card border border-border p-4 rounded-lg flex items-center gap-3">
                  <div className="bg-indigo-500/10 text-indigo-500 border border-indigo-500/20 p-2.5 rounded-lg">
                    <ShieldAlert className="h-6 w-6" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-muted-foreground">Rule Violation Count</div>
                    <div className="text-lg font-bold text-foreground mt-0.5">{quality.invalid_business_rule_count?.toLocaleString() || 0}</div>
                  </div>
                </div>
              </div>

              {/* Data quality timeline / history line chart */}
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                <div className="rounded-lg border border-border bg-card p-5 lg:col-span-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Historical Data Health Scorecard Timeline</h3>
                  <div className="h-60">
                    {quality.validation_trend_by_dataset_version && quality.validation_trend_by_dataset_version.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={quality.validation_trend_by_dataset_version}>
                          <defs>
                            <linearGradient id="colorHealth" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/>
                              <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                          <XAxis dataKey="version_label" stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                          <YAxis stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} domain={[50, 100]} />
                          <Tooltip />
                          <Area type="monotone" dataKey="score" stroke="#10b981" fillOpacity={1} fill="url(#colorHealth)" strokeWidth={2.5} />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="flex h-full items-center justify-center text-xs text-muted-foreground italic border border-dashed border-border rounded bg-muted/5">
                        No version history trend found. Run validation to log version metrics.
                      </div>
                    )}
                  </div>
                </div>

                {/* Scorecard checklist details */}
                <div className="rounded-lg border border-border bg-card p-5">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Quality Verification Checklist</h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between border-b border-border/60 pb-2">
                      <div className="text-xs font-semibold">Column mapping configured</div>
                      <span className="text-2xs bg-emerald-500/10 text-emerald-500 rounded px-1.5 py-0.5 font-bold uppercase border border-emerald-500/20">PASSED</span>
                    </div>
                    <div className="flex items-center justify-between border-b border-border/60 pb-2">
                      <div className="text-xs font-semibold">Missing values density check</div>
                      <span className={`text-2xs rounded px-1.5 py-0.5 font-bold uppercase border ${
                        (quality.missing_value_percentage || 0) < 5
                          ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                          : 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'
                      }`}>{ (quality.missing_value_percentage || 0) < 5 ? 'OPTIMAL' : 'WARNING' }</span>
                    </div>
                    <div className="flex items-center justify-between border-b border-border/60 pb-2">
                      <div className="text-xs font-semibold">Duplicate records ratio</div>
                      <span className="text-2xs bg-emerald-500/10 text-emerald-500 rounded px-1.5 py-0.5 font-bold uppercase border border-emerald-500/20">HEALTHY</span>
                    </div>
                    <div className="flex items-center justify-between border-b border-border/60 pb-2">
                      <div className="text-xs font-semibold">Schema drift detection</div>
                      <span 
                        className="text-2xs text-muted-foreground font-mono truncate max-w-[120px]" 
                        title={
                          typeof quality.schema_drift_indicator === 'object' 
                            ? JSON.stringify(quality.schema_drift_indicator) 
                            : String(quality.schema_drift_indicator || '')
                        }
                      >
                        {typeof quality.schema_drift_indicator === 'object'
                          ? (quality.schema_drift_indicator.drift_detected ? 'DRIFT DETECTED' : 'NO DRIFT')
                          : (quality.schema_drift_indicator || 'No Drift Detected')}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <EmptyState
              title="Failed to Load Scorecard"
              description="Run validation in catalogs workspace first."
              icon={AlertTriangle}
              variant="solid"
            />
          )}
        </div>
      )}
    </div>
  );
};
export default Dashboard;
