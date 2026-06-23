export function formatConfidence(confidence: number): string {
  return `${(confidence * 100).toFixed(0)}%`;
}

export function formatPlate(plate: string): string {
  return plate.toUpperCase().replace(/[^A-Z0-9]/g, '');
}

export function getFineAmount(type: string): string {
  const fines: Record<string, string> = {
    'NO_HELMET': '₹1,000',
    'NO_SEATBELT': '₹500',
    'TRIPLE_RIDING': '₹2,000',
    'WRONG_SIDE': '₹1,500',
    'RED_LIGHT': '₹5,000',
    'STOP_LINE': '₹1,000',
    'ILLEGAL_PARKING': '₹500',
  };
  return fines[type] || '₹0';
}

export function getConfidenceColor(confidence: number): string {
  if (confidence > 0.8) return '#22c55e';
  if (confidence > 0.6) return '#eab308';
  return '#ef4444';
}

export function formatDateTime(ts: string): string {
  return new Date(ts).toLocaleString();
}

export function formatTime(ts: string): string {
  return new Date(ts).toLocaleTimeString();
}
