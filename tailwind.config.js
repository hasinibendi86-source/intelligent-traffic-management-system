/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        panel: "#111827",
        panel2: "#1a2333",
        surface: "#0b1120",
        border: "#232f45",
        accent: "#38bdf8",
        low: "#22c55e",
        medium: "#eab308",
        high: "#ef4444",
      },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,0.4)",
      },
    },
  },
  plugins: [],
};
