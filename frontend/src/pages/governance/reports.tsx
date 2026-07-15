import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { DatasetSelector } from '@/components/dataset-selector';
import {
  FileText,
  Download,
  Calendar,
  FileSpreadsheet,
  AlertTriangle,
  Play,
  CheckCircle,
  Clock,
  RefreshCw,
  Plus
} from 'lucide-react';
import { EmptyState } from '@/components/empty-state';

export const ReportsPage = () => {
  const queryClient = useQueryClient();
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>(() => {
    return localStorage.getItem('selected_dataset_id') || '';
  });

  const [reportType, setReportType] = useState<'CREDIT_RISK_REPORT' | 'PORTFOLIO_REPORT'>('PORTFOLIO_REPORT');
  const [exportFormat, setExportFormat] = useState<'PDF' | 'XLSX'>('PDF');

  const handleDatasetChange = (id: string) => {
    setSelectedDatasetId(id);
  };

  // 1. Fetch Generated Reports List
  const { data: reportsData, isLoading, error, refetch } = useQuery({
    queryKey: ['reports-list', selectedDatasetId],
    queryFn: async () => {
      if (!selectedDatasetId) return { items: [] };
      const res = await apiClient.get('/reports', {
        params: { dataset_id: selectedDatasetId }
      });
      return res.data;
    },
    enabled: !!selectedDatasetId,
  });

  // 2. Generate Report Mutation
  const generateMutation = useMutation({
    mutationFn: async () => {
      const defaultTitle = reportType === 'PORTFOLIO_REPORT'
        ? 'Portfolio Performance Report'
        : 'Credit Risk Assessment Report';
      return await apiClient.post('/reports/generate', {
        dataset_id: selectedDatasetId,
        report_type: reportType,
        title: defaultTitle,
        export_format: exportFormat,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports-list', selectedDatasetId] });
      refetch();
    },
    onError: (err: any) => {
      alert(err.message || 'Failed to generate compliance report.');
    }
  });

  const handleDownload = (reportId: string) => {
    window.open(`/api/v1/reports/${reportId}/download`, '_blank');
  };

  const getFormatBadge = (format: string) => {
    const uppercase = format?.toUpperCase();
    if (uppercase === 'PDF') {
      return 'bg-red-500/10 text-red-500 border-red-500/20';
    }
    if (uppercase === 'XLSX') {
      return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20';
    }
    return 'bg-slate-500/10 text-slate-500 border-slate-500/20';
  };

  if (!selectedDatasetId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <h2 className="text-2xl font-bold tracking-tight">Analytics Reports Compilation</h2>
          <DatasetSelector selectedId={selectedDatasetId} onSelect={handleDatasetChange} />
        </div>
        <EmptyState
          title="No Structured Dataset Selected"
          description="Choose an active credit portfolio catalog from the selector at the top right to start reports compilation."
          icon={FileSpreadsheet}
          variant="dashed"
        />
      </div>
    );
  }

  const isCompiling = generateMutation.isPending;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Analytics Reports Compilation</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Compile, monitor, and export PDF or Excel compliance reports of portfolio credit risk assessments.
          </p>
        </div>
        <DatasetSelector selectedId={selectedDatasetId} onSelect={handleDatasetChange} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Compiler Form card */}
        <div className="rounded-lg border border-border bg-card p-6 shadow-sm h-fit space-y-4">
          <div className="flex items-center gap-2 text-primary font-semibold border-b border-border pb-3">
            <Plus className="h-5 w-5" />
            <h3 className="text-base font-bold">Compile Document</h3>
          </div>

          <div className="space-y-4">
            {/* Report Type Selection */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-muted-foreground uppercase" htmlFor="reportType">
                Report Type
              </label>
              <select
                id="reportType"
                value={reportType}
                onChange={(e: any) => setReportType(e.target.value)}
                className="block w-full rounded-md border border-border bg-card px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary"
              >
                <option value="PORTFOLIO_REPORT">Portfolio Risk Summary</option>
                <option value="CREDIT_RISK_REPORT">Granular Risk Assessment Logs</option>
              </select>
            </div>

            {/* Export Format Selection */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-muted-foreground uppercase" htmlFor="exportFormat">
                Export Format
              </label>
              <select
                id="exportFormat"
                value={exportFormat}
                onChange={(e: any) => setExportFormat(e.target.value)}
                className="block w-full rounded-md border border-border bg-card px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary"
              >
                <option value="PDF">Acrobat PDF (.pdf)</option>
                <option value="XLSX">Excel Spreadsheet (.xlsx)</option>
              </select>
            </div>

            {/* Compile trigger */}
            <button
              onClick={() => generateMutation.mutate()}
              disabled={isCompiling}
              className="inline-flex w-full items-center justify-center gap-1.5 rounded bg-primary text-primary-foreground py-2 text-sm font-semibold hover:bg-primary/95 transition-colors disabled:opacity-50"
            >
              {isCompiling ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              <span>{isCompiling ? 'Compiling Assessment...' : 'Compile Document'}</span>
            </button>
          </div>
        </div>

        {/* Generated list column */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-foreground">Document Register</h3>
          </div>

          {isLoading ? (
            <div className="flex h-48 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
          ) : error ? (
            <div className="rounded border border-destructive/20 bg-destructive/10 p-4 text-destructive text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              <span>Failed to load reports register for this dataset.</span>
            </div>
          ) : reportsData?.items?.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center border border-border bg-card rounded-lg shadow-2xs">
              <Clock className="h-10 w-10 text-muted-foreground mb-2" />
              <h4 className="font-semibold text-sm">No Compiled Documents</h4>
              <p className="text-xs text-muted-foreground max-w-xs mt-1">
                Configure your document settings on the left side and click compile to output reports.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-border bg-card shadow-sm">
              <table className="w-full text-left border-collapse" aria-label="Governance Reports">
                <thead>
                  <tr className="border-b border-border bg-muted/40 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    <th className="px-5 py-3">Report Title</th>
                    <th className="px-5 py-3">Format</th>
                    <th className="px-5 py-3">Created At</th>
                    <th className="px-5 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="text-xs divide-y divide-border">
                  {reportsData.items.map((report: any) => (
                    <tr key={report.id} className="hover:bg-muted/10 transition-colors">
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-primary" />
                          <span className="font-semibold">{report.title}</span>
                        </div>
                      </td>
                      <td className="px-5 py-3.5">
                        <span className={`inline-flex rounded border px-2 py-0.5 text-[10px] font-black ${getFormatBadge(report.export_format)}`}>
                          {report.export_format}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-muted-foreground">
                        {new Date(report.created_at).toLocaleString()}
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <button
                          onClick={() => handleDownload(report.id)}
                          className="inline-flex items-center gap-1 rounded border border-primary/20 text-primary bg-primary/5 px-2 py-1 hover:bg-primary hover:text-primary-foreground transition-colors"
                        >
                          <Download className="h-3 w-3" />
                          <span>Download</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default ReportsPage;
