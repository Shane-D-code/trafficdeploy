export const HudRadar = () => {
  return (
    <div className="radar">
      <div className="radar-dot" style={{ top: '30%', left: '40%' }} />
      <div className="radar-dot" style={{ top: '60%', left: '65%', opacity: 0.5 }} />
      <div className="radar-dot" style={{ top: '25%', left: '70%', opacity: 0.3 }} />
    </div>
  );
};
