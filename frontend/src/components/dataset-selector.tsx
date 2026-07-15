import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { Database, AlertCircle } from 'lucide-react';
import { useEffect } from 'react';

interface DatasetSelectorProps {
  selectedId: string;
  onSelect: (id: string) => void;
}

export const DatasetSelector = ({ selectedId, onSelect }: DatasetSelectorProps) => {
  // Query all active datasets
  const { data, isLoading, error } = useQuery({
    queryKey: ['datasets-list'],
    queryFn: async () => {
      const res = await apiClient.get('/datasets');
      return res.data;
    },
  });

  const activeDatasets = data?.items?.filter((ds: any) => !ds.archived_at) || [];

  // Handle auto-selection of first dataset if none selected or if selectedId is stale/archived
  useEffect(() => {
    if (activeDatasets.length > 0) {
      const found = activeDatasets.find((ds: any) => ds.id === selectedId);
      if (!found) {
        const stored = localStorage.getItem('selected_dataset_id');
        const storedFound = activeDatasets.find((ds: any) => ds.id === stored);
        const nextId = storedFound ? storedFound.id : activeDatasets[0].id;
        onSelect(nextId);
        localStorage.setItem('selected_dataset_id', nextId);
      }
    }
  }, [activeDatasets, selectedId, onSelect]);

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = e.target.value;
    onSelect(id);
    localStorage.setItem('selected_dataset_id', id);
  };

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 rounded border border-border bg-card px-3 py-1.5 text-xs animate-pulse">
        <div className="h-4 w-4 bg-muted rounded-full" />
        <div className="h-4 bg-muted rounded w-24" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-destructive bg-destructive/10 border border-destructive/20 rounded px-3 py-1.5">
        <AlertCircle className="h-4 w-4" />
        <span>Sync Error</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary border border-primary/20">
        <Database className="h-4 w-4" />
      </span>
      <select
        value={selectedId || ''}
        onChange={handleChange}
        className="block rounded-md border border-border bg-card px-3 py-1.5 text-xs font-semibold text-foreground focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary shadow-2xs max-w-[240px]"
        aria-label="Select Structured Dataset Catalog"
      >
        {activeDatasets.length === 0 ? (
          <option value="">No Active Datasets</option>
        ) : (
          activeDatasets.map((ds: any) => (
            <option key={ds.id} value={ds.id}>
              {ds.name}
            </option>
          ))
        )}
      </select>
    </div>
  );
};
export default DatasetSelector;
