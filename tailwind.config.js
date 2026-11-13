const t = require("daisyui/src/theming/themes");
// 配色: night=「深宇宙の観測デッキ」(シアン→バイオレットの光)、nord=「昼の設計図」。
// 文字と背景のコントラストは 4.5:1 以上(tests の axe で両テーマを確認)。pages/palette.json の theme と色をそろえる。
module.exports = {
  content: ["./site/**/*.html"],
  plugins: [require("daisyui")],
  daisyui: {
    themes: [
      {
        night: {
          ...t["night"],
          primary: "#56e0ff",
          "primary-content": "#04121c",
          secondary: "#9b8cff",
          "secondary-content": "#0a0820",
          accent: "#ffb86b",
          "accent-content": "#1c1004",
          "base-100": "#0b1026",
          "base-200": "#050816",
          "base-300": "#1f2a4d",
          "base-content": "#e7ecff",
          "--rounded-box": "0.875rem",
        },
      },
      {
        nord: {
          ...t["nord"],
          primary: "#2747c7",
          "primary-content": "#ffffff",
          secondary: "#6d3fd6",
          "secondary-content": "#ffffff",
          accent: "#b45309",
          "base-100": "#ffffff",
          "base-200": "#eef1f8",
          "base-300": "#d5dcec",
          "base-content": "#151b33",
          "--rounded-box": "0.875rem",
        },
      },
    ],
    darkTheme: "night",
  },
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Noto Sans JP"', "system-ui", "sans-serif"],
        // 見出しと数字: 英数字は Oxanium、かな・漢字は M PLUS 1
        display: ["Oxanium", '"M PLUS 1"', '"Noto Sans JP"', "system-ui", "sans-serif"],
      },
    },
  },
};
