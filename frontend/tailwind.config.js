/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          25: '#f5f3ff',
          50: '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
          950: '#1e1b4b'
        },
        accent: {
          success: '#10b981',
          successSoft: '#d1fae5',
          warning: '#f59e0b',
          warningSoft: '#fef3c7',
          danger: '#ef4444',
          dangerSoft: '#fee2e2',
          info: '#3b82f6',
          infoSoft: '#dbeafe'
        },
        surface: {
          0: '#ffffff',
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Plus Jakarta Sans', 'Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace']
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem', letterSpacing: '0.02em' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem', letterSpacing: '-0.02em' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem', letterSpacing: '-0.02em' }],
        '5xl': ['3rem', { lineHeight: '1.1', letterSpacing: '-0.03em' }]
      },
      borderRadius: {
        '2xs': '0.25rem',
        xs: '0.375rem',
        sm: '0.5rem',
        md: '0.625rem',
        lg: '0.75rem',
        xl: '1rem',
        '2xl': '1.25rem',
        '3xl': '1.5rem'
      },
      boxShadow: {
        xs: '0 1px 2px 0 rgb(0 0 0 / 0.04)',
        sm: '0 1px 3px 0 rgb(0 0 0 / 0.08), 0 1px 2px -1px rgb(0 0 0 / 0.08)',
        md: '0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.08)',
        lg: '0 10px 15px -3px rgb(0 0 0 / 0.08), 0 4px 6px -4px rgb(0 0 0 / 0.08)',
        xl: '0 20px 25px -5px rgb(0 0 0 / 0.08), 0 8px 10px -6px rgb(0 0 0 / 0.08)',
        '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.18)',
        inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.04)',
        glow: '0 0 0 3px rgba(99, 102, 241, 0.15)',
        'glow-success': '0 0 0 3px rgba(16, 185, 129, 0.18)',
        'glow-danger': '0 0 0 3px rgba(239, 68, 68, 0.15)',
        'glow-warning': '0 0 0 3px rgba(245, 158, 11, 0.18)',
        'soft-hover': '0 8px 24px -6px rgb(0 0 0 / 0.12)'
      },
      transitionTimingFunction: {
        'out-expo': 'cubic-bezier(0.16, 1, 0.3, 1)',
        'in-out-expo': 'cubic-bezier(0.87, 0, 0.13, 1)',
        'bounce-soft': 'cubic-bezier(0.34, 1.56, 0.64, 1)'
      },
      transitionDuration: {
        150: '150ms',
        200: '200ms',
        250: '250ms',
        300: '300ms',
        400: '400ms',
        500: '500ms'
      },
      keyframes: {
        'loading-bar': {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(400%)' }
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        'fade-out': {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' }
        },
        'scale-in': {
          '0%': { opacity: '0', transform: 'scale(0.96)' },
          '100%': { opacity: '1', transform: 'scale(1)' }
        },
        'scale-out': {
          '0%': { opacity: '1', transform: 'scale(1)' },
          '100%': { opacity: '0', transform: 'scale(0.96)' }
        },
        'slide-up': {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        },
        'slide-down': {
          '0%': { opacity: '0', transform: 'translateY(-12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        },
        'slide-in-right': {
          '0%': { opacity: '0', transform: 'translateX(20px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' }
        },
        'slide-out-right': {
          '0%': { opacity: '1', transform: 'translateX(0)' },
          '100%': { opacity: '0', transform: 'translateX(20px)' }
        },
        shimmer: {
          '0%': { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' }
        },
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(99, 102, 241, 0.25)' },
          '50%': { boxShadow: '0 0 0 8px rgba(99, 102, 241, 0)' }
        },
        'bounce-subtle': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-3px)' }
        },
        'spin-slow': {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' }
        },
        'check-pop': {
          '0%': { transform: 'scale(0)', opacity: '0' },
          '70%': { transform: 'scale(1.15)' },
          '100%': { transform: 'scale(1)', opacity: '1' }
        }
      },
      animation: {
        'loading-bar': 'loading-bar 1.5s ease-in-out infinite',
        'fade-in': 'fade-in 200ms ease-out forwards',
        'fade-out': 'fade-out 150ms ease-in forwards',
        'scale-in': 'scale-in 200ms cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'scale-out': 'scale-out 150ms ease-in forwards',
        'slide-up': 'slide-up 250ms cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'slide-down': 'slide-down 250ms cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'slide-in-right': 'slide-in-right 250ms cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'slide-out-right': 'slide-out-right 200ms ease-in forwards',
        shimmer: 'shimmer 1.5s infinite linear',
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'bounce-subtle': 'bounce-subtle 2s ease-in-out infinite',
        'spin-slow': 'spin-slow 3s linear infinite',
        'check-pop': 'check-pop 300ms cubic-bezier(0.34, 1.56, 0.64, 1) forwards'
      }
    }
  },
  plugins: [
    function ({ addBase, addUtilities, theme }) {
      addBase({
        ':root': {
          '--color-brand-600': theme('colors.brand.600'),
          '--color-brand-500': theme('colors.brand.500'),
          '--color-success': theme('colors.accent.success'),
          '--color-danger': theme('colors.accent.danger'),
          '--color-warning': theme('colors.accent.warning'),
          '--radius-card': theme('borderRadius.xl'),
          '--shadow-card': theme('boxShadow.md'),
          '--transition-fast': theme('transitionDuration.150'),
          '--transition-base': theme('transitionDuration.200'),
          '--transition-slow': theme('transitionDuration.300')
        }
      })
      addUtilities({
        '.text-balance': { textWrap: 'balance' },
        '.scrollbar-stable': { scrollbarGutter: 'stable both-edges' },
        '.gpu': { transform: 'translateZ(0)' }
      })
    }
  ]
}
