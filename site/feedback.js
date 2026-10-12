/* 読者の反応(👍と要望)。送り先は同じサイトの /api/*(Cloudflare Worker + D1)。個人を特定できる情報は送らない。 */
(function () {
  var box = document.getElementById("fb");
  if (!box) return;
  var page = location.pathname.replace(/\.html$/, "").replace(/\/index$/, "/") || "/";
  var like = /** @type {HTMLButtonElement} */ (document.getElementById("fb-like")),
    lm = document.getElementById("fb-like-msg"),
    KEY = "fb-like:" + page;
  function done() {
    like.disabled = true;
    like.textContent = "👍 ありがとうございます";
  }
  try {
    if (localStorage.getItem(KEY)) done();
  } catch (e) {}
  like.addEventListener("click", function () {
    like.disabled = true;
    fetch("/api/like", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ page: page }),
    })
      .then(function (r) {
        if (!r.ok) throw 0;
        done();
        try {
          localStorage.setItem(KEY, "1");
        } catch (e) {}
        lm.textContent = "励みになります。";
      })
      .catch(function () {
        like.disabled = false;
        lm.textContent = "送信できませんでした。時間をおいてお試しください。";
      });
  });
  var det = /** @type {HTMLDetailsElement} */ (document.getElementById("fb-req")),
    form = document.getElementById("fb-form"),
    msg = document.getElementById("fb-msg"),
    wid = null,
    key = box.getAttribute("data-sitekey");
  function loadTs() {
    // ロボット判定(Turnstile)は、入力欄を開いたときに初めて読み込む
    if (window.turnstile || document.getElementById("ts-js")) {
      render();
      return;
    }
    window.fbTsReady = render;
    var s = document.createElement("script");
    s.id = "ts-js";
    s.async = true;
    s.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=fbTsReady";
    document.head.appendChild(s);
  }
  function render() {
    if (wid === null && window.turnstile)
      wid = turnstile.render("#fb-ts", {
        sitekey: key,
        size: "flexible",
        theme: document.documentElement.dataset.theme === "nord" ? "light" : "dark",
      });
  }
  det.addEventListener("toggle", function () {
    if (det.open) loadTs();
  });
  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var body = /** @type {HTMLTextAreaElement} */ (document.getElementById("fb-body")).value.trim();
    if (body.length < 2) {
      msg.textContent = "内容を書いてください。";
      return;
    }
    var token = window.turnstile && wid !== null ? turnstile.getResponse(wid) : "";
    if (!token) {
      msg.textContent = "確認の完了をお待ちください（数秒かかることがあります）。";
      return;
    }
    msg.textContent = "送信しています…";
    fetch("/api/request", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ page: page, body: body, token: token }),
    })
      .then(function (r) {
        if (!r.ok) throw 0;
        form.innerHTML =
          '<p class="text-sm">受け取りました。ありがとうございます。今後の更新の参考にします。</p>';
      })
      .catch(function () {
        msg.textContent = "送信できませんでした。時間をおいてお試しください。";
        if (window.turnstile) turnstile.reset(wid);
      });
  });
})();
