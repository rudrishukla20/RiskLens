import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { DatasetSelector } from '@/components/dataset-selector';
import { formatCurrencyINR, formatLabel } from '@/lib/formatter';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar
} from 'recharts';
import {
  ShieldAlert,
  AlertTriangle,
  History,
  ArrowRightLeft
} from 'lucide-react';
import { EmptyState } from '@/components/empty-state';

export const DiagnosticAnalytics = () => {
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>(() => {
    return localStorage.getItem('selected_dataset_id') || '';
  });

  const [activeSubTab, setActiveSubTab] = useState<'rootcause' | 'vintage' | 'migration'>('rootcause');

  // 1. Fetch Diagnostics Metrics
  const { data: diagnostics, isLoading: isDiagLoading } = useQuery({
    queryKey: ['diagnostics-analytics', selectedDatasetId],
    queryFn: async () => {
      if (!selectedDatasetId) return null;
      const res = await apiClient.get('/analytics/diagnostics', {
        params: { dataset_id: selectedDatasetId },
      });
      return res.data;
    },
    enabled: !!selectedDatasetId,
  });

  // 2. Fetch Vintage/Cohort Metrics
  const { data: vintage, isLoading: isVintageLoading } = useQuery({
    queryKey: ['vintage-analytics', selectedDatasetId],
    queryFn: async () => {
      if (!selectedDatasetId) return null;
      const res = await apiClient.get('/analytics/vintage', {
        params: { dataset_id: selectedDatasetId },
      });
      return res.data;
    },
    enabled: !!selectedDatasetId && activeSubTab === 'vintage',
  });

  // 3. Fetch Migration Metrics
  const { data: migration, isLoading: isMigrateLoading } = useQuery({
    queryKey: ['migration-analytics', selectedDatasetId],
    queryFn: async () => {
      if (!selectedDatasetId) return null;
      const res = await apiClient.get('/analytics/migration', {
        params: { dataset_id: selectedDatasetId },
      });
      return res.data;
    },
    enabled: !!selectedDatasetId && activeSubTab === 'migration',
  });

  const handleDatasetChange = (id: string) => {
    setSelectedDatasetId(id);
  };



  if (!selectedDatasetId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <h2 className="text-2xl font-bold tracking-tight">Diagnostic & Advanced Analytics</h2>
          <DatasetSelector selectedId={selectedDatasetId} onSelect={handleDatasetChange} />
        </div>
        <EmptyState
          title="No Structured Dataset Selected"
          description="Choose an active credit portfolio catalog from the selector at the top right to start diagnostic calculations."
          icon={ShieldAlert}
          variant="dashed"
        />
      </div>
    );
  }

  const isDiagUnavailable = diagnostics?.visualizations?.driver_waterfall?.length === 0;
  const isVintageUnavailable = vintage?.status === 'unavailable' || !vintage?.visualizations || vintage?.visualizations?.vintage_trend_table?.length === 0;
  const isMigrationUnavailable = migration?.status === 'unavailable' || !migration?.visualizations || !migration.visualizations?.migration_matrix;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Diagnostic & Cohort Analytics</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Identify driver contribution waterfalls, variables correlations, vintage cohorts, and risk migration curves.
          </p>
        </div>
        <DatasetSelector selectedId={selectedDatasetId} onSelect={handleDatasetChange} />
      </div>

      {/* Tab select bar */}
      <div className="flex border border-border bg-card p-1 rounded-md w-fit">
        <button
          onClick={() => setActiveSubTab('rootcause')}
          className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded transition-colors ${
            activeSubTab === 'rootcause'
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-muted'
          }`}
        >
          <ShieldAlert className="h-3.5 w-3.5" />
          <span>Root Cause & Drivers</span>
        </button>
        <button
          onClick={() => setActiveSubTab('vintage')}
          className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded transition-colors ${
            activeSubTab === 'vintage'
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-muted'
          }`}
        >
          <History className="h-3.5 w-3.5" />
          <span>Vintage Cohorts</span>
        </button>
        <button
          onClick={() => setActiveSubTab('migration')}
          className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded transition-colors ${
            activeSubTab === 'migration'
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-muted'
          }`}
        >
          <ArrowRightLeft className="h-3.5 w-3.5" />
          <span>Risk Migration</span>
        </button>
      </div>

      {/* SUB TAB 1: DIAGNOSTIC & ROOT CAUSE */}
      {activeSubTab === 'rootcause' && (
        <div className="space-y-6">
          {isDiagLoading ? (
            <div className="flex h-64 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          ) : isDiagUnavailable ? (
            <EmptyState
              title="Diagnostic Data Unavailable"
              description="Run risk assessments on the dataset version to generate root cause breakdowns."
              icon={AlertTriangle}
              variant="solid"
            />
          ) : (
            <div className="space-y-6">
              
              {/* Summary text */}
              <div className="rounded-lg border border-border bg-card p-5">
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">Automated Risk Driver Commentary</h3>
                <p className="text-sm text-foreground leading-relaxed">{diagnostics.root_cause_summary}</p>
              </div>

              {/* Waterfall & bubble chart */}
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                
                {/* Waterfall */}
                <div className="bg-card border border-border p-5 rounded-lg">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Adverse Factors Risk Contribution Waterfall</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={diagnostics.visualizations.driver_waterfall}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                        <XAxis dataKey="driver" stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                        <YAxis stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                        <Tooltip formatter={(value: any) => [`+${value}%`, 'Avg Contribution']} />
                        <Bar dataKey="avg_contribution" fill="#ef4444" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Bubble Chart: Exposure vs Risk vs Loans count */}
                <div className="bg-card border border-border p-5 rounded-lg">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Segment Risk Exposure Bubble Map</h3>
                  <div className="h-64">
                    {diagnostics.visualizations.bubble_chart && diagnostics.visualizations.bubble_chart.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                          <CartesianGrid stroke="rgba(255,255,255,0.05)" />
                          <XAxis type="number" dataKey="x_exposure" name="Outstanding Exposure" unit="₹" stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                          <YAxis type="number" dataKey="y_risk" name="Avg Risk Score" domain={[0, 100]} stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                          <ZAxis type="number" dataKey="size_loans" range={[40, 400]} name="Loans Count" />
                          <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                          <Scatter name="Segments" data={diagnostics.visualizations.bubble_chart} fill="#8b5cf6" />
                        </ScatterChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="text-xs text-muted-foreground italic text-center py-20">Bubble data unavailable.</div>
                    )}
                  </div>
                </div>

                {/* Correlation Matrix */}
                <div className="bg-card border border-border p-5 rounded-lg lg:col-span-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Variables Correlation Matrix</h3>
                  <div className="overflow-x-auto rounded border border-border">
                    <table className="w-full text-left border-collapse" aria-label="Correlation Matrix Table">
                      <thead>
                        <tr className="border-b border-border bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                          <th className="px-6 py-2">Variable</th>
                          {diagnostics.correlation_analysis?.variables?.map((v: string) => (
                            <th key={v} className="px-6 py-2 text-center">{v}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="text-sm divide-y divide-border font-mono text-xs">
                        {diagnostics.correlation_analysis?.matrix?.map((row: number[], rIdx: number) => {
                          const vName = diagnostics.correlation_analysis.variables[rIdx];
                          return (
                            <tr key={vName} className="hover:bg-muted/10">
                              <td className="px-6 py-2.5 font-semibold text-foreground bg-muted/20">{vName}</td>
                              {row.map((val: number, cIdx: number) => {
                                const colorWeight = Math.abs(val);
                                return (
                                  <td
                                    key={cIdx}
                                    style={{
                                      backgroundColor: val > 0 ? `rgba(16, 185, 129, ${colorWeight * 0.25})` : `rgba(239, 68, 68, ${colorWeight * 0.25})`,
                                    }}
                                    className="px-6 py-2.5 text-center font-bold"
                                  >
                                    {val.toFixed(2)}
                                  </td>
                                );
                              })}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Drill through Borrower Segment list */}
                <div className="bg-card border border-border p-5 rounded-lg lg:col-span-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Detailed Segment Risk Comparative Profiles</h3>
                  <div className="overflow-x-auto rounded border border-border">
                    <table className="w-full text-left border-collapse" aria-label="Comparative Profiles Table">
                      <thead>
                        <tr className="border-b border-border bg-muted/30 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                          <th className="px-6 py-2.5">Segment Type</th>
                          <th className="px-6 py-2.5">Segment Value</th>
                          <th className="px-6 py-2.5">Loans Count</th>
                          <th className="px-6 py-2.5 font-mono text-right">Exposure</th>
                          <th className="px-6 py-2.5 text-right">Avg Risk Score</th>
                          <th className="px-6 py-2.5 text-right">High-Risk Count</th>
                        </tr>
                      </thead>
                      <tbody className="text-sm divide-y divide-border">
                        {diagnostics.visualizations.segment_comparison_table?.map((row: any, idx: number) => (
                          <tr key={idx} className="hover:bg-muted/10">
                            <td className="px-6 py-3 font-mono text-2xs text-muted-foreground uppercase">{row.segment_type}</td>
                            <td className="px-6 py-3 font-semibold text-foreground">{row.segment_value}</td>
                            <td className="px-6 py-3">{row.loans_count}</td>
                            <td className="px-6 py-3 font-mono text-xs text-right">{formatCurrencyINR(row.outstanding_exposure)}</td>
                            <td className="px-6 py-3 text-right font-bold">{row.average_risk_score?.toFixed(1) || '0.0'}</td>
                            <td className="px-6 py-3 text-right">
                              <span
                                className={`inline-flex rounded px-1.5 py-0.5 text-2xs font-bold border ${
                                  row.high_risk_loans_count > 0
                                    ? 'bg-red-500/10 text-red-500 border-red-500/20'
                                    : 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                                }`}
                              >
                                {row.high_risk_loans_count}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

              </div>

            </div>
          )}
        </div>
      )}

      {/* SUB TAB 2: VINTAGE & COHORTS */}
      {activeSubTab === 'vintage' && (
        <div className="space-y-6">
          {isVintageLoading ? (
            <div className="flex h-64 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          ) : isVintageUnavailable ? (
            <EmptyState
              title="Vintage Cohort Analysis Unavailable"
              description="Disbursement date or chronological cohort parameters are missing or unmapped in this dataset."
              icon={History}
              variant="solid"
            />
          ) : (
            <div className="space-y-6">
              
              {/* Vintage Heatmap matrix */}
              <div className="bg-card border border-border p-5 rounded-lg">
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">
                  Quarterly Disbursement Cohort Delinquency Heatmap Matrix
                </h3>
                <div className="overflow-x-auto rounded border border-border">
                  <table className="w-full text-left border-collapse" aria-label="Vintage Heatmap Matrix">
                    <thead>
                      <tr className="border-b border-border bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        <th className="px-6 py-2">Quarterly Cohort</th>
                        {vintage.visualizations.vintage_heatmap?.periods?.map((p: number) => (
                          <th key={p} className="px-6 py-2 text-center">Month {p}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="text-sm divide-y divide-border font-mono text-xs">
                      {vintage.visualizations.vintage_heatmap?.matrix?.map((rowValues: any[], idx: number) => {
                        const cohortName = vintage.visualizations.vintage_heatmap?.cohorts?.[idx] || 'Unknown';
                        return (
                          <tr key={idx} className="hover:bg-muted/10">
                            <td className="px-6 py-2.5 font-semibold text-foreground bg-muted/20">{cohortName}</td>
                            {rowValues?.map((val: number, cIdx: number) => {
                              const safeVal = val || 0;
                              return (
                                <td
                                  key={cIdx}
                                  style={{
                                    backgroundColor: `rgba(239, 68, 68, ${Math.min(1, safeVal / 10)})`,
                                  }}
                                  className="px-6 py-2.5 text-center font-semibold text-foreground"
                                >
                                  {safeVal.toFixed(2)}%
                                </td>
                              );
                            })}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Vintage trend details table */}
              <div className="bg-card border border-border p-5 rounded-lg">
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Cohorts Loss & Exposure Vintage Trend Details</h3>
                <div className="overflow-x-auto rounded border border-border">
                  <table className="w-full text-left border-collapse" aria-label="Vintage Trend Table">
                    <thead>
                      <tr className="border-b border-border bg-muted/30 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        <th className="px-6 py-2.5">Cohort</th>
                        <th className="px-6 py-2.5">Disbursed Loans</th>
                        <th className="px-6 py-2.5 font-mono text-right">Disbursed Volume</th>
                        <th className="px-6 py-2.5 text-right font-mono">Delinquency Rate</th>
                        <th className="px-6 py-2.5 text-right font-mono">High Risk Exposure</th>
                      </tr>
                    </thead>
                    <tbody className="text-sm divide-y divide-border">
                      {vintage.visualizations.vintage_trend_table?.map((row: any, idx: number) => (
                        <tr key={idx} className="hover:bg-muted/10">
                          <td className="px-6 py-3 font-semibold text-foreground">{row.cohort}</td>
                          <td className="px-6 py-3">{row.loan_count}</td>
                          <td className="px-6 py-3 font-mono text-xs text-right">{formatCurrencyINR(row.exposure)}</td>
                          <td className="px-6 py-3 text-right font-bold text-red-500 font-mono text-xs">{row.delinquency_rate_pct?.toFixed(2)}%</td>
                          <td className="px-6 py-3 text-right font-mono text-xs">{formatCurrencyINR(row.high_risk_exposure || 0)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          )}
        </div>
      )}

      {/* SUB TAB 3: RISK MIGRATION */}
      {activeSubTab === 'migration' && (
        <div className="space-y-6">
          {isMigrateLoading ? (
            <div className="flex h-64 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          ) : isMigrationUnavailable ? (
            <EmptyState
              title="Risk Migration Analysis Unavailable"
              description="Insufficient dataset history — upload a prior-period dataset to enable Risk Migration analysis."
              icon={ArrowRightLeft}
              variant="solid"
            />
          ) : (
            <div className="space-y-6">
              
              {/* Migration stats cards */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div className="rounded-lg border border-border bg-card p-5">
                  <div className="text-xs font-bold text-muted-foreground uppercase">Matched Borrowers Count</div>
                  <div className="mt-2 text-2xl font-black text-foreground">
                    {migration.visualizations.migration_summary_cards?.total_matched_borrowers?.toLocaleString() || 0}
                  </div>
                </div>
                <div className="rounded-lg border border-border bg-card p-5">
                  <div className="text-xs font-bold text-muted-foreground uppercase">Migrated Risk Ratings</div>
                  <div className="mt-2 text-2xl font-black text-foreground">
                    {migration.visualizations.migration_summary_cards?.migrated_borrowers_count?.toLocaleString() || 0}
                  </div>
                </div>
                <div className="rounded-lg border border-border bg-card p-5">
                  <div className="text-xs font-bold text-muted-foreground uppercase">Migration Rate Percentage</div>
                  <div className="mt-2 text-2xl font-black text-indigo-500">
                    {migration.visualizations.migration_summary_cards?.migration_rate_percentage?.toFixed(2) || '0.00'}%
                  </div>
                </div>
              </div>

              {/* Migration transition matrix table */}
              <div className="bg-card border border-border p-5 rounded-lg">
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">
                  Risk Category Migration counts Transition Matrix
                </h3>
                <div className="overflow-x-auto rounded border border-border">
                  <table className="w-full text-left border-collapse" aria-label="Migration Matrix Table">
                    <thead>
                      <tr className="border-b border-border bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        <th className="px-6 py-2">From \ To Category</th>
                        {migration.visualizations.migration_matrix?.to_categories?.map((cat: string) => (
                          <th key={cat} className="px-6 py-2 text-center">{cat}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="text-sm divide-y divide-border font-mono text-xs">
                      {migration.visualizations.migration_matrix?.from_categories?.map((fromCat: string, rIdx: number) => {
                        return (
                          <tr key={fromCat} className="hover:bg-muted/10">
                            <td className="px-6 py-2.5 font-semibold text-foreground bg-muted/20">{fromCat}</td>
                            {migration.visualizations.migration_matrix?.counts[rIdx]?.map((val: number, cIdx: number) => {
                              const toCat = migration.visualizations.migration_matrix.to_categories[cIdx];
                              const isDiagonal = fromCat === toCat;
                              return (
                                <td
                                  key={cIdx}
                                  className={`px-6 py-2.5 text-center font-semibold text-foreground ${
                                    isDiagonal ? 'bg-primary/5' : val > 0 ? 'bg-indigo-500/10' : ''
                                  }`}
                                >
                                  {val}
                                </td>
                              );
                            })}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          )}
        </div>
      )}
    </div>
  );
};
export default DiagnosticAnalytics;
