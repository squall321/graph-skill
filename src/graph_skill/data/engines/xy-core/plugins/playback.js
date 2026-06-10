/* playback — time-driven animation over EMBEDDED frames (deterministic artifact;
   animation is purely client-side replay of inlined data). One plugin powers:
     - mode "bubble"  : Gapminder-style moving/​resizing points (bubble-timeline, MC)
     - mode "trail"   : a marker sweeping a path, leaving a (optionally comet) trail
                        (animated-trajectory / phase-portrait / hysteresis / sweep-cursor)
     - mode "race"    : horizontal bar-chart-race with rank interpolation
   The recipe also emits a style:"none" carrier series so the engine autoscales axes.
   config (pluginConfig.playback): {
     mode, frames:[{t,entities:[{id,x,y,r?,value?,color?,label?}]}], path:[[x,y]],
     times:[...], trail_len?:0, fps?:1.2, loop?:true, palette?:[...], show_time?:true }
*/
(function () {
  "use strict";
  var PAL = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#999999"];
  function cfg(view) { return (view.pluginConfig && view.pluginConfig["playback"]) || null; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }

  function nFrames(c) { return c.mode === "trail" ? (c.path || []).length : (c.frames || []).length; }
  function frameLabel(c, idx) {
    if (c.mode === "trail") { var ts = c.times || []; return ts.length ? String(ts[clamp(idx, 0, ts.length - 1)]) : ("t " + idx); }
    var f = (c.frames || [])[clamp(idx, 0, (c.frames || []).length - 1)];
    return f && f.t != null ? String(f.t) : ("frame " + idx);
  }

  var P = {
    id: "playback",
    order: 60,

    onInit: function (core) {
      var c = (core.opts.pluginConfig && core.opts.pluginConfig["playback"]); if (!c) return;
      var n = nFrames(c), st = core._pstate["playback"] = { f: 0, playing: false, last: 0, n: n, fps: c.fps || 1.2 };

      var bar = document.createElement("div"); bar.className = "gs-playbar";
      var play = document.createElement("button"); play.className = "gs-pb-btn"; play.textContent = "▶";
      play.title = "재생/정지";
      var sld = document.createElement("input"); sld.type = "range"; sld.className = "gs-pb-slider";
      sld.min = "0"; sld.max = String(Math.max(0, n - 1)); sld.step = "any"; sld.value = "0";
      var lab = document.createElement("span"); lab.className = "gs-pb-lab"; lab.textContent = frameLabel(c, 0);

      function syncLab() { lab.textContent = frameLabel(c, Math.round(st.f)); }
      play.addEventListener("click", function () {
        st.playing = !st.playing;
        if (st.playing && st.f >= n - 1) st.f = 0;
        play.textContent = st.playing ? "❚❚" : "▶"; st.last = 0;
      });
      sld.addEventListener("input", function () {
        st.playing = false; play.textContent = "▶"; st.f = +sld.value; syncLab(); core.render();
      });
      bar.appendChild(play); bar.appendChild(sld); bar.appendChild(lab);
      core.root.appendChild(bar);
      st._sld = sld; st._syncLab = syncLab;

      var raf = window.requestAnimationFrame || function (f) { return setTimeout(function () { f(16); }, 16); };
      function tick(ts) {
        if (st._dead) return;
        if (st.playing) {
          if (!st.last) st.last = ts;
          st.f += (ts - st.last) / 1000 * st.fps;
          st.last = ts;
          if (st.f >= n - 1) {
            if (c.loop !== false) { st.f = 0; }
            else { st.f = n - 1; st.playing = false; play.textContent = "▶"; }
          }
          sld.value = String(st.f); syncLab(); core.render();
        }
        raf(tick);
      }
      raf(tick);
      var od = core.destroy;
      core.destroy = function () { st._dead = true; if (od) od.call(core); };
    },

    onDrawOver: function (ctx, view) {
      var c = cfg(view); if (!c) return;
      var st = view.core._pstate["playback"]; if (!st) return;
      var f = clamp(st.f, 0, Math.max(0, st.n - 1)), i0 = Math.floor(f), i1 = Math.min(i0 + 1, st.n - 1), fr = f - i0;
      var pl = view.plot;
      ctx.save();
      ctx.beginPath(); ctx.rect(pl.left, pl.top, pl.width, pl.height); ctx.clip();

      if (c.mode === "trail") P._trail(ctx, view, c, i0, i1, fr, pl);
      else if (c.mode === "race") P._race(ctx, view, c, i0, i1, fr, pl);
      else P._bubble(ctx, view, c, i0, i1, fr);

      ctx.restore();
      if (c.show_time !== false) {                       // faint year/time watermark
        ctx.save();
        ctx.font = "700 30px Segoe UI, system-ui, sans-serif";
        ctx.fillStyle = view.theme.sub || "#9aa3af"; ctx.globalAlpha = 0.32;
        ctx.textAlign = "right"; ctx.textBaseline = "bottom";
        ctx.fillText(frameLabel(c, Math.round(f)), pl.left + pl.width - 8, pl.top + pl.height - 6);
        ctx.restore();
      }
    },

    _bubble: function (ctx, view, c, i0, i1, fr) {
      var A = (c.frames[i0] || {}).entities || [], B = (c.frames[i1] || {}).entities || [];
      var bm = {}; B.forEach(function (e) { bm[e.id] = e; });
      var am = {}; A.forEach(function (e) { am[e.id] = e; });
      var ids = {}; A.forEach(function (e) { ids[e.id] = 1; }); B.forEach(function (e) { ids[e.id] = 1; });
      var keys = Object.keys(ids), k, pi = 0;
      for (k = 0; k < keys.length; k++) {
        var a = am[keys[k]], b = bm[keys[k]], e = a || b, idx = pi++;
        var x = lerp((a || b).x, (b || a).x, fr), y = lerp((a || b).y, (b || a).y, fr);
        var r = lerp((a || b).r != null ? (a || b).r : 10, (b || a).r != null ? (b || a).r : 10, fr);
        var col = e.color || c.palette && c.palette[idx % c.palette.length] || PAL[idx % PAL.length];
        var px = view.scaleX(x), py = view.scaleY(y);
        ctx.beginPath(); ctx.arc(px, py, Math.max(2, r), 0, 6.2832);
        ctx.globalAlpha = 0.55; ctx.fillStyle = col; ctx.fill();
        ctx.globalAlpha = 1; ctx.lineWidth = 1.2; ctx.strokeStyle = col; ctx.stroke();
        if (e.label && r >= 9) {
          ctx.globalAlpha = 1; ctx.fillStyle = view.theme.fg; ctx.font = "11px Segoe UI, system-ui, sans-serif";
          ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(e.label, px, py);
        }
      }
      ctx.globalAlpha = 1;
    },

    _trail: function (ctx, view, c, i0, i1, fr, pl) {
      var path = c.path || []; if (path.length < 2) return;
      var headX = lerp(path[i0][0], path[i1][0], fr), headY = lerp(path[i0][1], path[i1][1], fr);
      var start = c.trail_len ? Math.max(0, i0 - c.trail_len) : 0;
      ctx.lineWidth = 2; ctx.lineJoin = "round"; ctx.lineCap = "round";
      ctx.strokeStyle = view.theme.accent;
      ctx.beginPath();
      ctx.moveTo(view.scaleX(path[start][0]), view.scaleY(path[start][1]));
      for (var k = start + 1; k <= i0; k++) ctx.lineTo(view.scaleX(path[k][0]), view.scaleY(path[k][1]));
      ctx.lineTo(view.scaleX(headX), view.scaleY(headY));
      ctx.stroke();
      var hx = view.scaleX(headX), hy = view.scaleY(headY);
      ctx.beginPath(); ctx.arc(hx, hy, 5, 0, 6.2832); ctx.fillStyle = view.theme.accent; ctx.fill();
      ctx.lineWidth = 2; ctx.strokeStyle = view.theme.bg || "#fff"; ctx.stroke();
    },

    _race: function (ctx, view, c, i0, i1, fr, pl) {
      var A = (c.frames[i0] || {}).entities || [], B = (c.frames[i1] || {}).entities || [];
      var bm = {}; B.forEach(function (e) { bm[e.id] = e; });
      var merged = A.map(function (a) {
        var b = bm[a.id] || a; return { id: a.id, label: a.label || a.id, color: a.color, value: lerp(a.value || 0, b.value || 0, fr) };
      });
      merged.sort(function (p, q) { return q.value - p.value; });
      var top = merged.slice(0, c.top || 12);
      var maxV = 1; top.forEach(function (e) { maxV = Math.max(maxV, e.value); });
      var slotH = pl.height / top.length, barH = Math.min(slotH * 0.7, 34), x0 = view.scaleX(0);
      for (var k = 0; k < top.length; k++) {
        var e = top[k], y = pl.top + slotH * k + (slotH - barH) / 2;
        var w = (view.scaleX(e.value) - x0);
        var col = e.color || PAL[k % PAL.length];
        ctx.fillStyle = col; ctx.globalAlpha = 0.85; ctx.fillRect(x0, y, Math.max(0, w), barH); ctx.globalAlpha = 1;
        ctx.fillStyle = view.theme.fg; ctx.font = "12px Segoe UI, system-ui, sans-serif";
        ctx.textAlign = "left"; ctx.textBaseline = "middle"; ctx.fillText(" " + e.label, x0 + 4, y + barH / 2);
        ctx.textAlign = "right"; ctx.fillText(view.fmt(e.value) + " ", x0 + Math.max(0, w) - 2, y + barH / 2);
      }
    },

    onHover: function (view, cursor) {
      var c = cfg(view); if (!c || !cursor) return null;
      var st = view.core._pstate["playback"]; if (!st) return null;
      return { hud: frameLabel(c, Math.round(st.f)) };
    }
  };

  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"]["playback"] = P;
})();
