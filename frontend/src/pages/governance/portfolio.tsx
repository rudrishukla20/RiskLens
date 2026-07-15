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
  Layers,
  AlertTriangle,
  MapPin
} from 'lucide-react';
import { EmptyState } from '@/components/empty-state';

const COLORS = ['#10b981', '#f59e0b', '#ef4444'];

export const PortfolioAnalytics = () => {
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>(() => {
    return localStorage.getItem('selected_dataset_id') || '';
  });

  const [distTab, setDistTab] = useState<'regions' | 'purposes' | 'employment' | 'income'>('regions');

  // Fetch Portfolio Analytics
  const { data: portfolioData, isLoading, error } = useQuery({
    queryKey: ['portfolio-analytics', selectedDatasetId],
    queryFn: async () => {
      if (!selectedDatasetId) return null;
      const res = await apiClient.get('/analytics/portfolio', {
        params: { dataset_id: selectedDatasetId },
      });
      return res.data;
    },
    enabled: !!selectedDatasetId,
  });

  const handleDatasetChange = (id: string) => {
    setSelectedDatasetId(id);
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const getDistributionData = () => {
    if (!portfolioData || !portfolioData.visualizations?.exposure_distribution) return [];
    const dist = portfolioData.visualizations.exposure_distribution;
    let target = {};
    if (distTab === 'regions') target = dist.regions || {};
    else if (distTab === 'purposes') target = dist.loan_purposes || {};
    else if (distTab === 'employment') target = dist.employment_types || {};
    else if (distTab === 'income') target = dist.income_bands || {};

    return Object.entries(target).map(([key, val]) => ({
      name: key,
      value: val,
    }));
  };

  if (!selectedDatasetId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <h2 className="text-2xl font-bold tracking-tight">Portfolio Analytics</h2>
          <DatasetSelector selectedId={selectedDatasetId} onSelect={handleDatasetChange} />
        </div>
        <EmptyState
          title="No Structured Dataset Selected"
          description="Choose an active credit portfolio catalog from the selector at the top right to start portfolio calculations."
          icon={Layers}
          variant="dashed"
        />
      </div>
    );
  }

  const vis = portfolioData?.visualizations;
  const isDataAvailable = portfolioData && portfolioData.total_loans !== 0 && typeof portfolioData.total_loans === 'number';

  // Composition data format for Pie
  const comp = vis?.portfolio_composition_donut;
  const donutData = comp
    ? [
        { name: 'Low Risk', value: comp.LOW?.exposure || 0 },
        { name: 'Medium Risk', value: comp.MEDIUM?.exposure || 0 },
        { name: 'High Risk', value: comp.HIGH?.exposure || 0 },
      ]
    : [];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Portfolio Analytics</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Monitor diversification index, geographic concentrations, region risk matrices, and segment portfolio breakdowns.
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
          title="Portfolio Data Unavailable"
          description="This dataset has no active records or fields are unmapped. Align columns under catalogs details first."
          icon={AlertTriangle}
          variant="solid"
        />
      ) : (
        <div className="space-y-6">
          
          {/* Portfolio KPI Cards */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-5">
            <div className="rounded-lg border border-border bg-card p-4">
              <div className="text-3xs font-bold text-muted-foreground uppercase tracking-wider">Portfolio Size</div>
              <div className="mt-1 text-lg font-black text-foreground">
                {formatCurrency(portfolioData.portfolio_value || 0)}
              </div>
            </div>
            <div className="rounded-lg border border-border bg-card p-4">
              <div className="text-3xs font-bold text-muted-foreground uppercase tracking-wider">Average Risk Score</div>
              <div className="mt-1 text-lg font-black text-foreground">
                {portfolioData.average_risk_score?.toFixed(1) || '0.0'}
              </div>
            </div>
            <div className="rounded-lg border border-border bg-card p-4">
              <div className="text-3xs font-bold text-muted-foreground uppercase tracking-wider">Concentration Index</div>
              <div className="mt-1 text-lg font-black text-foreground">
                {portfolioData.concentration_index !== undefined && portfolioData.concentration_index !== null ? `${(portfolioData.concentration_index * 100).toFixed(1)}%` : 'N/A'}
              </div>
            </div>
            <div className="rounded-lg border border-border bg-card p-4">
              <div className="text-3xs font-bold text-muted-foreground uppercase tracking-wider">High-Risk Exposure</div>
              <div className="mt-1 text-lg font-black text-red-500">
                {formatCurrency(portfolioData.high_risk_exposure || 0)}
              </div>
            </div>
            <div className="rounded-lg border border-border bg-card p-4 col-span-2 lg:col-span-1">
              <div className="text-3xs font-bold text-muted-foreground uppercase tracking-wider">Diversification Index</div>
              <div className="mt-1 text-lg font-black text-emerald-500">
                {portfolioData.diversification_index?.toFixed(2) || '0.00'}
              </div>
            </div>
          </div>

          {/* Charts area */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            
            {/* Chart 1: Donut Composition */}
            <div className="bg-card border border-border p-5 rounded-lg">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Portfolio Risk Composition</h3>
              <div className="h-64 flex justify-center items-center">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={donutData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={75}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {donutData.map((_entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 2: Exposure distributions selector */}
            <div className="bg-card border border-border p-5 rounded-lg">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Exposure Distribution</h3>
                <div className="flex bg-muted/60 p-0.5 rounded border border-border/80 w-fit text-2xs font-semibold">
                  <button
                    onClick={() => setDistTab('regions')}
                    className={`px-2.5 py-1 rounded transition-colors ${distTab === 'regions' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'}`}
                  >
                    Region
                  </button>
                  <button
                    onClick={() => setDistTab('purposes')}
                    className={`px-2.5 py-1 rounded transition-colors ${distTab === 'purposes' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'}`}
                  >
                    Sector
                  </button>
                  <button
                    onClick={() => setDistTab('employment')}
                    className={`px-2.5 py-1 rounded transition-colors ${distTab === 'employment' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'}`}
                  >
                    Employment
                  </button>
                  <button
                    onClick={() => setDistTab('income')}
                    className={`px-2.5 py-1 rounded transition-colors ${distTab === 'income' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'}`}
                  >
                    Income
                  </button>
                </div>
              </div>
              <div className="h-60">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={getDistributionData()}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="name" stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                    <YAxis stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                    <Tooltip formatter={(value: any) => formatCurrency(value)} />
                    <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Region Risk matrix heatmap/table */}
            <div className="bg-card border border-border p-5 rounded-lg lg:col-span-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">
                Region Risk Classification Exposure Matrix
              </h3>
              <div className="overflow-x-auto rounded border border-border">
                <table className="w-full text-left border-collapse" aria-label="Region Risk Matrix Table">
                  <thead>
                    <tr className="border-b border-border bg-muted/30 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      <th className="px-6 py-2.5">Region</th>
                      <th className="px-6 py-2.5">Risk Category</th>
                      <th className="px-6 py-2.5">Total Loans Ingested</th>
                      <th className="px-6 py-2.5 font-mono text-right">Exposure Value</th>
                    </tr>
                  </thead>
                  <tbody className="text-sm divide-y divide-border">
                    {vis?.region_risk_heatmap?.matrix?.map((cell: any, idx: number) => {
                      return (
                        <tr key={idx} className="hover:bg-muted/10">
                          <td className="px-6 py-2.5 font-semibold text-foreground flex items-center gap-1">
                            <MapPin className="h-3.5 w-3.5 text-primary" />
                            <span>{cell.region}</span>
                          </td>
                          <td className="px-6 py-2.5">
                            <span
                              className={`inline-flex rounded px-1.5 py-0.5 text-3xs font-bold border ${
                                cell.risk_category === 'HIGH'
                                  ? 'bg-red-500/10 text-red-500 border-red-500/20'
                                  : cell.risk_category === 'MEDIUM'
                                  ? 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'
                                  : 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                              }`}
                            >
                              {cell.risk_category}
                            </span>
                          </td>
                          <td className="px-6 py-2.5">{cell.count}</td>
                          <td className="px-6 py-2.5 font-mono text-xs text-right">{formatCurrency(cell.exposure)}</td>
                        </tr>
                      );
                    })}
                    {(!vis?.region_risk_heatmap?.matrix || vis.region_risk_heatmap.matrix.length === 0) && (
                      <tr>
                        <td colSpan={4} className="text-center py-6 text-muted-foreground text-xs italic">
                          No regional risk segments mapped.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Drilldown table */}
            <div className="bg-card border border-border p-5 rounded-lg lg:col-span-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">
                Structured Segment Exposure & Risk Drilldown Table
              </h3>
              <div className="overflow-x-auto rounded border border-border">
                <table className="w-full text-left border-collapse" aria-label="Segment Drilldown">
                  <thead>
                    <tr className="border-b border-border bg-muted/30 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      <th className="px-6 py-2.5">Segment Type</th>
                      <th className="px-6 py-2.5">Segment Value</th>
                      <th className="px-6 py-2.5">Borrowers</th>
                      <th className="px-6 py-2.5 font-mono text-right">Exposure Amount</th>
                      <th className="px-6 py-2.5 text-right">Avg Risk Score</th>
                      <th className="px-6 py-2.5 text-right">High-Risk Share %</th>
                    </tr>
                  </thead>
                  <tbody className="text-sm divide-y divide-border">
                    {vis?.segment_drilldown_table?.slice(0, 10).map((row: any, idx: number) => {
                      const highRiskPct = row.portfolio_value > 0 ? ((row.high_risk_exposure / row.portfolio_value) * 100).toFixed(1) : '0.0';
                      return (
                        <tr key={idx} className="hover:bg-muted/10">
                          <td className="px-6 py-3 font-mono text-2xs text-muted-foreground uppercase">{row.segment_type}</td>
                          <td className="px-6 py-3 font-semibold text-foreground">{row.segment_value}</td>
                          <td className="px-6 py-3">{row.borrower_count}</td>
                          <td className="px-6 py-3 font-mono text-xs text-right">{formatCurrency(row.outstanding_exposure)}</td>
                          <td className="px-6 py-3 text-right">{row.average_risk_score?.toFixed(1) || '0.0'}</td>
                          <td className="px-6 py-3 text-right">
                            <span
                              className={`inline-flex rounded px-1.5 py-0.5 text-2xs font-bold border ${
                                parseFloat(highRiskPct) > 30
                                  ? 'bg-red-500/10 text-red-500 border-red-500/20'
                                  : parseFloat(highRiskPct) > 10
                                  ? 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'
                                  : 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                              }`}
                            >
                              {highRiskPct}%
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                    {(!vis?.segment_drilldown_table || vis.segment_drilldown_table.length === 0) && (
                      <tr>
                        <td colSpan={6} className="text-center py-6 text-muted-foreground text-xs italic">
                          No segment drilldown records computed.
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
export default PortfolioAnalytics;
