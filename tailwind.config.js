const t = require("daisyui/src/theming/themes");
// 配色は「地図帳」から取る。面の色=海、パネル=紙、文字=墨、リンク=海の注記の青、選んだもの=朱。
// nord=昼の地図帳(淡い海)、night=夜の海図(深い海)。標高の段彩(緑→黄→黄土→茶)はデータの色で、pages/palette.json の ramp。
// 文字と背景のコントラストは 4.5:1 以上(tests の axe で両テーマを確認)。pages/palette.json の theme と色をそろえる。
module.exports = {
  content: ["./site/**/*.html"],
  plugins: [require("daisyui")],
  daisyui: {
    themes: [
      {
        night: {
          ...t["night"],
          primary: "#8fd0ee",
          "primary-content": "#0a1a26",
          secondary: "#e6b04f",
          "secondary-content": "#1f1503",
          accent: "#ff7355",
          "accent-content": "#2a0a03",
          "base-100": "#132a3b",
          "base-200": "#0d1f2d",
          "base-300": "#2a475c",
          "base-content": "#e9f0f2",
          "--rounded-box": "0.25rem",
          "--rounded-btn": "0.25rem",
          "--rounded-badge": "0.25rem",
        },
      },
      {
        nord: {
          ...t["nord"],
          primary: "#0b5f8f",
          "primary-content": "#ffffff",
          secondary: "#8a5a0b",
          "secondary-content": "#ffffff",
          accent: "#c8361f",
          "accent-content": "#ffffff",
          "base-100": "#fbfcfa",
          "base-200": "#dcebf1",
          "base-300": "#b3c9d3",
          "base-content": "#14232e",
          "--rounded-box": "0.25rem",
          "--rounded-btn": "0.25rem",
          "--rounded-badge": "0.25rem",
        },
      },
    ],
    darkTheme: "night",
  },
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Zen Kaku Gothic New"', '"Noto Sans JP"', "system-ui", "sans-serif"],
        // 見出しと数字: 英数字は Barlow Semi Condensed、かな・漢字は Zen Kaku Gothic New
        display: ['"Barlow Semi Condensed"', '"Zen Kaku Gothic New"', '"Noto Sans JP"', "system-ui", "sans-serif"],
      },
    },
  },
};
