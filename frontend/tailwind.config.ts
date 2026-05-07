import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17211d",
        line: "#d8ddd9",
        panel: "#f7f8f5",
        accent: "#126a5a",
      },
    },
  },
  plugins: [],
};

export default config;
