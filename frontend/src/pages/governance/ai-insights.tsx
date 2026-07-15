import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { DatasetSelector } from '@/components/dataset-selector';
import {
  BrainCircuit,
  Sparkles,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  Lightbulb,
  ShieldCheck,
  TrendingUp,
  FileText
} from 'lucide-react';
import { EmptyState } from '@/components/empty-state';

export const AIInsightsPage = () => {
  const queryClient = useQueryClient();
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>(() => {
    return localStorage.getItem('selected_dataset_id') || '';
  });

  const handleDatasetChange = (id: string) => {
    setSelectedDatasetId(id);
  };

  // 1. Fetch latest AI Insight
  const { data: insight, isLoading, error, refetch } = useQuery({
    queryKey: ['ai-insight', selectedDatasetId],
    queryFn: async () => {
      if (!selectedDatasetId) return null;
      const res = await apiClient.get('/ai-insights', {
        params: { dataset_id: selectedDatasetId }
      });
      // Filter for RISK analysis type
      const riskInsights = res.data?.items?.filter((item: any) => item.analysis_type === 'RISK') || [];
      return riskInsights[0] || null;
    },
    enabled: !!selectedDatasetId,
  });

  // 2. Generate/Regenerate Mutation
  const generateMutation = useMutation({
    mutationFn: async () => {
      return await apiClient.post('/ai-insights/generate', {
        dataset_id: selectedDatasetId,
        analysis_type: 'RISK',
        force_regenerate: true,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-insight', selectedDatasetId] });
      refetch();
    },
    onError: (err: any) => {
      alert(err.message || 'Failed to generate AI commentary.');
    }
  });

  if (!selectedDatasetId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <h2 className="text-2xl font-bold tracking-tight">AI LLM Commentary Insights</h2>
          <DatasetSelector selectedId={selectedDatasetId} onSelect={handleDatasetChange} />
        </div>
        <EmptyState
          title="No Structured Dataset Selected"
          description="Choose an active credit portfolio catalog from the selector at the top right to load explainable AI commentary."
          icon={BrainCircuit}
          variant="dashed"
        />
      </div>
    );
  }

  const isGenerating = generateMutation.isPending;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">AI LLM Commentary Insights</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Generative explainable AI findings, risks analysis, and compliance recommendations.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <DatasetSelector selectedId={selectedDatasetId} onSelect={handleDatasetChange} />
          <button
            onClick={() => generateMutation.mutate()}
            disabled={isGenerating}
            className="inline-flex items-center gap-1.5 rounded bg-primary text-primary-foreground px-3 py-1.5 text-xs font-semibold hover:bg-primary/95 transition-colors disabled:opacity-50"
          >
            {isGenerating ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Sparkles className="h-3.5 w-3.5" />
            )}
            <span>{insight ? 'Regenerate' : 'Generate Insights'}</span>
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-16 text-center border border-border bg-card rounded-lg shadow-sm">
          <AlertTriangle className="h-10 w-10 text-yellow-500 mb-2" />
          <h4 className="font-semibold">Failed to Load AI Insights</h4>
          <p className="text-xs text-muted-foreground max-w-md mt-1">
            Ensure the backend AI settings are configured correctly and try again.
          </p>
        </div>
      ) : !insight && !isGenerating ? (
        <div className="flex flex-col items-center justify-center py-16 text-center border-2 border-dashed border-border rounded-lg bg-card shadow-sm">
          <BrainCircuit className="h-12 w-12 text-primary mb-3" />
          <h4 className="font-semibold text-foreground">No AI Insights Found</h4>
          <p className="text-xs text-muted-foreground max-w-sm mt-1 mb-4">
            No cached commentary exists for this dataset. Click the button above to generate LLM insights.
          </p>
          <button
            onClick={() => generateMutation.mutate()}
            className="inline-flex items-center gap-1.5 rounded bg-primary text-primary-foreground px-4 py-2 text-xs font-semibold hover:bg-primary/95 transition-colors"
          >
            <Sparkles className="h-4 w-4" />
            <span>Generate First Insight</span>
          </button>
        </div>
      ) : isGenerating ? (
        <div className="flex flex-col items-center justify-center py-20 text-center border border-border bg-card rounded-lg shadow-sm space-y-4">
          <RefreshCw className="h-10 w-10 text-primary animate-spin" />
          <h4 className="font-semibold">Synthesizing Analytical Context...</h4>
          <p className="text-xs text-muted-foreground max-w-sm">
            RiskLens is gathering credit risk distributions, HHI indices, and DPD delinquency days to formulate explainable insights.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Main summary card */}
          <div className="lg:col-span-2 space-y-6">
            <div className="rounded-lg border border-border bg-card p-6 shadow-sm space-y-4">
              <div className="flex items-center gap-2 text-primary font-semibold border-b border-border pb-3">
                <FileText className="h-5 w-5" />
                <h3 className="text-base font-bold">Executive Risk Summary</h3>
              </div>
              <p className="text-sm leading-relaxed text-foreground/90 whitespace-pre-line">
                {insight.executive_summary}
              </p>
            </div>

            {/* Recommendations card */}
            <div className="rounded-lg border border-border bg-card p-6 shadow-sm space-y-4">
              <div className="flex items-center gap-2 text-emerald-500 font-semibold border-b border-border pb-3">
                <Lightbulb className="h-5 w-5" />
                <h3 className="text-base font-bold">Strategic Recommendations</h3>
              </div>
              <ul className="space-y-3">
                {insight.recommendations?.map((rec: string, idx: number) => (
                  <li key={idx} className="flex gap-2.5 text-sm text-foreground/90 leading-normal">
                    <CheckCircle className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                    <span>{rec}</span>
                  </li>
                ))}
                {(!insight.recommendations || insight.recommendations.length === 0) && (
                  <li className="text-xs text-muted-foreground italic">No recommendations provided.</li>
                )}
              </ul>
            </div>
          </div>

          {/* Key findings and risk observations sidebar */}
          <div className="space-y-6">
            {/* Key Findings */}
            <div className="rounded-lg border border-border bg-card p-6 shadow-sm space-y-4">
              <div className="flex items-center gap-2 text-indigo-500 font-semibold border-b border-border pb-3">
                <TrendingUp className="h-5 w-5" />
                <h3 className="text-base font-bold">Key Findings</h3>
              </div>
              <ul className="space-y-3">
                {insight.key_findings?.map((find: string, idx: number) => (
                  <li key={idx} className="flex gap-2 text-sm text-foreground/90">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-500/10 text-indigo-500 text-xs font-bold mt-0.5">
                      {idx + 1}
                    </span>
                    <span>{find}</span>
                  </li>
                ))}
                {(!insight.key_findings || insight.key_findings.length === 0) && (
                  <li className="text-xs text-muted-foreground italic">No key findings logged.</li>
                )}
              </ul>
            </div>

            {/* Risk Observations */}
            <div className="rounded-lg border border-border bg-card p-6 shadow-sm space-y-4">
              <div className="flex items-center gap-2 text-rose-500 font-semibold border-b border-border pb-3">
                <ShieldCheck className="h-5 w-5" />
                <h3 className="text-base font-bold">Governance Observations</h3>
              </div>
              <ul className="space-y-3">
                {insight.risk_observations?.map((obs: string, idx: number) => (
                  <li key={idx} className="flex gap-2.5 text-sm text-foreground/90">
                    <AlertTriangle className="h-4 w-4 text-rose-500 shrink-0 mt-0.5" />
                    <span>{obs}</span>
                  </li>
                ))}
                {(!insight.risk_observations || insight.risk_observations.length === 0) && (
                  <li className="text-xs text-muted-foreground italic">No risk observations flagged.</li>
                )}
              </ul>
            </div>

            {/* Metadata info */}
            <div className="rounded-lg border border-border bg-card/50 p-4 text-[10px] text-muted-foreground space-y-1">
              <div><strong>AI Provider:</strong> {insight.provider}</div>
              <div><strong>LLM Model:</strong> {insight.model_name}</div>
              <div><strong>Generated At:</strong> {new Date(insight.created_at).toLocaleString()}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default AIInsightsPage;
