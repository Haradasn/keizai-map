// 別の <script> で読み込まれるグローバルの宣言（型チェック用。実行時には何も出力されない）。
// ベンダーライブラリ(maplibregl / ForceGraph3D)、生成データ(pref-map-data.js の PREF_MAP、net-mini.js の NET_MINI)、
// Cloudflare Turnstile(turnstile / fbTsReady)をゆるく any で宣言している。
interface Window {
  PREF_MAP: any;
  NET_MINI: any;
  turnstile: any;
  maplibregl: any;
  ForceGraph3D: any;
  fbTsReady: any;
  // 産業マップ(explorer.html のインライン script が置く: 群の色と explorer_data.json)
  XP: { gc: any; data: any };
}
// グラフの共通関数(ビルド時に KA.pal が注入され、charts.js が KA.line などを足す)
declare var KA: any;
declare const maplibregl: any;
declare const turnstile: any;
declare const ForceGraph3D: any;

// Cloudflare Workers だけにある API(worker/index.js の合言葉の比較で使う)
interface SubtleCrypto {
  timingSafeEqual(a: ArrayBuffer | ArrayBufferView, b: ArrayBuffer | ArrayBufferView): boolean;
}
