/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./components/**/*.{js,vue,ts}",
    "./layouts/**/*.vue",
    "./pages/**/*.vue",
    "./plugins/**/*.{js,ts}",
    "./app.vue",
    "./error.vue",
  ],
  theme: {
    extend: {
      fontFamily: {
        serif: ['Fraunces', 'Georgia', 'serif'],
        sans: ['"Plus Jakarta Sans"', 'Inter', 'sans-serif'],
        besley: ['Besley', 'serif'],
        schibsted: ['"Schibsted Grotesk"', 'sans-serif'],
      },
      colors: {
        bg: '#F2FFEE',
        surface: '#D4F53C',
        border: 'rgba(13, 43, 34, 0.1)',
        text: '#0D2B22',
        'text-muted': '#2d4a43',
        primary: '#0D2B22',
        'primary-hover': '#1a4d3e',
      }
    },
  },
  plugins: [],
}
