/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        'heading': ['Orbitron', 'Rajdhani', 'sans-serif'],
        'body': ['Rajdhani', 'sans-serif'],
        'mono': ['"IBM Plex Mono"', '"JetBrains Mono"', 'monospace'],
        'terminal': ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        hud: {
          bg: '#0B0F13',
          secondary: '#141A20',
          panel: '#1B232C',
          border: '#3A434F',
          green: '#A3FF3C',
          'green-dim': '#7BFF7B',
          warning: '#FFD43B',
          danger: '#FF5D5D',
          white: '#EAEAEA',
          muted: '#6B7280',
        },
      },
      animation: {
        'scan-line': 'scanLine 2s ease-in-out infinite',
        'pulse-hud': 'pulseHud 2s ease-in-out infinite',
        'blink-dot': 'blinkDot 1.5s step-end infinite',
        'radar-sweep': 'radarSweep 3s linear infinite',
        'typing': 'typing 0.05s steps(1) infinite',
        'fade-in': 'fadeIn 0.4s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'count-up': 'countUp 1s ease-out',
        'bracket-pulse': 'bracketPulse 2s ease-in-out infinite',
        'grid-scroll': 'gridScroll 20s linear infinite',
        'data-feed': 'dataFeed 0.5s ease-out',
      },
      keyframes: {
        scanLine: {
          '0%': { top: '-5%' },
          '100%': { top: '105%' },
        },
        pulseHud: {
          '0%, 100%': { opacity: '0.8' },
          '50%': { opacity: '1' },
        },
        blinkDot: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        radarSweep: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        typing: {
          '0%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(15px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        countUp: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        bracketPulse: {
          '0%, 100%': { opacity: '0.6' },
          '50%': { opacity: '1' },
        },
        gridScroll: {
          '0%': { transform: 'translateY(0)' },
          '100%': { transform: 'translateY(40px)' },
        },
        dataFeed: {
          '0%': { opacity: '0', transform: 'translateX(-10px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
      },
      boxShadow: {
        'hud': '0 0 10px rgba(163, 255, 60, 0.1)',
        'hud-lg': '0 0 20px rgba(163, 255, 60, 0.08)',
        'hud-inner': 'inset 0 0 15px rgba(163, 255, 60, 0.03)',
      },
    },
  },
  plugins: [],
};
