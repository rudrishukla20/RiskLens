export const formatCurrencyINR = (val: number | null | undefined, maximumFractionDigits: number = 0): string => {
  if (val === null || val === undefined || isNaN(val)) return '₹0';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits,
  }).format(val);
};

export const formatLabel = (label: string): string => {
  if (!label) return label;
  return label.replace(/\$/g, '₹');
};
