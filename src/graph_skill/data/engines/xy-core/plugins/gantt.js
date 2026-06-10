/* gantt — project schedule bars on a date axis. All layout data pre-computed by the recipe
   (dates as epoch DAYS); the plugin draws group bands, task bars + progress fill, milestone
   diamonds, dependency elbows, weekend shading, date ticks, and a client-side TODAY line.
   Uses options.hideAxes + onDrawOutside (labels live in the margins, unclipped).
   config (pluginConfig.gantt): {
     rows:[{name, group?, start, end, progress?(0..1), color?, owner?, milestone?}],
     deps:[[fromIdx,toIdx]], t0, t1, ticks:[{t,label}], weekends?:bool, today?:bool }   */
(function () {
  "use strict";
  var PAL = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#8c564b", "#999999"];
  function cfg(view) { return (view.pluginConfig && view.pluginConfig.gantt) || null; }
  function dayMs() { return 86400000; }
  function todayEpochDay() { var d = new Date(); return Math.floor((Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())) / dayMs()); }
  function fmtDay(t) {
    var d = new Date(t * dayMs());
    return (d.getUTCMonth() + 1) + "/" + d.getUTCDate();
  }

  var P = {
    id: "gantt",
    order: 45,
    onDrawOutside: function (ctx, view) {
      var c = cfg(view); if (!c) return;
      var rows = c.rows || [], n = rows.length; if (!n) return;
      var pl = view.plot, tok = view.theme;
      var yOf = function (i) { return view.scaleY(n - 1 - i); };          // row 0 at top
      var rowH = pl.height / n, barH = Math.min(rowH * 0.62, 22);
      ctx.save();

      // group bands (alternating tint) + group labels
      var gi = -1, gname = null;
      for (var b = 0; b < n; b++) {
        if ((rows[b].group || "") !== gname) { gname = rows[b].group || ""; gi++; }
        if (gi % 2 === 1) {
          ctx.fillStyle = tok.fg; ctx.globalAlpha = 0.045;
          ctx.fillRect(pl.left, yOf(b) - rowH / 2, pl.width, rowH);
          ctx.globalAlpha = 1;
        }
        rows[b]._gi = gi;
      }

      // weekend shading (only useful on short ranges)
      if (c.weekends !== false && (c.t1 - c.t0) <= 130) {
        ctx.fillStyle = tok.sub; ctx.globalAlpha = 0.07;
        for (var d0 = Math.ceil(c.t0); d0 <= Math.floor(c.t1); d0++) {
          var dow = (d0 + 4) % 7;                                          // 0=Sun .. 6=Sat
          if (dow === 0 || dow === 6) {
            var x0 = view.scaleX(d0 - 0.5), x1 = view.scaleX(d0 + 0.5);
            ctx.fillRect(Math.max(pl.left, x0), pl.top, Math.min(x1, pl.left + pl.width) - Math.max(pl.left, x0), pl.height);
          }
        }
        ctx.globalAlpha = 1;
      }

      // date ticks + light verticals
      ctx.font = "10px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "center"; ctx.textBaseline = "top";
      (c.ticks || []).forEach(function (tk) {
        var x = view.scaleX(tk.t); if (x < pl.left - 1 || x > pl.left + pl.width + 1) return;
        ctx.strokeStyle = tok.grid; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(x, pl.top); ctx.lineTo(x, pl.top + pl.height); ctx.stroke();
        ctx.fillStyle = tok.sub; ctx.fillText(tk.label, x, pl.top + pl.height + 4);
      });

      // dependency elbows (drawn under bars)
      ctx.strokeStyle = tok.sub; ctx.lineWidth = 1.2; ctx.globalAlpha = 0.75;
      (c.deps || []).forEach(function (dp) {
        var a = rows[dp[0]], z = rows[dp[1]]; if (!a || !z) return;
        var xa = view.scaleX(a.end), ya = yOf(dp[0]);
        var xz = view.scaleX(z.start), yz = yOf(dp[1]);
        var mid = Math.max(xa + 8, xz - 8);
        ctx.beginPath();
        ctx.moveTo(xa, ya); ctx.lineTo(mid, ya); ctx.lineTo(mid, yz); ctx.lineTo(xz - 4, yz);
        ctx.stroke();
        ctx.beginPath(); ctx.moveTo(xz - 4, yz - 3.5); ctx.lineTo(xz, yz); ctx.lineTo(xz - 4, yz + 3.5);
        ctx.fillStyle = tok.sub; ctx.fill();
      });
      ctx.globalAlpha = 1;

      // bars / milestones + task name labels in the left margin
      for (var i = 0; i < n; i++) {
        var r = rows[i], y = yOf(i);
        var col = r.color || PAL[r._gi % PAL.length];
        if (r.milestone) {
          var mx = view.scaleX(r.start), s = barH * 0.5;
          ctx.fillStyle = col;
          ctx.beginPath(); ctx.moveTo(mx, y - s); ctx.lineTo(mx + s, y); ctx.lineTo(mx, y + s); ctx.lineTo(mx - s, y); ctx.closePath(); ctx.fill();
        } else {
          var bx0 = view.scaleX(r.start), bx1 = view.scaleX(r.end), bw = Math.max(2, bx1 - bx0);
          ctx.fillStyle = col; ctx.globalAlpha = 0.35;
          ctx.beginPath();
          if (ctx.roundRect) ctx.roundRect(bx0, y - barH / 2, bw, barH, 4); else ctx.rect(bx0, y - barH / 2, bw, barH);
          ctx.fill(); ctx.globalAlpha = 1;
          var pr = (r.progress != null) ? Math.max(0, Math.min(1, r.progress)) : 0;
          if (pr > 0) {
            ctx.fillStyle = col;
            ctx.beginPath();
            if (ctx.roundRect) ctx.roundRect(bx0, y - barH / 2, bw * pr, barH, 4); else ctx.rect(bx0, y - barH / 2, bw * pr, barH);
            ctx.fill();
          }
          ctx.strokeStyle = col; ctx.lineWidth = 1;
          ctx.beginPath();
          if (ctx.roundRect) ctx.roundRect(bx0, y - barH / 2, bw, barH, 4); else ctx.rect(bx0, y - barH / 2, bw, barH);
          ctx.stroke();
          if (r.progress != null && bw > 44) {
            ctx.fillStyle = "#fff"; ctx.font = "600 10px Segoe UI, system-ui, sans-serif";
            ctx.textAlign = "left"; ctx.textBaseline = "middle";
            if (bw * pr > 34) ctx.fillText(Math.round(pr * 100) + "%", bx0 + 5, y);
          }
        }
        // task name in the left margin
        ctx.fillStyle = tok.fg; ctx.font = "11px Segoe UI, system-ui, sans-serif";
        ctx.textAlign = "right"; ctx.textBaseline = "middle";
        ctx.fillText(r.name, pl.left - 8, y);
      }

      // today line (client-side: shows the date the report is VIEWED)
      if (c.today !== false) {
        var td = todayEpochDay();
        if (td >= c.t0 && td <= c.t1) {
          var tx = view.scaleX(td);
          ctx.strokeStyle = "#dc2626"; ctx.lineWidth = 1.4; ctx.setLineDash([5, 4]);
          ctx.beginPath(); ctx.moveTo(tx, pl.top); ctx.lineTo(tx, pl.top + pl.height); ctx.stroke();
          ctx.setLineDash([]);
          ctx.fillStyle = "#dc2626"; ctx.font = "600 10px Segoe UI, system-ui, sans-serif";
          ctx.textAlign = "center"; ctx.textBaseline = "bottom";
          ctx.fillText("오늘", tx, pl.top - 2);
        }
      }
      ctx.restore();
    },

    onHover: function (view, cursor) {
      var c = cfg(view); if (!c || !cursor) return null;
      var rows = c.rows || [], n = rows.length; if (!n) return null;
      var idx = n - 1 - Math.round(cursor.dataY);
      if (idx < 0 || idx >= n) return null;
      var r = rows[idx];
      var span = r.milestone ? fmtDay(r.start) : (fmtDay(r.start) + " ~ " + fmtDay(r.end));
      var bits = [r.name + ": " + span];
      if (r.progress != null && !r.milestone) bits.push(Math.round(r.progress * 100) + "%");
      if (r.owner) bits.push(r.owner);
      return { hud: bits.join(" · ") };
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"].gantt = P;
})();
