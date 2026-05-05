/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        karnataka: { red: '#CC0000', yellow: '#FFD700', blue: '#003399' },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'recording':  'recording 1.5s ease-in-out infinite',
      },
      keyframes: {
        recording: {
          '0%, 100%': { transform: 'scale(1)', opacity: '1' },
          '50%':      { transform: 'scale(1.15)', opacity: '0.7' },
        }
      }
    },
  },
  plugins: [],
}
