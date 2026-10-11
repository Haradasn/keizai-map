module.exports={content:["./site/**/*.html"],plugins:[require("daisyui")],
daisyui:{themes:[{light:{...require("daisyui/src/theming/themes")["light"],primary:"#1f5fd1","base-100":"#ffffff","base-200":"#f4f5f7"}},
{dark:{...require("daisyui/src/theming/themes")["dark"],primary:"#6aa3ff","base-100":"#141923","base-content":"#e8ecf4","base-200":"#0c0f15","base-300":"#262e3d"}}],darkTheme:"dark"},
theme:{extend:{fontFamily:{sans:['"Noto Sans JP"','system-ui','sans-serif']}}}}
