import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import {
  FileText,
  Upload,
  AlertTriangle,
  Plus,
  Link2,
  Calendar,
  Info
} from 'lucide-react';

export const DocumentsPage = () => {
  const queryClient = useQueryClient();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [datasetId, setDatasetId] = useState<string>('');
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Fetch documents list
  const { data: documentData, isLoading: isDocsLoading, error: docsError } = useQuery({
    queryKey: ['documents'],
    queryFn: async () => {
      const res = await apiClient.get('/documents');
      return res.data;
    },
  });

  // Fetch structured datasets (to support linking document to a dataset)
  const { data: datasetData } = useQuery({
    queryKey: ['datasets'],
    queryFn: async () => {
      const res = await apiClient.get('/datasets');
      return res.data;
    },
  });

  // Upload document mutation
  const uploadMutation = useMutation({
    mutationFn: async (formData: FormData) => {
      return await apiClient.post('/documents/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setSuccessMsg('Compliance document uploaded and logged successfully!');
      setSelectedFile(null);
      setDatasetId('');
      setUploadError(null);
      setTimeout(() => {
        setUploadOpen(false);
        setSuccessMsg(null);
      }, 2000);
    },
    onError: (err: any) => {
      setUploadError(err.message || 'Failed to upload document. Verify file type and size.');
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setUploadError(null);
    }
  };

  const handleUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setUploadError('Please select a PDF or DOCX file to upload.');
      return;
    }

    const ext = selectedFile.name.substring(selectedFile.name.lastIndexOf('.')).toLowerCase();
    if (!['.pdf', '.docx'].includes(ext)) {
      setUploadError('Only compliance document formats (.pdf, .docx) are allowed.');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);
    if (datasetId) {
      formData.append('dataset_id', datasetId);
    }

    uploadMutation.mutate(formData);
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">Compliance Document Processing</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Upload policies, regulatory files, or loan portfolios descriptors, and map them to structured datasets.
          </p>
        </div>
        <button
          onClick={() => {
            setUploadOpen(true);
            setUploadError(null);
            setSuccessMsg(null);
          }}
          className="inline-flex items-center gap-2 rounded bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/95 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        >
          <Plus className="h-4 w-4" />
          <span>Upload Document</span>
        </button>
      </div>

      {/* Docs List */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold tracking-tight">Ingested Compliance Documents</h3>

        {docsError && (
          <div className="flex items-center gap-2 rounded border border-destructive/20 bg-destructive/10 p-4 text-destructive">
            <AlertTriangle className="h-5 w-5" />
            <span>Failed to load ingested documents. Ensure the backend api server is running.</span>
          </div>
        )}

        {isDocsLoading ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2].map((n) => (
              <div key={n} className="h-32 rounded-lg border border-border bg-card p-6 animate-pulse space-y-4">
                <div className="h-4 bg-muted rounded w-2/3"></div>
                <div className="h-4 bg-muted rounded w-1/2"></div>
              </div>
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-border bg-card shadow-sm">
            <table className="w-full text-left border-collapse" aria-label="Ingested Compliance Documents">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  <th className="px-6 py-3">Document Details</th>
                  <th className="px-6 py-3">Linked Dataset ID</th>
                  <th className="px-6 py-3">File Size</th>
                  <th className="px-6 py-3">Upload Status</th>
                  <th className="px-6 py-3">Uploaded At</th>
                </tr>
              </thead>
              <tbody className="text-sm divide-y divide-border">
                {documentData?.items?.map((doc: any) => (
                  <tr key={doc.id} className="hover:bg-muted/10 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="rounded bg-primary/10 p-2 text-primary">
                          <FileText className="h-5 w-5" />
                        </div>
                        <div>
                          <div className="font-semibold text-foreground">{doc.original_file_name}</div>
                          <div className="text-2xs text-muted-foreground font-mono uppercase tracking-wider">{doc.document_type} format</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {doc.dataset_id ? (
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/60 rounded-md px-2.5 py-1 border border-border/80 w-fit">
                          <Link2 className="h-3.5 w-3.5 text-primary" />
                          <span className="font-mono text-2xs select-all">{doc.dataset_id}</span>
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground italic">Independent (Unlinked)</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-xs font-mono text-muted-foreground">
                      {formatBytes(doc.file_size_bytes || 0)}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex rounded px-2 py-0.5 text-2xs font-semibold border ${
                          doc.upload_status === 'COMPLETED'
                            ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                            : 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'
                        }`}
                      >
                        {doc.upload_status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-xs text-muted-foreground font-mono">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                        <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                      </div>
                    </td>
                  </tr>
                ))}
                {(documentData?.items?.length === 0 || !documentData?.items) && (
                  <tr>
                    <td colSpan={5} className="text-center py-12">
                      <div className="flex flex-col items-center justify-center space-y-3">
                        <div className="rounded-full bg-muted p-3">
                          <FileText className="h-8 w-8 text-muted-foreground" />
                        </div>
                        <div className="font-semibold text-foreground">No Compliance Documents Uploaded</div>
                        <p className="text-xs text-muted-foreground max-w-sm">
                          Ingest compliance files, regulatory briefs, or risk policy models to run document extraction and benchmarking reports.
                        </p>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Info Card */}
      <div className="rounded-lg border border-border/80 bg-muted/20 p-5 flex gap-3.5 items-start">
        <Info className="h-5 w-5 text-primary shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h4 className="font-semibold text-sm text-foreground">Document Processing & LLM Commentary</h4>
          <p className="text-xs text-muted-foreground leading-relaxed">
            RiskLens utilizes regulatory documents to contextualize credit validation score warnings. In later phases, you'll be able to run automated ratio extraction and generate compliance audit commentaries referencing these policy documents directly.
          </p>
        </div>
      </div>

      {/* Modal: Upload Document */}
      {uploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md bg-card rounded-lg border border-border p-6 shadow-xl animate-scale-in">
            <h3 className="text-lg font-bold text-foreground">Upload Compliance Document</h3>
            <p className="text-xs text-muted-foreground mt-1">
              Upload compliance documents, loan policies, or regulatory checklists (PDF or DOCX).
            </p>

            <form onSubmit={handleUploadSubmit} className="mt-4 space-y-4">
              {uploadError && (
                <div className="rounded border border-destructive/20 bg-destructive/10 p-3 text-xs text-destructive flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>{uploadError}</span>
                </div>
              )}
              {successMsg && (
                <div className="rounded border border-emerald-500/20 bg-emerald-500/10 p-3 text-xs text-emerald-500">
                  {successMsg}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                  Link to Structured Dataset (Optional)
                </label>
                <select
                  value={datasetId}
                  onChange={(e) => setDatasetId(e.target.value)}
                  className="block w-full rounded border border-border bg-transparent px-3 py-2 text-sm text-foreground focus:border-primary focus:ring-1 focus:ring-primary"
                  disabled={uploadMutation.isPending}
                >
                  <option value="" className="bg-card">-- Select Dataset to Link --</option>
                  {datasetData?.items?.filter((ds: any) => !ds.archived_at).map((ds: any) => (
                    <option key={ds.id} value={ds.id} className="bg-card">
                      {ds.name} ({ds.original_file_name})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                  Attach Document
                </label>
                <div className="flex items-center justify-center rounded-lg border-2 border-dashed border-border p-6 hover:bg-muted/10 transition-colors">
                  <div className="text-center space-y-1.5">
                    <Upload className="mx-auto h-8 w-8 text-muted-foreground" />
                    <div className="text-xs text-muted-foreground">
                      <label className="relative cursor-pointer rounded-md font-semibold text-primary focus-within:outline-hidden hover:underline">
                        <span>Upload a file</span>
                        <input
                          type="file"
                          accept=".pdf,.docx"
                          className="sr-only"
                          onChange={handleFileChange}
                          disabled={uploadMutation.isPending}
                        />
                      </label>
                      <span> or drag and drop</span>
                    </div>
                    <p className="text-[10px] text-muted-foreground">PDF or DOCX formats up to 50MB</p>
                    {selectedFile && (
                      <p className="mt-2 text-xs font-medium text-emerald-500 truncate max-w-[280px]">
                        Selected: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                      </p>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-border">
                <button
                  type="button"
                  onClick={() => setUploadOpen(false)}
                  className="rounded border border-border px-4 py-2 text-xs font-semibold hover:bg-muted text-foreground"
                  disabled={uploadMutation.isPending}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploadMutation.isPending}
                  className="rounded bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/90"
                >
                  {uploadMutation.isPending ? 'Uploading...' : 'Ingest Document'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
export default DocumentsPage;
