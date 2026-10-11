const t=require("daisyui/src/theming/themes");
module.exports={content:["./site/**/*.html"],plugins:[require("daisyui")],
daisyui:{themes:[{night:{...t["night"],"base-200":"#0b1120","base-300":"#1e293b","base-content":"#e2e8f0"}},"nord"],darkTheme:"night"},
theme:{extend:{fontFamily:{sans:['"Noto Sans JP"','system-ui','sans-serif']}}}}
