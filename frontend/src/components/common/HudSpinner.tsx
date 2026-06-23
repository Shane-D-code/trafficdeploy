interface HudSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
}

export const HudSpinner: React.FC<HudSpinnerProps> = ({ size = 'md', text }) => {
  const sizes = { sm: 'h-5 w-5', md: 'h-8 w-8', lg: 'h-12 w-12' };

  return (
    <div className="flex flex-col items-center justify-center gap-3 py-8">
      <div className={`${sizes[size]} border border-[#3A434F] border-t-[#A3FF3C] rounded-full animate-spin`} />
      {text && <p className="terminal-line text-[#6B7280] terminal-cursor">{text}...</p>}
    </div>
  );
};
