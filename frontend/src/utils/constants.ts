export const VIOLATION_TYPES: Record<string, { label: string; fine: string; color: string }> = {
  NO_HELMET: { label: 'No Helmet', fine: '₹1,000', color: '#ef4444' },
  NO_SEATBELT: { label: 'No Seatbelt', fine: '₹500', color: '#eab308' },
  TRIPLE_RIDING: { label: 'Triple Riding', fine: '₹2,000', color: '#a855f7' },
  WRONG_SIDE: { label: 'Wrong Side', fine: '₹1,500', color: '#ec4899' },
  RED_LIGHT: { label: 'Red Light', fine: '₹5,000', color: '#ef4444' },
  STOP_LINE: { label: 'Stop Line', fine: '₹1,000', color: '#06b6d4' },
  ILLEGAL_PARKING: { label: 'Illegal Parking', fine: '₹500', color: '#eab308' },
};

export const NEON_COLORS = ['#a855f7', '#06b6d4', '#ec4899', '#22c55e', '#eab308', '#ef4444'];
