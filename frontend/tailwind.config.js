/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#09090b",
        surface: "#121215",
        surfaceHover: "#18181c",
        card: "#141418",
        border: "#27272a",
        borderSubtle: "#1f1f23",
        textPrimary: "#f4f4f5",
        textSecondary: "#a1a1aa",
        textMuted: "#71717a",
        accent: "#6366f1",
        accentHover: "#4f46e5",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "'Segoe UI'",
          "Roboto",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
        mono: [
          "'SFMono-Regular'",
          "Consolas",
          "'Liberation Mono'",
          "Menlo",
          "Courier",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
}
