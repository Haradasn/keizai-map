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
}
declare const maplibregl: any;
declare const turnstile: any;
declare const ForceGraph3D: any;
