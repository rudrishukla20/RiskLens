import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { DatasetSelector } from '@/components/dataset-selector';
import { formatCurrencyINR } from '@/lib/formatter';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import {
  TrendingUp,
  Clock
} from 'lucide-react';
import { EmptyState } from '@/components/empty-state';

export const TrendAnalysis = () => {
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>(() => {
    return localStorage.getItem('selected_dataset_id') || '';
  });

  // Fetch Trend Analytics
  const { data: trendData, isLoading, error } = useQuery({
    queryKey: ['trend-analytics', selectedDatasetId],
    queryFn: async () => {
      if (!selectedDatasetId) return null;
      const res = await apiClient.get('/analytics/trends', {
        params: { dataset_id: selectedDatasetId },
      });
      return res.data;
    },
    enabled: !!selectedDatasetId,
  });

  const handleDatasetChange = (id: string) => {
    setSelectedDatasetId(id);
  };



  if (!selectedDatasetId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <h2 className="text-2xl font-bold tracking-tight">Trend Analysis</h2>
          <DatasetSelector selectedId={selectedDatasetId} onSelect={handleDatasetChange} />
        </div>
        <EmptyState
          title="No Structured Dataset Selected"
          description="Choose an active credit portfolio catalog from the selector at the top right to start chronological trend calculations."
          icon={TrendingUp}
          variant="dashed"
        />
      </div>
    );
  }

  const isUnavailable = trendData?.status === 'unavailable' || !trendData?.visualizations || trendData?.visualizations?.loan_growth_line?.length === 0;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Trend Analysis</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Analyze historical monthly portfolio growth, credit risk score trends, and default timeline metrics.
          </p>
        </div>
        <DatasetSelector selectedId={selectedDatasetId} onSelect={handleDatasetChange} />
      </div>

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      ) : error || isUnavailable ? (
        <EmptyState
          title="Chronological Trends Unavailable"
          description="This dataset does not contain disbursement dates, or the date fields have not been mapped to the canonical schema."
          icon={Clock}
          variant="solid"
        />
      ) : (
        <div className="space-y-6">
          
          {/* Trends Charts Grid */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            
            {/* Chart 1: Loan Count & Volume Growth */}
            <div className="bg-card border border-border p-5 rounded-lg">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Ingested Loan Count Growth Timeline</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendData.visualizations.loan_growth_line}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="period" stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                    <YAxis stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                    <Tooltip formatter={(value: any) => [value, 'Loans']} />
                    <Legend />
                    <Line type="monotone" dataKey="cumulative_count" name="Cumulative Loans" stroke="#6366f1" strokeWidth={3} dot={{ r: 4 }} />
                    <Line type="monotone" dataKey="monthly_count" name="New Loans" stroke="#10b981" strokeWidth={2} strokeDasharray="5 5" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 2: Exposure Area Trend */}
            <div className="bg-card border border-border p-5 rounded-lg">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Outstanding Portfolio Exposure Trend</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trendData.visualizations.exposure_trend_area}>
                    <defs>
                      <linearGradient id="colorExp" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25}/>
                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="period" stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                    <YAxis stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                    <Tooltip formatter={(value: any) => formatCurrencyINR(value)} />
                    <Legend />
                    <Area type="monotone" dataKey="exposure" name="Total Outstanding" stroke="#6366f1" fillOpacity={1} fill="url(#colorExp)" strokeWidth={2.5} />
                    <Area type="monotone" dataKey="high_risk_exposure" name="High Risk Exposure" stroke="#ef4444" fill="none" strokeWidth={2} strokeDasharray="4 4" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 3: Avg Risk Score Trend */}
            <div className="bg-card border border-border p-5 rounded-lg">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Monthly Weighted Average Credit Risk Score</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendData.visualizations.risk_score_trend_line}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="period" stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                    <YAxis stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} domain={[0, 100]} />
                    <Tooltip formatter={(value: any) => [value?.toFixed(1), 'Risk Score']} />
                    <Line type="monotone" dataKey="average_risk_score" stroke="#f59e0b" strokeWidth={3} dot={{ r: 5 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 4: Delinquency trend line */}
            <div className="bg-card border border-border p-5 rounded-lg">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Delinquency Days Timeline Trend</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendData.visualizations.delinquency_trend_line}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="period" stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                    <YAxis stroke="currentColor" style={{ opacity: 0.6, fontSize: '10px' }} />
                    <Tooltip formatter={(value: any) => [value?.toFixed(1), 'Days']} />
                    <Line type="monotone" dataKey="average_delinquency_days" stroke="#ef4444" strokeWidth={3} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

          </div>

        </div>
      )}
    </div>
  );
};
export default TrendAnalysis;
