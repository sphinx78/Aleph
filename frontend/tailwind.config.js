/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        sage: {
          DEFAULT: '#99B29B',
          50: '#F5F7F5',
          100: '#EAEEEC',
          200: '#CCD8CE',
          300: '#99B29B', // Main Sage
          400: '#7B9B7E',
          500: '#5F7F62',
          800: '#2E3F2F',
        },
        sand: {
          DEFAULT: '#FAF7F2',
          50: '#FDFCFB',
          100: '#FAF7F2', // Main Warm Sand
          200: '#EAE1D4', // Accent Warm Grey/Sand
          300: '#D6C8B5',
          400: '#A3917A',
          800: '#6B6864', // Text sand grey
        },
        clay: {
          DEFAULT: '#C07A50', // Clay / Terracotta
          50: '#FBF5F1',
          100: '#F6E6DC',
          300: '#E2B193',
          500: '#C07A50',
          800: '#7E4C2E',
        },
        charcoal: {
          DEFAULT: '#2D2D2D',
          light: '#6B6864',
          dark: '#1A1A1A',
        }
      },
      fontFamily: {
        sans: ['Inter', 'Outfit', 'sans-serif'],
        serif: ['Playfair Display', 'Georgia', 'serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      scale: {
        '102': '1.02',
      }
    },
  },
  plugins: [],
}
