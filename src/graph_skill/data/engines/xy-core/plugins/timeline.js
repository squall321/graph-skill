/* timeline — milestone events on a horizontal date axis with alternating callouts.
   Dates pre-parsed to epoch DAYS by the recipe. hideAxes + onDrawOutside.
   config (pluginConfig.timeline): { events:[{t,label,desc?,status?(done|active|pending),color?}],
                                     t0, t1, ticks:[{t,label}], today?:bool }                 */
(function () {
  "use strict";
  var STATUS = { done: "#16a34a", active: "#2563eb", pending: "#9aa3af" };
  function cfg(view) { return (view.pluginConfig && view.pluginConfig.timeline) || null; }
  function dayMs() { return 86400000; }
  function todayEpochDay() { var d = new Date(); return Math.floor((Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())) / dayMs()); }
  function fmtDay(t) { var d = new Date(t * dayMs()); return (d.getUTCMonth() + 1) + "/" + d.getUTCDate(); }

  var P = {
    id: "timeline",
    order: 45,
    onDrawOutside: function (ctx, view) {
      var c = cfg(view); if (!c) return;
      var ev = c.events || []; if (!ev.length) return;
      var pl = view.plot, tok = view.theme, midY = pl.top + pl.height * 0.55;
      ctx.save();

      // date ticks under the axis
      ctx.font = "10px Segoe UI, system-ui, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "top";
      (c.ticks || []).forEach(function (tk) {
        var x = view.scaleX(tk.t); if (x < pl.left - 1 || x > pl.left + pl.width + 1) return;
        ctx.strokeStyle = tok.grid; ctx.beginPath(); ctx.moveTo(x, midY - 4); ctx.lineTo(x, midY + 4); ctx.stroke();
        ctx.fillStyle = tok.sub; ctx.fillText(tk.label, x, pl.top + pl.height + 4);
      });

      // axis
      ctx.strokeStyle = tok.axis; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(pl.left, midY); ctx.lineTo(pl.left + pl.width, midY); ctx.stroke();

      // events: alternating callouts above/below
      for (var i = 0; i < ev.length; i++) {
        var e = ev[i], x = view.scaleX(e.t);
        var col = e.color || STATUS[e.status || "pending"] || STATUS.pending;
        var up = i % 2 === 0;
        var ly = up ? midY - 26 - (i % 4 === 2 ? 18 : 0) : midY + 26 + (i % 4 === 3 ? 18 : 0);
        ctx.strokeStyle = col; ctx.lineWidth = 1.2;
        ctx.beginPath(); ctx.moveTo(x, midY); ctx.lineTo(x, ly + (up ? 10 : -10)); ctx.stroke();
        ctx.beginPath(); ctx.arc(x, midY, 6, 0, 6.2832);
        ctx.fillStyle = col; ctx.fill();
        ctx.lineWidth = 2; ctx.strokeStyle = tok.bg; ctx.stroke();
        if (e.status === "done") {                                 // check mark
          ctx.strokeStyle = "#fff"; ctx.lineWidth = 1.6;
          ctx.beginPath(); ctx.moveTo(x - 2.6, midY); ctx.lineTo(x - 0.8, midY + 2); ctx.lineTo(x + 2.8, midY - 2.4); ctx.stroke();
        }
        ctx.fillStyle = tok.fg; ctx.font = "600 11px Segoe UI, system-ui, sans-serif";
        ctx.textAlign = "center"; ctx.textBaseline = up ? "bottom" : "top";
        ctx.fillText(e.label, x, ly + (up ? 6 : -6));
        ctx.fillStyle = tok.sub; ctx.font = "10px Segoe UI, system-ui, sans-serif";
        ctx.fillText(fmtDay(e.t), x, ly + (up ? 18 : -18));
      }

      // today marker
      if (c.today !== false) {
        var td = todayEpochDay();
        if (td >= c.t0 && td <= c.t1) {
          var tx = view.scaleX(td);
          ctx.strokeStyle = "#dc2626"; ctx.lineWidth = 1.4; ctx.setLineDash([5, 4]);
          ctx.beginPath(); ctx.moveTo(tx, pl.top + 6); ctx.lineTo(tx, pl.top + pl.height - 6); ctx.stroke();
          ctx.setLineDash([]);
          ctx.fillStyle = "#dc2626"; ctx.font = "600 10px Segoe UI, system-ui, sans-serif";
          ctx.textAlign = "center"; ctx.textBaseline = "bottom";
          ctx.fillText("오늘", tx, pl.top + 6);
        }
      }
      ctx.restore();
    },

    onHover: function (view, cursor) {
      var c = cfg(view); if (!c || !cursor) return null;
      var ev = c.events || [], best = null, bd = Infinity;
      for (var i = 0; i < ev.length; i++) {
        var d = Math.abs(view.scaleX(ev[i].t) - cursor.px);
        if (d < bd) { bd = d; best = ev[i]; }
      }
      if (!best || bd > 40) return null;
      var s = best.label + " · " + fmtDay(best.t);
      if (best.status) s += " · " + ({ done: "완료", active: "진행", pending: "예정" }[best.status] || best.status);
      if (best.desc) s += " — " + best.desc;
      return { hud: s };
    }
  };
  window.GraphPlugins = window.GraphPlugins || {};
  window.GraphPlugins["xy-core"] = window.GraphPlugins["xy-core"] || {};
  window.GraphPlugins["xy-core"].timeline = P;
})();
