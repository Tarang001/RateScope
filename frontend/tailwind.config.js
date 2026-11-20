/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["IBM Plex Sans", "ui-sans-serif", "system-ui"],
      },
      colors: {
        ink: {
          950: "#07111f",
          900: "#0c1b2e",
          800: "#13263f",
        },
        brand: {
          400: "#2dd4bf",
          500: "#14b8a6",
          600: "#0f766e",
        },
      },
    },
  },
  plugins: [],
};
