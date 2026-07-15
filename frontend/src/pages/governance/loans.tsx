import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { DatasetSelector } from '@/components/dataset-selector';
import { formatCurrencyINR, formatLabel } from '@/lib/formatter';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Treemap
} from 'recharts';
import {
  Activity,
  AlertTriangle,
  Layers
} from 'lucide-react';
import { EmptyState } from '@/components/empty-state';

export const LoanExposure = () => {
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>(() => {
    return localStorage.getItem('selected_dataset_id') || '';
  });

  // Fetch Loan Analytics
  const { data: loanData, isLoading, error } = useQuery({
    queryKey: ['loan-analytics', selectedDatasetId],
    queryFn: async () => {
      if (!selectedDatasetId) return null;
      const res = await apiClient.get('/analytics/loans', {
        params: { dataset_id: selectedDatasetId },
      });
      return res.data;
    },
    enabled: !!selectedDatasetId,
  });

  const handleDatasetChange = (id: string) => {
    setSelectedDatasetId(id);
  };

  // Convert histogram bins to Recharts friendly list
  const getHistogramData = (hist: any) => {
    if (!hist || !hist.counts) return [];
    return hist.counts.map((c: number, idx: number) => ({
      range: formatLabel(hist.bins[idx] || `Bin ${idx + 1}`),
      Count: c,
    }));
  };

  // Convert loan exposure dictionary to list
  const getExposureBarsData = (bars: any) => {
    if (!bars || typeof bars !== 'object') return [];
    return Object.entries(bars).map(([key, val]) => ({
      name: key,
      Exposure: val,
    }));
  };

  if (!selectedDatasetId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <h2 className="text-2xl font-bold tracking-tight">Loan Exposure Analysis</h2>
          <DatasetSelector selectedId={selectedDatasetId} onSelect={handleDatasetChange} />
        </div>
        <EmptyState
          title="No Structured Dataset Selected"
          description="Choose an active credit portfolio catalog from the selector at the top right to start loan exposure calculations."
          icon={Layers}
          variant="dashed"
        />
      </div>
    );
  }

  const vis = loanData?.visualizations;
  const isDataAvailable = loanData && loanData.total_loans !== 0 && typeof loanData.total_loans === 'number';

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Loan Exposure Analysis</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Evaluate interest rate distributions, delinquency aging brackets, outstanding exposures, and repayment burden ratios.
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
          title="Loan Data Unavailable"
          description="This dataset has no active records or loan fields are unmapped. Align columns under catalogs details first."
          icon={AlertTriangle}
          variant="solid"
        />
      ) : (
        <div className="space-y-6">
          
          {/* Main loan KPIs */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="rounded-lg border border-border bg-card p-5">
              <div className="text-xs font-bold text-muted-foreground uppercase">Total Loan Contracts</div>
              <div className="mt-2 text-2xl font-black text-foreground">{loanData.total_loans?.toLocaleString()}</div>
            </div>
            <div className="rounded-lg border border-border bg-card p-5">
              <div className="text-xs font-bold text-muted-foreground uppercase">Outstanding Exposure</div>
              <div className="mt-2 text-2xl font-black text-foreground">
                {formatCurrencyINR(loanData.outstanding_exposure || 0)}
              </div>
            </div>
            <div className="rounded-lg border border-border bg-card p-5">
              <div className="text-xs font-bold text-muted-foreground uppercase">Avg Loan Size</div>
              <div className="mt-2 text-2xl font-black text-foreground">
                {formatCurrencyINR(loanData.average_loan_amount || 0)}
              </div>
            </div>
            <div className="rounded-lg border border-border bg-card p-5">
              <div className="text-xs font-bold text-muted-foreground uppercase">Repayment Burden Ratio</div>
              <div className="mt-2 text-2xl font-black text-foreground">
                {loanData.repayment_burden_ratio !== undefined && loanData.repayment_burden_ratio !== null ? `${(loanData.repayment_burden_ratio * 100).toFixed(1)}%` : 'N/A'}
              </div>
            </div>
          </div>

          {/* Exposure & purpose charts */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            
            {/* Chart 1: Outstanding Exposure Bars */}
            <div className="bg-card border border-border p-5 rounded-lg">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Outstanding Exposure by Status</h3>
              <div className="h-64">
                {vis?.loan_exposure_bars ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={getExposureBarsData(vis.loan_exposure_bars)}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="name" stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                      <YAxis stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                      <Tooltip formatter={(value: any) => formatCurrencyINR(value)} />
                      <Bar dataKey="Exposure" fill="#6366f1" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="text-xs text-muted-foreground italic text-center py-20">Exposure status data unavailable.</div>
                )}
              </div>
            </div>

            {/* Chart 2: Purpose Treemap */}
            <div className="bg-card border border-border p-5 rounded-lg">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Loan Purpose Exposure Treemap</h3>
              <div className="h-64">
                {vis?.loan_purpose_treemap?.children && vis.loan_purpose_treemap.children.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <Treemap
                      data={vis.loan_purpose_treemap.children}
                      dataKey="exposure"
                      nameKey="name"
                      stroke="#1e293b"
                      fill="#6366f1"
                    >
                      <Tooltip formatter={(value: any) => [formatCurrencyINR(value), 'Exposure']} />
                    </Treemap>
                  </ResponsiveContainer>
                ) : (
                  <div className="text-xs text-muted-foreground italic text-center py-20">Treemap children data unavailable.</div>
                )}
              </div>
            </div>

            {/* Chart 3: Loan Amount Histogram */}
            <div className="bg-card border border-border p-5 rounded-lg">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Loan Amount Distribution Histogram</h3>
              <div className="h-64">
                {vis?.loan_amount_histogram ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={getHistogramData(vis.loan_amount_histogram)}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="range" stroke="currentColor" style={{ opacity: 0.6, fontSize: '9px' }} />
                      <YAxis stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                      <Tooltip />
                      <Bar dataKey="Count" fill="#10b981" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="text-xs text-muted-foreground italic text-center py-20">Histogram distribution data unavailable.</div>
                )}
              </div>
            </div>

            {/* Boxplot 4: Interest Rate Boxplot Approximation */}
            <div className="bg-card border border-border p-5 rounded-lg">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Interest Rate Distribution Range</h3>
              <div className="flex flex-col justify-center h-full max-h-64 space-y-4">
                {vis?.interest_rate_boxplot && typeof vis.interest_rate_boxplot === 'object' && vis.interest_rate_boxplot.median !== undefined ? (
                  <div className="space-y-4">
                    <div className="text-xs text-muted-foreground leading-relaxed flex items-start gap-1.5 rounded bg-muted/30 p-3">
                      <Layers className="h-4 w-4 shrink-0 text-primary mt-0.5" />
                      <span>
                        This boxplot represents the IQR (Interquartile Range) for interest rates. Mapped limits:
                        Median is at <strong>{vis.interest_rate_boxplot.median?.toFixed(2)}%</strong>. 
                        Middle 50% variables are between <strong>{vis.interest_rate_boxplot.q1?.toFixed(2)}%</strong> and <strong>{vis.interest_rate_boxplot.q3?.toFixed(2)}%</strong>.
                      </span>
                    </div>

                    <div className="space-y-2">
                      {(() => {
                        const maxVal = Math.max(vis.interest_rate_boxplot.max || 40, 40);
                        return (
                          <>
                            <div className="flex justify-between text-2xs text-muted-foreground font-semibold font-mono">
                              <span>Min: {vis.interest_rate_boxplot.min?.toFixed(2)}%</span>
                              <span>Max: {vis.interest_rate_boxplot.max?.toFixed(2)}%</span>
                            </div>
                            <div className="relative w-full bg-muted/60 h-8 rounded border border-border flex items-center shadow-inner">
                              {/* Q1 to Q3 Box */}
                              <div
                                className="absolute bg-primary/25 border-x-2 border-primary h-full"
                                style={{
                                  left: `${(vis.interest_rate_boxplot.q1 / maxVal) * 100}%`,
                                  width: `${((vis.interest_rate_boxplot.q3 - vis.interest_rate_boxplot.q1) / maxVal) * 100}%`
                                }}
                              />
                              {/* Median line */}
                              <div
                                className="absolute bg-primary w-0.75 h-full z-10"
                                style={{ left: `${(vis.interest_rate_boxplot.median / maxVal) * 100}%` }}
                              />
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-muted-foreground italic text-center py-20">Interest rate boxplot data unavailable.</div>
                )}
              </div>
            </div>

            {/* Waterfall 5: Exposure Waterfall Flow */}
            <div className="bg-card border border-border p-5 rounded-lg lg:col-span-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Ingested Portfolio Principal Exposure Waterfall</h3>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
                {vis?.exposure_waterfall?.map((step: any, idx: number) => {
                  return (
                    <div
                      key={idx}
                      className={`rounded-lg border p-4 text-center relative overflow-hidden ${
                        step.type === 'total'
                          ? 'border-indigo-500/30 bg-indigo-500/5'
                          : step.type === 'subtraction'
                          ? 'border-emerald-500/20 bg-emerald-500/5'
                          : step.type === 'remaining'
                          ? 'border-primary/30 bg-primary/5'
                          : 'border-red-500/20 bg-red-500/5'
                      }`}
                    >
                      <div className="text-3xs uppercase font-bold text-muted-foreground tracking-wider">{step.label}</div>
                      <div
                        className={`mt-2 text-lg font-black ${
                          step.type === 'subtraction'
                            ? 'text-emerald-500'
                            : step.type === 'info'
                            ? 'text-red-500'
                            : 'text-foreground'
                        }`}
                      >
                        {formatCurrencyINR(step.value)}
                      </div>
                      <p className="text-[9px] text-muted-foreground mt-1 uppercase">
                        {step.type === 'total' ? 'Initial Sum' : step.type === 'subtraction' ? 'Outflow' : step.type === 'remaining' ? 'Balance' : 'Loss exception'}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Table 6: Delinquency aging table */}
            <div className="bg-card border border-border p-5 rounded-lg lg:col-span-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Delinquency Aging Brackets Table</h3>
              <div className="overflow-x-auto rounded border border-border">
                <table className="w-full text-left border-collapse" aria-label="Delinquency Aging Brackets">
                  <thead>
                    <tr className="border-b border-border bg-muted/30 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      <th className="px-6 py-2.5">Aging Bucket</th>
                      <th className="px-6 py-2.5">Loans Count</th>
                      <th className="px-6 py-2.5 font-mono text-right">Exposure Amount</th>
                      <th className="px-6 py-2.5 text-right">Share %</th>
                    </tr>
                  </thead>
                  <tbody className="text-sm divide-y divide-border">
                    {vis?.delinquency_aging_table?.map((item: any, idx: number) => {
                      return (
                        <tr
                          key={idx}
                          className={`hover:bg-muted/10 transition-colors ${
                            item.bucket !== 'Current' && item.bucket !== '0 DPD' ? 'bg-red-500/2xs' : ''
                          }`}
                        >
                          <td className="px-6 py-3 font-semibold text-foreground">{item.bucket}</td>
                          <td className="px-6 py-3">{item.count}</td>
                          <td className="px-6 py-3 font-mono text-xs text-right">{formatCurrencyINR(item.exposure)}</td>
                          <td className="px-6 py-3 text-right font-semibold">
                            <span
                              className={`inline-flex rounded px-1.5 py-0.5 text-2xs ${
                                item.bucket === 'Current' || item.bucket === '0 DPD'
                                  ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                                  : 'bg-red-500/10 text-red-500 border border-red-500/20'
                              }`}
                            >
                              {item.percentage_of_loans}%
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                    {(!vis?.delinquency_aging_table || vis.delinquency_aging_table.length === 0) && (
                      <tr>
                        <td colSpan={4} className="text-center py-6 text-muted-foreground text-xs italic">
                          No delinquency stats computed.
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
export default LoanExposure;
