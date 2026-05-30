/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // ── Luxury Gold Palette ──
        primary: {
          DEFAULT: '#C9A96E',
          light:   '#DFC08A',
          dark:    '#A8874D',
        },
        accent: {
          DEFAULT: '#EDE0D4',
          muted:   '#D4C4B0',
        },
        // ── Dark Backgrounds ──
        bg: {
          DEFAULT: '#0F172A',
          card:    '#1E293B',
          elevated:'#263548',
        },
        // ── Text ──
        content: {
          DEFAULT: '#F8F5F0',
          muted:   '#94A3B8',
          subtle:  '#64748B',
        },
        // ── Status ──
        success: '#22C55E',
        warning: '#F59E0B',
        danger:  '#EF4444',
        info:    '#3B82F6',
      },
      fontFamily: {
        ar:       ['Cairo', 'Tajawal', 'sans-serif'],
        en:       ['Inter', 'sans-serif'],
        'title-ar': ['Amiri', 'serif'],
        'title-en': ['Playfair Display', 'serif'],
      },
      borderRadius: {
        sm:  '6px',
        md:  '12px',
        lg:  '20px',
        xl:  '32px',
      },
      boxShadow: {
        gold:   '0 0 30px rgba(201, 169, 110, 0.15)',
        card:   '0 4px 24px rgba(0,0,0,0.35)',
        glow:   '0 0 60px rgba(201, 169, 110, 0.08)',
        inset:  'inset 0 1px 0 rgba(255,255,255,0.05)',
      },
      backgroundImage: {
        'gradient-gold':    'linear-gradient(135deg, #C9A96E, #EDE0D4)',
        'gradient-surface': 'linear-gradient(180deg, #1E293B, #0F172A)',
        'gradient-card':    'linear-gradient(145deg, rgba(30,41,59,0.8), rgba(15,23,42,0.9))',
      },
      backdropBlur: {
        glass: '12px',
      },
    },
  },
  plugins: [],
}
