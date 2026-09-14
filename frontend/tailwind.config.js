/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bento: {
          border: 'rgba(0, 0, 0, 0.1)',
          borderDark: 'rgba(255, 255, 255, 0.1)',
          surface: 'rgba(255, 255, 255, 0.75)',
          surfaceDark: 'rgba(11, 13, 19, 0.78)',
        },
        neon: {
          cyan: '#00f0ff',
          magenta: '#ff007f',
          amber: '#ffb703',
          emerald: '#00ff9f',
          purple: '#9d4edd',
          rose: '#ff0055',
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Outfit', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
    },
  },
  plugins: [],
};
