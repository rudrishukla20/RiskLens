import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { DatasetSelector } from '@/components/dataset-selector';
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import {
  Users,
  AlertTriangle
} from 'lucide-react';

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#8b5cf6'];

export const BorrowerRisk = () => {
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>(() => {
    return localStorage.getItem('selected_dataset_id') || '';
  });

  // 1. Fetch Borrower Analytics
  const { data: borrowerData, isLoading, error } = useQuery({
    queryKey: ['borrower-analytics', selectedDatasetId],
    queryFn: async () => {
      if (!selectedDatasetId) return null;
      const res = await apiClient.get('/analytics/borrowers', {
        params: { dataset_id: selectedDatasetId },
      });
      return res.data;
    },
    enabled: !!selectedDatasetId,
  });

  // 2. Fetch Risk Assessments for High-Risk table
  const { data: riskAssessments } = useQuery({
    queryKey: ['risk-assessments', selectedDatasetId],
    queryFn: async () => {
      if (!selectedDatasetId) return [];
      const res = await apiClient.get('/analytics/risk', {
        params: { dataset_id: selectedDatasetId },
      });
      return res.data;
    },
    enabled: !!selectedDatasetId,
  });

  // Filter high-risk assessments
  const highRiskBorrowers = riskAssessments?.filter((r: any) => r.risk_category === 'HIGH') || [];

  const handleDatasetChange = (id: string) => {
    setSelectedDatasetId(id);
  };

  const getFormatData = (dict: Record<string, number> | string | undefined) => {
    if (!dict || typeof dict === 'string') return [];
    return Object.entries(dict).map(([key, val]) => ({
      name: key,
      value: val,
    }));
  };

  const getStackedData = (stacked: any) => {
    if (!stacked || !stacked.default_status_by_employment) return [];
    const { categories, series } = stacked.default_status_by_employment;
    return categories.map((cat: string, idx: number) => ({
      name: cat,
      Performing: series.Performing[idx] || 0,
      Defaulted: series.Defaulted[idx] || 0,
    }));
  };

  if (!selectedDatasetId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <h2 className="text-2xl font-bold tracking-tight">Borrower Risk Analysis</h2>
          <DatasetSelector selectedId={selectedDatasetId} onSelect={handleDatasetChange} />
        </div>
        <div className="flex flex-col items-center justify-center py-16 text-center border-2 border-dashed border-border rounded-lg bg-card shadow-sm">
          <Users className="h-12 w-12 text-muted-foreground mb-3" />
          <h4 className="font-semibold text-foreground">No Structured Dataset Selected</h4>
          <p className="text-xs text-muted-foreground max-w-sm mt-1">
            Choose an active credit portfolio catalog from the selector at the top right to start risk segment calculations.
          </p>
        </div>
      </div>
    );
  }

  const vis = borrowerData?.visualizations;
  const isDataAvailable = borrowerData && borrowerData.borrower_count !== 0 && typeof borrowerData.borrower_count === 'number';

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Borrower Risk Analysis</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Identify borrower delinquencies, default vectors, and demographic segments risk densities.
          </p>
        </div>
        <DatasetSelector selectedId={selectedDatasetId} onSelect={handleDatasetChange} />
      </div>

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      ) : error || !isDataAvailable ? (
        <div className="flex flex-col items-center justify-center py-16 text-center border border-border bg-card rounded-lg shadow-sm">
          <AlertTriangle className="h-10 w-10 text-yellow-500 mb-2" />
          <h4 className="font-semibold">Borrower Data Unavailable</h4>
          <p className="text-xs text-muted-foreground max-w-md mt-1">
            This dataset has no active records or borrower fields are unmapped. Align columns under catalogs details first.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          
          {/* Main stats */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-border bg-card p-5">
              <div className="text-xs font-bold text-muted-foreground uppercase">Unique Borrowers Count</div>
              <div className="mt-2 text-2xl font-black text-foreground">{borrowerData.borrower_count?.toLocaleString()}</div>
            </div>
            <div className="rounded-lg border border-border bg-card p-5">
              <div className="text-xs font-bold text-muted-foreground uppercase">Income Levels Profile</div>
              <div className="mt-2 text-sm space-y-1">
                <div className="flex justify-between"><span className="text-muted-foreground">Average:</span> <span className="font-semibold">${borrowerData.income_distribution?.mean?.toLocaleString() || '0'}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Median:</span> <span className="font-semibold">${borrowerData.income_distribution?.median?.toLocaleString() || '0'}</span></div>
              </div>
            </div>
            <div className="rounded-lg border border-border bg-card p-5">
              <div className="text-xs font-bold text-muted-foreground uppercase">Assessed Risk Distribution</div>
              <div className="mt-2 text-xs flex gap-2 items-center flex-wrap">
                <span className="bg-emerald-500/10 text-emerald-500 rounded px-2 py-0.5 font-semibold">Low Risk</span>
                <span className="bg-yellow-500/10 text-yellow-500 rounded px-2 py-0.5 font-semibold">Med Risk</span>
                <span className="bg-red-500/10 text-red-500 rounded px-2 py-0.5 font-semibold font-bold">High Risk</span>
              </div>
            </div>
          </div>

          {/* Demographics distributions */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            
            {/* Chart 1: Income Bands Bar */}
            <div className="bg-card border border-border p-5 rounded-lg">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Risk by Income Bands distribution</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={getFormatData(borrowerData.income_bands)}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="name" stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                    <YAxis stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 2: Performing vs Defaulted Loans by Employment (Stacked Bar) */}
            <div className="bg-card border border-border p-5 rounded-lg">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Default Status by Employment Type</h3>
              <div className="h-64">
                {vis?.stacked_bars ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={getStackedData(vis.stacked_bars)}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="name" stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                      <YAxis stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="Performing" stackId="a" fill="#10b981" />
                      <Bar dataKey="Defaulted" stackId="a" fill="#ef4444" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="text-xs text-muted-foreground italic text-center py-20">Stacked bar data unavailable.</div>
                )}
              </div>
            </div>

            {/* Chart 3: Age Distribution Pie */}
            <div className="bg-card border border-border p-5 rounded-lg">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Borrowers Age Segments</h3>
              <div className="h-64 flex justify-center items-center">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={getFormatData(borrowerData.age_bands)}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={75}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {getFormatData(borrowerData.age_bands).map((_entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 4: Boxplot approximation of Income by Employment */}
            <div className="bg-card border border-border p-5 rounded-lg">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Income Distribution Range by Employment Group</h3>
              <div className="space-y-4 max-h-64 overflow-y-auto pr-2">
                {vis?.boxplots?.income_by_employment?.map((box: any, idx: number) => {
                  const maxRange = Math.max(...vis.boxplots.income_by_employment.map((b: any) => b.max)) || 1;
                  return (
                    <div key={idx} className="space-y-1">
                      <div className="text-xs font-bold text-foreground">{box.group}</div>
                      <div className="flex items-center gap-3">
                        <span className="text-[10px] text-muted-foreground font-mono font-semibold">${box.min.toLocaleString()}</span>
                        <div className="relative flex-1 bg-muted/60 h-6 rounded border border-border flex items-center">
                          {/* Q1 to Q3 Box */}
                          <div
                            className="absolute bg-primary/20 border-x border-primary h-full"
                            style={{
                              left: `${(box.q1 / maxRange) * 100}%`,
                              width: `${((box.q3 - box.q1) / maxRange) * 100}%`
                            }}
                          />
                          {/* Median Marker */}
                          <div
                            className="absolute bg-primary w-0.5 h-full z-10"
                            style={{ left: `${(box.median / maxRange) * 100}%` }}
                            title={`Median: $${box.median.toLocaleString()}`}
                          />
                        </div>
                        <span className="text-[10px] text-muted-foreground font-mono font-semibold">${box.max.toLocaleString()}</span>
                      </div>
                    </div>
                  );
                }) || (
                  <div className="text-xs text-muted-foreground italic text-center py-20">Boxplot range data unavailable.</div>
                )}
              </div>
            </div>

            {/* Chart 5: Risk Heatmap Table */}
            <div className="bg-card border border-border p-5 rounded-lg lg:col-span-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">
                Segment Default Risk Matrix (Employment vs Income Band)
              </h3>
              <div className="overflow-x-auto rounded border border-border">
                <table className="w-full text-left border-collapse" aria-label="Risk Default Matrix">
                  <thead>
                    <tr className="border-b border-border bg-muted/30 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      <th className="px-6 py-2.5">Employment Category</th>
                      <th className="px-6 py-2.5">Income Band</th>
                      <th className="px-6 py-2.5">Active Loans</th>
                      <th className="px-6 py-2.5">Default Rate %</th>
                      <th className="px-6 py-2.5">Risk Exposure Density</th>
                    </tr>
                  </thead>
                  <tbody className="text-sm divide-y divide-border">
                    {vis?.heatmaps?.employment_vs_income_risk?.map((cell: any, idx: number) => {
                      return (
                        <tr key={idx} className="hover:bg-muted/10">
                          <td className="px-6 py-2.5 font-semibold text-foreground">{cell.x}</td>
                          <td className="px-6 py-2.5">{cell.y}</td>
                          <td className="px-6 py-2.5">{cell.loans_count}</td>
                          <td className="px-6 py-2.5 font-mono text-xs text-red-500 font-bold">{cell.value}%</td>
                          <td className="px-6 py-2.5">
                            <span
                              className={`inline-flex rounded px-2 py-0.5 text-3xs font-bold border ${
                                cell.value > 25
                                  ? 'bg-red-500/10 text-red-500 border-red-500/20'
                                  : cell.value > 10
                                  ? 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'
                                  : 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                              }`}
                            >
                              {cell.value > 25 ? 'HIGH RISK' : cell.value > 10 ? 'MODERATE' : 'LOW RISK'}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                    {(!vis?.heatmaps?.employment_vs_income_risk || vis.heatmaps.employment_vs_income_risk.length === 0) && (
                      <tr>
                        <td colSpan={5} className="text-center py-6 text-muted-foreground text-xs italic">
                          No cross-tab matrix computed.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* High-risk exposures table */}
            <div className="bg-card border border-border p-5 rounded-lg lg:col-span-2">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  High-Risk Borrower Profiles Exposure Table
                </h3>
                <span className="inline-flex rounded-full bg-red-500/10 px-2 py-0.5 text-2xs font-bold text-red-500 border border-red-500/20">
                  {highRiskBorrowers.length} Identified
                </span>
              </div>
              <div className="overflow-x-auto rounded border border-border">
                <table className="w-full text-left border-collapse" aria-label="High-Risk Exposure Table">
                  <thead>
                    <tr className="border-b border-border bg-muted/30 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      <th className="px-6 py-2.5">Borrower ID</th>
                      <th className="px-6 py-2.5">Risk Score</th>
                      <th className="px-6 py-2.5">Risk Drivers Summary</th>
                      <th className="px-6 py-2.5 font-mono text-right">Assessed At</th>
                    </tr>
                  </thead>
                  <tbody className="text-sm divide-y divide-border">
                    {highRiskBorrowers.map((profile: any) => (
                      <tr key={profile.id} className="hover:bg-red-500/5 transition-colors">
                        <td className="px-6 py-3 font-semibold text-foreground">{profile.borrower_id || 'N/A'}</td>
                        <td className="px-6 py-3">
                          <span className="font-mono text-xs font-bold text-red-500 bg-red-500/10 rounded px-1.5 py-0.5 border border-red-500/20">
                            {profile.risk_score?.toFixed(1) || '0.0'}
                          </span>
                        </td>
                        <td className="px-6 py-3 text-xs text-muted-foreground">{profile.risk_driver_summary || 'No summary'}</td>
                        <td className="px-6 py-3 text-xs text-muted-foreground font-mono text-right">
                          {new Date(profile.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                    {highRiskBorrowers.length === 0 && (
                      <tr>
                        <td colSpan={4} className="text-center py-6 text-muted-foreground text-xs italic">
                          No high-risk borrower assessments found in this dataset version.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

          </div>

        </div>
      )}
    </div>
  );
};
export default BorrowerRisk;
