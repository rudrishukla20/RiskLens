import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { DatasetSelector } from '@/components/dataset-selector';
import { formatCurrencyINR, formatLabel } from '@/lib/formatter';
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Treemap
} from 'recharts';
import {
  AlertTriangle,
  Compass
} from 'lucide-react';
import { EmptyState } from '@/components/empty-state';

export const ConcentrationAnalysis = () => {
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>(() => {
    return localStorage.getItem('selected_dataset_id') || '';
  });

  // Fetch Concentration Analytics
  const { data: concentrationData, isLoading, error } = useQuery({
    queryKey: ['concentration-analytics', selectedDatasetId],
    queryFn: async () => {
      if (!selectedDatasetId) return null;
      const res = await apiClient.get('/analytics/concentration', {
        params: { dataset_id: selectedDatasetId },
      });
      return res.data;
    },
    enabled: !!selectedDatasetId,
  });

  const handleDatasetChange = (id: string) => {
    setSelectedDatasetId(id);
  };



  const getHHICategory = (hhi: number) => {
    if (hhi < 1500) return { label: 'Diversified / Safe', color: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20' };
    if (hhi <= 2500) return { label: 'Moderate Concentration', color: 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20' };
    return { label: 'High Concentration Risk', color: 'text-red-500 bg-red-500/10 border-red-500/20' };
  };

  if (!selectedDatasetId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <h2 className="text-2xl font-bold tracking-tight">Concentration Analysis</h2>
          <DatasetSelector selectedId={selectedDatasetId} onSelect={handleDatasetChange} />
        </div>
        <EmptyState
          title="No Structured Dataset Selected"
          description="Choose an active credit portfolio catalog from the selector at the top right to start concentration calculations."
          icon={Compass}
          variant="dashed"
        />
      </div>
    );
  }

  const vis = concentrationData?.visualizations;
  const isDataAvailable = concentrationData && concentrationData.herfindahl_hirschman_index !== undefined;

  const hhiCat = getHHICategory(concentrationData?.herfindahl_hirschman_index || 0);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Concentration Analysis</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Identify regulatory limits breaches, Herfindahl-Hirschman Index (HHI) curves, and Pareto concentration margins.
          </p>
        </div>
        <DatasetSelector selectedId={selectedDatasetId} onSelect={handleDatasetChange} />
      </div>

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      ) : error || !isDataAvailable ? (
        <EmptyState
          title="Concentration Data Unavailable"
          description="This dataset has no active records or concentration fields are unmapped. Align columns under catalogs details first."
          icon={AlertTriangle}
          variant="solid"
        />
      ) : (
        <div className="space-y-6">
          
          {/* Herfindahl-Hirschman index details */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            
            {/* HHI Score meter card */}
            <div className="rounded-lg border border-border bg-card p-5 md:col-span-1 shadow-2xs flex flex-col justify-between">
              <div>
                <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Herfindahl-Hirschman Index</div>
                <div className="mt-2 text-3xl font-black text-foreground">
                  {concentrationData.herfindahl_hirschman_index?.toFixed(1) || '0.0'}
                </div>
              </div>
              <div className="mt-4">
                <span className={`inline-flex rounded-md border px-2.5 py-1 text-xs font-bold ${hhiCat.color}`}>
                  {hhiCat.label}
                </span>
                <p className="text-3xs text-muted-foreground mt-2 leading-relaxed">
                  HHI scores measure overall portfolio diversification. Scores &lt; 1500 indicate safe, well-diversified portfolios.
                </p>
              </div>
            </div>

            {/* Segment HHI Dimension Indexes */}
            <div className="rounded-lg border border-border bg-card p-5 md:col-span-2 shadow-2xs">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3">Concentration Index by Dimension</h3>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div className="bg-muted/30 border border-border p-3 rounded text-center">
                  <div className="text-3xs uppercase font-bold text-muted-foreground">Geographic (Region)</div>
                  <div className="text-lg font-black text-foreground mt-1">
                    {concentrationData.hhi_by_dimension?.region?.toFixed(0) || '0'}
                  </div>
                </div>
                <div className="bg-muted/30 border border-border p-3 rounded text-center">
                  <div className="text-3xs uppercase font-bold text-muted-foreground">Loan Purpose</div>
                  <div className="text-lg font-black text-foreground mt-1">
                    {concentrationData.hhi_by_dimension?.loan_purpose?.toFixed(0) || '0'}
                  </div>
                </div>
                <div className="bg-muted/30 border border-border p-3 rounded text-center">
                  <div className="text-3xs uppercase font-bold text-muted-foreground">Employment</div>
                  <div className="text-lg font-black text-foreground mt-1">
                    {concentrationData.hhi_by_dimension?.employment_type?.toFixed(0) || '0'}
                  </div>
                </div>
                <div className="bg-muted/30 border border-border p-3 rounded text-center">
                  <div className="text-3xs uppercase font-bold text-muted-foreground">Income Bands</div>
                  <div className="text-lg font-black text-foreground mt-1">
                    {concentrationData.hhi_by_dimension?.income_band?.toFixed(0) || '0'}
                  </div>
                </div>
              </div>
            </div>

          </div>

          {/* Pareto & Treemap */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            
            {/* Chart 1: Regional Pareto chart */}
            <div className="bg-card border border-border p-5 rounded-lg">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Region Exposure Pareto Analysis</h3>
              <div className="h-64">
                {vis?.pareto_chart && vis.pareto_chart.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={vis.pareto_chart}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="region" stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                      <YAxis yAxisId="left" stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                      <YAxis yAxisId="right" orientation="right" domain={[0, 100]} stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                      <Tooltip formatter={(value: any, name: string) => name === 'exposure' ? formatCurrencyINR(value) : `${value}%`} />
                      <Legend />
                      <Bar yAxisId="left" dataKey="exposure" fill="#6366f1" radius={[4, 4, 0, 0]} />
                      <Line yAxisId="right" type="monotone" dataKey="cumulative_percentage" stroke="#ef4444" strokeWidth={3} dot={{ r: 4 }} />
                    </ComposedChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="text-xs text-muted-foreground italic text-center py-20">Pareto chart data unavailable.</div>
                )}
              </div>
            </div>

            {/* Chart 2: Purpose Treemap */}
            <div className="bg-card border border-border p-5 rounded-lg">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Segment Exposure Treemap</h3>
              <div className="h-64">
                {vis?.treemap?.purposes?.children && vis.treemap.purposes.children.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <Treemap
                      data={vis.treemap.purposes.children}
                      dataKey="exposure"
                      nameKey="name"
                      stroke="#1e293b"
                      fill="#6366f1"
                    >
                      <Tooltip formatter={(value: any) => [formatCurrencyINR(value), 'Exposure']} />
                    </Treemap>
                  </ResponsiveContainer>
                ) : (
                  <div className="text-xs text-muted-foreground italic text-center py-20">Treemap data unavailable.</div>
                )}
              </div>
            </div>

            {/* Table 3: Top Concentration Table */}
            <div className="bg-card border border-border p-5 rounded-lg lg:col-span-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">
                Ranked Portfolio Exposure Concentration Table
              </h3>
              <div className="overflow-x-auto rounded border border-border">
                <table className="w-full text-left border-collapse" aria-label="Ranked Exposure Table">
                  <thead>
                    <tr className="border-b border-border bg-muted/30 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      <th className="px-6 py-2.5">Rank</th>
                      <th className="px-6 py-2.5">Concentration Type</th>
                      <th className="px-6 py-2.5">Segment / Value</th>
                      <th className="px-6 py-2.5 font-mono text-right">Outstanding Exposure</th>
                      <th className="px-6 py-2.5 text-right">Exposure Share %</th>
                    </tr>
                  </thead>
                  <tbody className="text-sm divide-y divide-border">
                    {vis?.ranked_exposure_table?.slice(0, 10).map((row: any, idx: number) => {
                      return (
                        <tr key={idx} className="hover:bg-muted/10">
                          <td className="px-6 py-3 font-semibold text-foreground">{row.rank}</td>
                          <td className="px-6 py-3 font-mono text-2xs text-muted-foreground uppercase">{row.concentration_type}</td>
                          <td className="px-6 py-3 font-semibold">{formatLabel(row.concentration_key)}</td>
                          <td className="px-6 py-3 font-mono text-xs text-right">{formatCurrencyINR(row.exposure_amount)}</td>
                          <td className="px-6 py-3 text-right">
                            <span
                              className={`inline-flex rounded px-1.5 py-0.5 text-2xs font-bold border ${
                                row.exposure_percentage > 35
                                  ? 'bg-red-500/10 text-red-500 border-red-500/20'
                                  : row.exposure_percentage > 15
                                  ? 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'
                                  : 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                              }`}
                            >
                              {row.exposure_percentage}%
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                    {(!vis?.ranked_exposure_table || vis.ranked_exposure_table.length === 0) && (
                      <tr>
                        <td colSpan={5} className="text-center py-6 text-muted-foreground text-xs italic">
                          No concentration indexes ranked.
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
export default ConcentrationAnalysis;
