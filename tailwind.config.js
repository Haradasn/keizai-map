const t=require("daisyui/src/theming/themes");
module.exports={content:["./site/**/*.html"],plugins:[require("daisyui")],
daisyui:{themes:[{night:{...t["night"],"base-200":"#0b1120","base-300":"#1e293b","base-content":"#e2e8f0"}},
// nord は文字と primary を少し濃くする(背景とのコントラスト 4.5:1 以上。tests の axe で確認)
{nord:{...t["nord"],"base-content":"#1f2430",primary:"#3f6390"}}],darkTheme:"night"},
theme:{extend:{fontFamily:{sans:['"Noto Sans JP"','system-ui','sans-serif']}}}}
