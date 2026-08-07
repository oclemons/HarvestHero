"""ai_assistant.py — Pattern intelligence engine + Ava UI."""

import collections
import datetime
import statistics
import threading
import tkinter as tk
from typing import List, Dict, Any

import customtkinter as ctk

from theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, BG_OVERLAY, BG_HOVER,
    ACCENT, ACCENT_HOVER, ACCENT_GOLD,
    ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR,
    BG_PRIMARY, BG_SECONDARY, BG_CARD,
)


# ---------------------------------------------------------------------------
# Pattern Intelligence Engine
# ---------------------------------------------------------------------------

class _PatternEngine:
    """Statistical pattern analysis — velocity, anomalies, predictions, loss."""

    def __init__(self, db):
        self.db     = db
        self._txns  = None
        self._items = None

    def _load(self):
        if self._txns is None:
            self._txns  = self.db.get_transactions()
            self._items = self.db.get_all_items()

    # ── Consumption velocity ──────────────────────────────────────────

    def velocity(self, barcode: str, days: int = 14) -> float:
        """Average units/day scanned out for an item over the last N days."""
        self._load()
        cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
        qty = sum(t["quantity"] for t in self._txns
                  if t["barcode"] == barcode
                  and t["transaction_type"] == "SCAN_OUT"
                  and t["timestamp"][:10] >= cutoff)
        return qty / max(days, 1)

    def trend(self, barcode: str, window: int = 7) -> str:
        """Compare recent window vs older window → 'rising'/'falling'/'stable'."""
        self._load()
        today = datetime.date.today()
        rc = (today - datetime.timedelta(days=window)).isoformat()
        oc = (today - datetime.timedelta(days=window * 2)).isoformat()
        recent = sum(t["quantity"] for t in self._txns
                     if t["barcode"] == barcode
                     and t["transaction_type"] == "SCAN_OUT"
                     and t["timestamp"][:10] >= rc)
        older = sum(t["quantity"] for t in self._txns
                    if t["barcode"] == barcode
                    and t["transaction_type"] == "SCAN_OUT"
                    and oc <= t["timestamp"][:10] < rc)
        if older == 0:
            return "new"
        ratio = recent / older
        if ratio > 1.3:   return "rising"
        if ratio < 0.7:   return "falling"
        return "stable"

    # ── Stockout prediction ───────────────────────────────────────────

    def predict_stockout(self, item: dict) -> dict | None:
        v = self.velocity(item["barcode"], days=14)
        if v <= 0:
            return None
        cur = item["current_quantity"]
        min_stock = item["minimum_stock"]
        return {
            "days_until_min":  max(0, int((cur - min_stock) / v)),
            "days_until_zero": max(0, int(cur / v)),
            "velocity":        round(v, 2),
            "trend":           self.trend(item["barcode"]),
        }

    def stockout_predictions(self, horizon_days: int = 14) -> List[dict]:
        self._load()
        results = []
        for item in self._items:
            p = self.predict_stockout(item)
            if p and p["days_until_zero"] <= horizon_days:
                results.append({
                    "item_name":        item["item_name"],
                    "current_quantity": item["current_quantity"],
                    "minimum_stock":    item["minimum_stock"],
                    **p,
                })
        return sorted(results, key=lambda x: x["days_until_zero"])

    # ── Anomaly detection (z-score on transaction qty) ────────────────

    def anomalous_transactions(self, days: int = 30) -> List[dict]:
        self._load()
        cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
        recent = [t for t in self._txns if t["timestamp"][:10] >= cutoff]

        groups: Dict[tuple, list] = collections.defaultdict(list)
        for t in recent:
            groups[(t["barcode"], t["transaction_type"])].append(t["quantity"])

        anomalies = []
        for t in recent:
            key  = (t["barcode"], t["transaction_type"])
            qtys = groups[key]
            if len(qtys) < 4:
                continue
            mean  = statistics.mean(qtys)
            stdev = statistics.stdev(qtys)
            if stdev == 0:
                continue
            z = (t["quantity"] - mean) / stdev
            if z > 2.5:
                anomalies.append({
                    **dict(t),
                    "z_score": round(z, 1),
                    "mean":    round(mean, 1),
                })
        return sorted(anomalies, key=lambda x: x["z_score"], reverse=True)[:10]

    # ── Loss / shrinkage indicator ────────────────────────────────────

    def loss_indicators(self, days: int = 30) -> List[dict]:
        """Items where outflow persistently exceeds inflow."""
        self._load()
        cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
        recent = [t for t in self._txns if t["timestamp"][:10] >= cutoff]

        net: Dict[str, dict] = collections.defaultdict(
            lambda: {"item_name": "", "in": 0, "out": 0})
        for t in recent:
            net[t["barcode"]]["item_name"] = t["item_name"]
            if t["transaction_type"] == "SCAN_IN":
                net[t["barcode"]]["in"]  += t["quantity"]
            else:
                net[t["barcode"]]["out"] += t["quantity"]

        losses = []
        for bc, d in net.items():
            if d["out"] > d["in"] * 1.5 and d["out"] >= 5:
                losses.append({
                    "barcode":   bc,
                    "item_name": d["item_name"],
                    "total_out": d["out"],
                    "total_in":  d["in"],
                    "net_loss":  d["out"] - d["in"],
                    "ratio":     round(d["out"] / max(d["in"], 1), 1),
                })
        return sorted(losses, key=lambda x: x["net_loss"], reverse=True)

    # ── Duplicate scan detection ──────────────────────────────────────

    def duplicate_scans(self, minutes: int = 5) -> List[dict]:
        """Same item + same user scanned twice within N minutes."""
        self._load()
        window = datetime.timedelta(minutes=minutes)
        outs = sorted(
            [t for t in self._txns if t["transaction_type"] == "SCAN_OUT"],
            key=lambda t: (t["barcode"], t["username"], t["timestamp"]))

        dupes = []
        for i in range(1, len(outs)):
            prev, curr = outs[i - 1], outs[i]
            if prev["barcode"] != curr["barcode"] or \
               prev["username"] != curr["username"]:
                continue
            try:
                t1 = datetime.datetime.fromisoformat(prev["timestamp"])
                t2 = datetime.datetime.fromisoformat(curr["timestamp"])
                gap = abs(t2 - t1)
                if gap <= window:
                    dupes.append({
                        "item_name":   curr["item_name"],
                        "username":    curr["username"],
                        "timestamp":   curr["timestamp"],
                        "gap_seconds": int(gap.total_seconds()),
                    })
            except Exception:
                continue
        return dupes[:15]

    # ── After-hours transactions ──────────────────────────────────────

    def after_hours_transactions(self,
                                  start_hour: int = 7,
                                  end_hour:   int = 19,
                                  days:       int = 30) -> List[dict]:
        self._load()
        cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
        results = []
        for t in self._txns:
            if t["timestamp"][:10] < cutoff:
                continue
            try:
                hour = int(t["timestamp"][11:13])
                if hour < start_hour or hour >= end_hour:
                    results.append(dict(t))
            except Exception:
                continue
        return results[:20]

    # ── User volume anomaly ───────────────────────────────────────────

    def user_anomalies(self, recent_days: int = 7,
                       baseline_days: int = 60) -> List[dict]:
        """Users whose scan volume this week is 2.5× their rolling average."""
        self._load()
        today        = datetime.date.today()
        base_cutoff  = (today - datetime.timedelta(days=baseline_days)).isoformat()
        recent_cutoff = (today - datetime.timedelta(days=recent_days)).isoformat()

        user_daily: Dict[str, Dict[str, int]] = collections.defaultdict(
            lambda: collections.defaultdict(int))
        for t in self._txns:
            if t["timestamp"][:10] >= base_cutoff:
                user_daily[t["username"]][t["timestamp"][:10]] += t["quantity"]

        anomalies = []
        for username, daily in user_daily.items():
            old_vals = [v for d, v in daily.items() if d < recent_cutoff]
            new_vals = [v for d, v in daily.items() if d >= recent_cutoff]
            if len(old_vals) < 5 or not new_vals:
                continue
            old_mean = statistics.mean(old_vals)
            new_mean = statistics.mean(new_vals)
            if old_mean == 0:
                continue
            ratio = new_mean / old_mean
            if ratio > 2.5:
                anomalies.append({
                    "username":        username,
                    "ratio":           round(ratio, 1),
                    "recent_avg":      round(new_mean, 1),
                    "historical_avg":  round(old_mean, 1),
                })
        return sorted(anomalies, key=lambda x: x["ratio"], reverse=True)

    # ── Expiration tracking ──────────────────────────────────────────

    def expiration_alerts(self) -> dict:
        """Categorized expiration alerts: expired / 14d / 30d / 60d."""
        return {
            "expired":    self.db.get_expired_items(),
            "expire_14":  self.db.get_expiring_items(14),
            "expire_30":  self.db.get_expiring_items(30),
            "expire_60":  self.db.get_expiring_items(60),
        }

    # ── Shopping list (priority purchase recommendations) ─────────────

    def shopping_list(self) -> List[dict]:
        """Ordered purchase request list: HIGH / MEDIUM / LOW priority."""
        self._load()
        items   = []
        seen    = set()

        for item in self.db.get_out_of_stock_items():
            seen.add(item["item_name"])
            items.append({
                "item_name": item["item_name"],
                "priority":  "HIGH",
                "reason":    "Out of stock",
                "have":      0,
                "minimum":   item["minimum_stock"],
            })

        for p in self.stockout_predictions(7):
            if p["item_name"] not in seen:
                seen.add(p["item_name"])
                items.append({
                    "item_name": p["item_name"],
                    "priority":  "HIGH",
                    "reason":    f"Runs out in ~{p['days_until_zero']}d",
                    "have":      p["current_quantity"],
                    "minimum":   p["minimum_stock"],
                })

        for item in self.db.get_low_stock_items():
            if item["item_name"] not in seen:
                seen.add(item["item_name"])
                items.append({
                    "item_name": item["item_name"],
                    "priority":  "MEDIUM",
                    "reason":    f"At minimum ({item['current_quantity']} / {item['minimum_stock']})",
                    "have":      item["current_quantity"],
                    "minimum":   item["minimum_stock"],
                })

        for p in self.stockout_predictions(14):
            if p["item_name"] not in seen and p["days_until_zero"] > 7:
                seen.add(p["item_name"])
                items.append({
                    "item_name": p["item_name"],
                    "priority":  "LOW",
                    "reason":    f"Low in ~{p['days_until_zero']}d",
                    "have":      p["current_quantity"],
                    "minimum":   p["minimum_stock"],
                })
        return items

    # ── Aggregated insights ───────────────────────────────────────────

    def all_insights(self) -> List[dict]:
        self._load()
        results = []

        oos = self.db.get_out_of_stock_items()
        if oos:
            results.append({
                "kind": "error", "icon": "✕", "priority": 100,
                "title": f"{len(oos)} item(s) out of stock",
                "body":  ", ".join(i["item_name"] for i in oos[:5]),
            })

        # Expiration alerts
        exp_alerts = self.expiration_alerts()
        if exp_alerts["expired"]:
            n = len(exp_alerts["expired"])
            results.append({
                "kind": "error", "icon": "⊘", "priority": 98,
                "title": f"{n} item(s) EXPIRED — remove from shelves immediately",
                "body":  ", ".join(i["item_name"] for i in exp_alerts["expired"][:5]),
            })
        if exp_alerts["expire_14"]:
            n = len(exp_alerts["expire_14"])
            results.append({
                "kind": "error", "icon": "⏰", "priority": 93,
                "title": f"{n} item(s) expiring within 14 days — move to front",
                "body":  ", ".join(
                    f"{i['item_name']} ({i['expiration_date']})"
                    for i in exp_alerts["expire_14"][:4]),
            })
        elif exp_alerts["expire_30"]:
            n = len(exp_alerts["expire_30"])
            results.append({
                "kind": "warning", "icon": "⌛", "priority": 88,
                "title": f"{n} item(s) expiring within 30 days",
                "body":  ", ".join(
                    f"{i['item_name']} ({i['expiration_date']})"
                    for i in exp_alerts["expire_30"][:4]),
            })

        soon = self.stockout_predictions(3)
        if soon:
            lines = ", ".join(
                f"{p['item_name']} (~{p['days_until_zero']}d)" for p in soon)
            results.append({
                "kind": "error", "icon": "⏱", "priority": 95,
                "title": "Stockout predicted within 3 days",
                "body":  lines,
            })

        losses = self.loss_indicators()
        if losses:
            lines = ", ".join(
                f"{l['item_name']} ({l['ratio']}× more out than in)"
                for l in losses[:3])
            results.append({
                "kind": "warning", "icon": "⚠", "priority": 90,
                "title": "Potential inventory shrinkage detected",
                "body":  lines,
            })

        anom = self.anomalous_transactions()
        if anom:
            lines = ", ".join(
                f"{a['item_name']} ({a['quantity']} units, z={a['z_score']})"
                for a in anom[:3])
            results.append({
                "kind": "warning", "icon": "⚡", "priority": 85,
                "title": "Unusual transaction quantities",
                "body":  lines,
            })

        dupes = self.duplicate_scans()
        if dupes:
            lines = ", ".join(
                f"{d['item_name']} ({d['username']})" for d in dupes[:3])
            results.append({
                "kind": "warning", "icon": "⊛", "priority": 80,
                "title": f"Possible duplicate scans ({len(dupes)} found)",
                "body":  lines,
            })

        u_anom = self.user_anomalies()
        if u_anom:
            lines = ", ".join(
                f"{u['username']} ({u['ratio']}× normal volume)"
                for u in u_anom[:3])
            results.append({
                "kind": "warning", "icon": "◈", "priority": 75,
                "title": "Unusual user scan activity",
                "body":  lines,
            })

        medium = [p for p in self.stockout_predictions(14)
                  if p["days_until_zero"] > 3]
        if medium:
            lines = ", ".join(
                f"{p['item_name']} (~{p['days_until_zero']}d)" for p in medium[:5])
            results.append({
                "kind": "warning", "icon": "⏳", "priority": 70,
                "title": "Predicted stockout within 14 days",
                "body":  lines,
            })

        low = self.db.get_low_stock_items()
        if low:
            results.append({
                "kind": "warning", "icon": "▼", "priority": 65,
                "title": f"{len(low)} item(s) at or below minimum stock",
                "body":  ", ".join(i["item_name"] for i in low[:5]),
            })

        cutoff7 = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
        recent_outs = [t for t in self._txns
                       if t["transaction_type"] == "SCAN_OUT"
                       and t["timestamp"][:10] >= cutoff7]
        if recent_outs:
            counts = collections.Counter(t["item_name"] for t in recent_outs)
            top = counts.most_common(3)
            results.append({
                "kind": "info", "icon": "↑", "priority": 50,
                "title": "Fastest-moving items (7 days)",
                "body":  ", ".join(f"{n} ({c})" for n, c in top),
            })

        ah = self.after_hours_transactions()
        if ah:
            results.append({
                "kind": "info", "icon": "◑", "priority": 45,
                "title": f"{len(ah)} after-hours transactions (last 30 days)",
                "body":  "Review the Anomalies tab for details.",
            })

        cutoff30 = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
        touched  = {t["barcode"] for t in self._txns
                    if t["timestamp"][:10] >= cutoff30}
        slow = [i["item_name"] for i in self._items
                if i["barcode"] not in touched]
        if slow:
            results.append({
                "kind": "info", "icon": "○", "priority": 30,
                "title": f"{len(slow)} item(s) not moved in 30+ days",
                "body":  ", ".join(slow[:5]) + ("…" if len(slow) > 5 else ""),
            })

        results.sort(key=lambda x: x["priority"], reverse=True)

        if not results:
            results.append({
                "kind": "success", "icon": "✓", "priority": 0,
                "title": "Inventory looks healthy",
                "body":  "No anomalies or issues detected.",
            })
        return results


# ---------------------------------------------------------------------------
# _LocalAI — public API (wraps PatternEngine, keeps health_score compat)
# ---------------------------------------------------------------------------

class _LocalAI:
    def __init__(self, db):
        self.db = db
        self._pe = _PatternEngine(db)

    def health_score(self) -> int:
        items = self.db.get_all_items()
        if not items:
            return 100
        total = len(items)
        out = sum(1 for i in items if i["current_quantity"] == 0)
        low = sum(1 for i in items if 0 < i["current_quantity"] <= i["minimum_stock"])
        penalty = out * 15 + low * 5
        return max(0, min(100, 100 - int(penalty * 100 / max(total * 15, 1))))

    def insights(self) -> List[dict]:
        return self._pe.all_insights()

    def pattern_engine(self) -> _PatternEngine:
        return self._pe

    def answer(self, question: str) -> str:
        q = question.lower()
        stats = self.db.get_stats()
        self._pe._load()

        # ── Loss / shrinkage ──────────────────────────────
        if any(w in q for w in ("loss", "shrinkage", "missing", "theft",
                                "stolen", "disappear")):
            losses = self._pe.loss_indicators()
            if not losses:
                return "No shrinkage patterns detected in the last 30 days."
            lines = "\n".join(
                f"  • {l['item_name']}: {l['total_out']} out vs "
                f"{l['total_in']} in (×{l['ratio']} ratio)"
                for l in losses[:6])
            return (f"Potential shrinkage detected for {len(losses)} item(s):\n"
                    f"{lines}\n\nReview the Anomalies tab for transaction details.")

        # ── Anomaly ───────────────────────────────────────
        if any(w in q for w in ("anomal", "unusual", "suspicious",
                                "weird", "outlier", "abnormal")):
            anom = self._pe.anomalous_transactions()
            dupes = self._pe.duplicate_scans()
            lines = []
            if anom:
                lines.append(f"Unusual quantities ({len(anom)} transactions):")
                for a in anom[:4]:
                    lines.append(
                        f"  • {a['item_name']}: {a['quantity']} units "
                        f"(avg {a['mean']}, z={a['z_score']})")
            if dupes:
                lines.append(f"\nDuplicate scans ({len(dupes)} found):")
                for d in dupes[:4]:
                    lines.append(
                        f"  • {d['item_name']} by {d['username']} "
                        f"(gap: {d['gap_seconds']}s)")
            return "\n".join(lines) if lines else "No anomalies detected."

        # ── Duplicate scans ───────────────────────────────
        if any(w in q for w in ("duplicate", "double scan", "scan twice")):
            dupes = self._pe.duplicate_scans()
            if not dupes:
                return "No duplicate scans detected in the transaction history."
            lines = "\n".join(
                f"  • {d['item_name']} by {d['username']} at {d['timestamp'][:16]} "
                f"(gap: {d['gap_seconds']}s)"
                for d in dupes[:8])
            return f"Possible duplicate scans ({len(dupes)}):\n{lines}"

        # ── Predictions / forecast ────────────────────────
        if any(w in q for w in ("predict", "forecast", "when will",
                                "run out", "stockout", "days left")):
            preds = self._pe.stockout_predictions(30)
            if not preds:
                return "No items are predicted to stock out in the next 30 days."
            lines = "\n".join(
                f"  • {p['item_name']}: ~{p['days_until_zero']} days "
                f"(velocity {p['velocity']}/day, trend: {p['trend']})"
                for p in preds[:8])
            return (f"Stockout predictions for the next 30 days "
                    f"({len(preds)} items):\n{lines}")

        # ── After-hours ───────────────────────────────────
        if any(w in q for w in ("after hours", "night", "midnight",
                                "outside hours", "late")):
            ah = self._pe.after_hours_transactions()
            if not ah:
                return "No after-hours transactions found in the last 30 days."
            lines = "\n".join(
                f"  • {t['item_name']} by {t['username']} at {t['timestamp'][:16]}"
                for t in ah[:8])
            return f"After-hours transactions ({len(ah)} in 30 days):\n{lines}"

        # ── User anomaly ──────────────────────────────────
        if any(w in q for w in ("user", "staff", "who", "employee")):
            u_anom = self._pe.user_anomalies()
            if u_anom:
                lines = "\n".join(
                    f"  • {u['username']}: {u['ratio']}× normal "
                    f"(avg {u['recent_avg']} vs historical {u['historical_avg']})"
                    for u in u_anom)
                return f"Users with unusual activity:\n{lines}"
            top = collections.Counter(
                t["username"] for t in self._pe._txns).most_common(5)
            lines = "\n".join(f"  • {u}: {c} transactions" for u, c in top)
            return f"Most active users (all time):\n{lines}"

        # ── Velocity / trend ──────────────────────────────
        if any(w in q for w in ("velocity", "trend", "rate",
                                "consumption", "how fast")):
            items = self.db.get_all_items()
            data = []
            for item in items:
                v = self._pe.velocity(item["barcode"])
                if v > 0:
                    t = self._pe.trend(item["barcode"])
                    data.append((item["item_name"], v, t))
            data.sort(key=lambda x: x[1], reverse=True)
            if not data:
                return "No consumption data yet."
            lines = "\n".join(
                f"  • {n}: {v:.2f}/day ({tr})"
                for n, v, tr in data[:8])
            return f"Item consumption velocities:\n{lines}"

        # ── Standard questions ────────────────────────────
        if any(w in q for w in ("low stock", "running low")):
            items = self.db.get_low_stock_items()
            if not items:
                return "No items are currently low on stock."
            return ("Low stock items:\n" +
                    "\n".join(f"  • {i['item_name']} "
                              f"({i['current_quantity']} / min {i['minimum_stock']})"
                              for i in items[:8]))

        if any(w in q for w in ("out of stock", "zero", "empty")):
            items = self.db.get_out_of_stock_items()
            if not items:
                return "No items are currently out of stock."
            return f"Out of stock ({len(items)}):\n" + \
                   "\n".join(f"  • {i['item_name']}" for i in items[:8])

        if any(w in q for w in ("fast", "popular", "most used", "moving")):
            outs = [t for t in self._pe._txns
                    if t["transaction_type"] == "SCAN_OUT"]
            counts = collections.Counter(t["item_name"] for t in outs)
            if not counts:
                return "No scan-out transactions yet."
            top = counts.most_common(5)
            return "Top 5 fastest-moving items:\n" + \
                   "\n".join(f"  • {n}: {c} scan-outs" for n, c in top)

        if any(w in q for w in ("today", "this week", "recent", "activity")):
            return (
                f"Today's activity:\n"
                f"  • Scan Ins:  {stats['today_in_count']} "
                f"({stats['today_in_qty']} units)\n"
                f"  • Scan Outs: {stats['today_out_count']} "
                f"({stats['today_out_qty']} units)\n"
                f"  • Week total: {stats['week_txns']} transactions"
            )

        # ── Expiration ────────────────────────────────────
        if any(w in q for w in ("expir", "expired", "expiry", "expire",
                                "rotation", "rotate", "shelf life", "spoil")):
            alerts = self._pe.expiration_alerts()
            lines  = []
            if alerts["expired"]:
                lines.append(f"EXPIRED ({len(alerts['expired'])} items — remove now):")
                for i in alerts["expired"][:5]:
                    lines.append(f"  ✕ {i['item_name']}  (expired {i['expiration_date']})")
            if alerts["expire_14"]:
                lines.append(f"\nExpiring within 14 days ({len(alerts['expire_14'])} items — move to front):")
                for i in alerts["expire_14"][:6]:
                    lines.append(f"  ⏰ {i['item_name']}  ({i['expiration_date']})")
            if alerts["expire_30"] and not alerts["expire_14"]:
                lines.append(f"\nExpiring within 30 days ({len(alerts['expire_30'])} items):")
                for i in alerts["expire_30"][:6]:
                    lines.append(f"  ⌛ {i['item_name']}  ({i['expiration_date']})")
            if not any([alerts["expired"], alerts["expire_14"], alerts["expire_30"]]):
                return "No items are expiring within the next 30 days."
            return "\n".join(lines)

        # ── Shopping list / purchase request ──────────────
        if any(w in q for w in ("shop", "buy", "order", "purchase",
                                "request", "what should", "what do we need",
                                "need to order", "restock list")):
            sl = self.db.get_shopping_list()
            if not sl:
                return "Nothing on the shopping list — inventory looks healthy!"
            lines = ["Shopping list (auto-tracked from sales):"]
            for x in sorted(sl, key=lambda r: r["quantity_needed"], reverse=True):
                lines.append(f"  • {x['item_name']}  — need {x['quantity_needed']}")
            return "\n".join(lines)

        # ── Morning briefing ──────────────────────────────
        if any(w in q for w in ("brief", "morning", "good morning",
                                "summary", "overview", "what's happening",
                                "daily report")):
            alerts  = self._pe.expiration_alerts()
            sl      = self.db.get_shopping_list()
            top_sl  = sorted(sl, key=lambda r: r["quantity_needed"], reverse=True)
            low     = self.db.get_low_stock_items()
            oos     = self.db.get_out_of_stock_items()
            preds   = self._pe.stockout_predictions(7)
            today   = datetime.date.today().strftime("%A, %B %d")
            lines = [
                f"Good morning! Here's your pantry summary for {today}:",
                "",
                f"Inventory Status:",
                f"  • Total items:     {stats['total_items']}",
                f"  • Low stock:       {stats['low_stock']}",
                f"  • Out of stock:    {stats['out_of_stock']}",
            ]
            if alerts["expired"]:
                lines.append(f"  • EXPIRED (remove): {len(alerts['expired'])} items")
            if alerts["expire_14"]:
                lines.append(f"  • Expiring in 14d:  {len(alerts['expire_14'])} items")
            if preds:
                lines.append(f"\nExpected shortages this week:")
                for p in preds[:4]:
                    lines.append(f"  • {p['item_name']} in ~{p['days_until_zero']} days")
            if top_sl:
                lines.append(f"\nShopping list ({len(sl)} item(s)):")
                for x in top_sl[:4]:
                    lines.append(f"  • {x['item_name']}  — need {x['quantity_needed']}")
            lines.append(f"\nToday's scans: {stats['today_in_count']} in, {stats['today_out_count']} out")
            return "\n".join(lines)

        # ── Where is / storage location ───────────────────
        if any(w in q for w in ("where is", "where are", "shelf",
                                "location", "storage", "stored", "which shelf")):
            items = self.db.get_all_items()
            located = [i for i in items if i.get("storage_location")]
            if not located:
                return "No storage locations have been assigned yet."
            # Try to find specific item mentioned in question
            for item in located:
                if item["item_name"].lower() in q:
                    return (f"{item['item_name']} is stored at: "
                            f"{item['storage_location']}.")
            lines = "\n".join(
                f"  • {i['item_name']}: {i['storage_location']}"
                for i in sorted(located, key=lambda x: x["storage_location"])[:12])
            return f"Storage locations:\n{lines}"

        if any(w in q for w in ("restock", "priority")):
            items = (self.db.get_out_of_stock_items() +
                     self.db.get_low_stock_items())
            if not items:
                return "No restock priorities — inventory looks healthy!"
            return "Restock priorities:\n" + \
                   "\n".join(f"  • {i['item_name']} "
                             f"(have {i['current_quantity']}, "
                             f"min {i['minimum_stock']})"
                             for i in items[:8])

        if any(w in q for w in ("health", "score", "status")):
            score = self.health_score()
            return (
                f"Inventory Health Score: {score}/100\n"
                f"  • Items: {stats['total_items']}  "
                f"Units: {stats['total_units']}\n"
                f"  • Low stock: {stats['low_stock']}  "
                f"Out of stock: {stats['out_of_stock']}"
            )

        # ── Specific item question ─────────────────────────
        items = self.db.get_all_items()
        for item in items:
            name_lower = item["item_name"].lower()
            if name_lower in q or any(w in q for w in name_lower.split()):
                v    = self._pe.velocity(item["barcode"])
                p    = self._pe.predict_stockout(item)
                exp  = item.get("expiration_date", "")
                loc  = item.get("storage_location", "")
                brand = item.get("brand", "")
                lines = [
                    f"{item['item_name']}"
                    + (f"  ({brand})" if brand else ""),
                    f"  Category: {item['category'] or 'N/A'}",
                    f"  Stock: {item['current_quantity']} units  (min: {item['minimum_stock']})",
                ]
                if loc:
                    lines.append(f"  Location: {loc}")
                if v and v > 0:
                    lines.append(f"  Weekly use: ~{round(v*7,1)} units/week")
                if p:
                    lines.append(f"  Estimated days remaining: {p['days_until_zero']}")
                if exp:
                    lines.append(f"  Expiration date: {exp}")
                return "\n".join(lines)

        return (
            "I can answer questions like:\n"
            "  • Morning briefing / daily summary\n"
            "  • What's expiring soon?\n"
            "  • What should we order? / Shopping list\n"
            "  • Where is [item]? / Storage locations\n"
            "  • How many [item name] do we have?\n"
            "  • What items are running low?\n"
            "  • What are the stockout predictions?\n"
            "  • Is there any inventory loss or shrinkage?\n"
            "  • Are there any anomalous transactions?\n"
            "  • What's the consumption velocity/trend?\n"
            "  • What's today's activity?\n"
            "  • What's the health score?"
        )


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

_KIND_COLORS = {
    "error":   ACCENT_RED,
    "warning": ACCENT_AMBER,
    "info":    ACCENT,
    "success": ACCENT_GREEN,
}

_TREND_ICONS = {"rising": "↑", "falling": "↓", "stable": "→", "new": "★"}
_TREND_COLORS = {
    "rising":  ACCENT_AMBER,
    "falling": ACCENT_GREEN,
    "stable":  TEXT_MUTED,
    "new":     ACCENT,
}


def _insight_card(parent, insight: dict, row: int):
    color = _KIND_COLORS.get(insight["kind"], ACCENT)
    card  = ctk.CTkFrame(
        parent, fg_color=BG_ELEVATED, corner_radius=10,
        border_width=1, border_color=BORDER_COLOR)
    card.grid(row=row, column=0, sticky="ew", pady=3)
    card.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(
        card, text=insight["icon"],
        font=ctk.CTkFont(family=FONT_FAMILY, size=16),
        text_color=color, width=38,
    ).grid(row=0, column=0, rowspan=2, padx=(14, 4), pady=12)
    ctk.CTkLabel(
        card, text=insight["title"],
        font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
        text_color=TEXT_PRIMARY, anchor="w",
    ).grid(row=0, column=1, sticky="w", padx=6, pady=(12, 2))
    ctk.CTkLabel(
        card, text=insight["body"],
        font=ctk.CTkFont(family=FONT_FAMILY, size=11),
        text_color=TEXT_MUTED, anchor="w", wraplength=620,
    ).grid(row=1, column=1, sticky="w", padx=6, pady=(0, 12))


# ---------------------------------------------------------------------------
# AIAssistant UI — tabbed: Insights | Predictions | Anomalies | Ask Ava
# ---------------------------------------------------------------------------

class AIAssistant(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color=BG_SURFACE)
        self.db  = db
        self._ai = _LocalAI(db)
        self._pe = self._ai.pattern_engine()
        self._active_tab = "insights"
        self._build()
        self.on_shown()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── Header ──────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=40, pady=(28, 0))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text="Ava",
            font=ctk.CTkFont(family=FONT_FAMILY, size=26, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            hdr, text="Pattern Intelligence · Built-in AI",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w")

        # Health score pill
        self._score_lbl = ctk.CTkLabel(
            hdr, text="—",
            font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
            text_color=ACCENT_GOLD,
        )
        self._score_lbl.grid(row=0, column=2, sticky="e")
        ctk.CTkLabel(
            hdr, text="Health Score",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=2, sticky="e")

        ctk.CTkButton(
            hdr, text="Refresh", width=90, height=32,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY, corner_radius=8,
            border_width=1, border_color=BORDER_COLOR,
            command=self.on_shown,
        ).grid(row=0, column=3, padx=(16, 0), sticky="e")

        # ── Tab bar ──────────────────────────────────────────────────
        tab_bar = ctk.CTkFrame(self, fg_color="transparent")
        tab_bar.grid(row=1, column=0, sticky="ew", padx=40, pady=(16, 0))

        self._tab_btns: dict = {}
        for key, label in [
            ("insights",    "Insights"),
            ("predictions", "Predictions"),
            ("anomalies",   "Anomalies"),
            ("ask",         "Ask Ava"),
        ]:
            b = ctk.CTkButton(
                tab_bar, text=label, width=120, height=34, corner_radius=8,
                fg_color=BG_ELEVATED if key == "insights" else "transparent",
                hover_color=BG_ELEVATED,
                text_color=ACCENT if key == "insights" else TEXT_MUTED,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                command=lambda k=key: self._switch_tab(k),
            )
            b.pack(side="left", padx=(0, 4))
            self._tab_btns[key] = b

        # ── Tab panels ───────────────────────────────────────────────
        self._panels: dict = {}
        for key, build_fn in [
            ("insights",    self._build_insights_panel),
            ("predictions", self._build_predictions_panel),
            ("anomalies",   self._build_anomalies_panel),
            ("ask",         self._build_ask_panel),
        ]:
            panel = build_fn()
            panel.grid(row=2, column=0, sticky="nsew")
            self._panels[key] = panel

        self._panels["predictions"].grid_remove()
        self._panels["anomalies"].grid_remove()
        self._panels["ask"].grid_remove()

    def _build_insights_panel(self) -> ctk.CTkFrame:
        panel = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0)
        panel.grid_columnconfigure(0, weight=1)
        self._insights_inner = ctk.CTkFrame(panel, fg_color="transparent")
        self._insights_inner.grid(row=0, column=0, sticky="ew", padx=40, pady=16)
        self._insights_inner.grid_columnconfigure(0, weight=1)
        return panel

    def _build_predictions_panel(self) -> ctk.CTkFrame:
        panel = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0)
        panel.grid_columnconfigure(0, weight=1)
        self._pred_inner = ctk.CTkFrame(panel, fg_color="transparent")
        self._pred_inner.grid(row=0, column=0, sticky="ew", padx=40, pady=16)
        self._pred_inner.grid_columnconfigure(0, weight=1)
        return panel

    def _build_anomalies_panel(self) -> ctk.CTkFrame:
        panel = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0)
        panel.grid_columnconfigure(0, weight=1)
        self._anom_inner = ctk.CTkFrame(panel, fg_color="transparent")
        self._anom_inner.grid(row=0, column=0, sticky="ew", padx=40, pady=16)
        self._anom_inner.grid_columnconfigure(0, weight=1)
        return panel

    def _build_ask_panel(self) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(self, fg_color="transparent")
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        # Suggestion chips
        chips = ctk.CTkFrame(panel, fg_color="transparent")
        chips.grid(row=0, column=0, sticky="ew", padx=40, pady=(12, 0))
        for q in [
            "Any inventory loss or shrinkage?",
            "What are the stockout predictions?",
            "Are there duplicate scans?",
            "What's today's activity?",
            "Show consumption velocity",
            "Any unusual user activity?",
        ]:
            ctk.CTkButton(
                chips, text=q, height=30, corner_radius=20,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                fg_color=BG_ELEVATED, hover_color=BG_HOVER,
                text_color=TEXT_SECONDARY,
                border_width=1, border_color=BORDER_COLOR,
                command=lambda question=q: self._ask_preset(question),
            ).pack(side="left", padx=(0, 6), pady=4)

        # Chat log
        self._chat_log = ctk.CTkScrollableFrame(
            panel, fg_color=BG_ELEVATED, corner_radius=12)
        self._chat_log.grid(row=1, column=0, sticky="nsew",
                            padx=40, pady=(12, 0))
        self._chat_log.grid_columnconfigure(0, weight=1)
        self._chat_row = 0

        # Input bar
        input_row = ctk.CTkFrame(panel, fg_color="transparent")
        input_row.grid(row=2, column=0, sticky="ew", padx=40, pady=12)
        input_row.grid_columnconfigure(0, weight=1)

        self._q_var = tk.StringVar()
        entry = ctk.CTkEntry(
            input_row, textvariable=self._q_var,
            placeholder_text="Ask Ava anything about your inventory…",
            height=44, fg_color=BG_OVERLAY,
            border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            corner_radius=10,
        )
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        entry.bind("<Return>", lambda _: self._ask())

        ctk.CTkButton(
            input_row, text="Ask", width=80, height=44,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color=BG_BASE, corner_radius=10,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self._ask,
        ).grid(row=0, column=1)

        return panel

    # ------------------------------------------------------------------
    # Tab switching
    # ------------------------------------------------------------------

    def _switch_tab(self, key: str):
        self._active_tab = key
        for k, btn in self._tab_btns.items():
            btn.configure(
                fg_color=BG_ELEVATED if k == key else "transparent",
                text_color=ACCENT if k == key else TEXT_MUTED,
            )
        for k, panel in self._panels.items():
            if k == key:
                panel.grid()
            else:
                panel.grid_remove()

    # ------------------------------------------------------------------
    # Populate
    # ------------------------------------------------------------------

    def on_shown(self):
        score = self._ai.health_score()
        color = (ACCENT_GREEN if score >= 75 else
                 ACCENT_AMBER if score >= 50 else ACCENT_RED)
        self._score_lbl.configure(text=f"{score}/100", text_color=color)
        # Refresh a fresh engine each time
        self._ai = _LocalAI(self.db)
        self._pe = self._ai.pattern_engine()
        self._populate_insights()
        self._populate_predictions()
        self._populate_anomalies()

    def _populate_insights(self):
        for w in self._insights_inner.winfo_children():
            w.destroy()
        insights = self._ai.insights()
        for i, ins in enumerate(insights):
            _insight_card(self._insights_inner, ins, i)

    def _populate_predictions(self):
        for w in self._pred_inner.winfo_children():
            w.destroy()
        self._pe._load()

        ctk.CTkLabel(
            self._pred_inner, text="Stockout Forecasts",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_SECONDARY, anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        preds = self._pe.stockout_predictions(30)
        if not preds:
            ctk.CTkLabel(
                self._pred_inner,
                text="No items predicted to stock out in the next 30 days.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=TEXT_MUTED,
            ).grid(row=1, column=0, sticky="w", pady=20)
        else:
            for i, p in enumerate(preds):
                self._pred_row(self._pred_inner, p, i + 1)

        # Velocity table
        ctk.CTkLabel(
            self._pred_inner, text="Consumption Velocity",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_SECONDARY, anchor="w",
        ).grid(row=len(preds) + 2, column=0, sticky="w", pady=(24, 8))

        items = self.db.get_all_items()
        vel_data = []
        for item in items:
            v = self._pe.velocity(item["barcode"])
            t = self._pe.trend(item["barcode"])
            if v > 0:
                vel_data.append((item["item_name"], item["current_quantity"], v, t))
        vel_data.sort(key=lambda x: x[2], reverse=True)

        base_row = len(preds) + 3
        if not vel_data:
            ctk.CTkLabel(
                self._pred_inner,
                text="No consumption data yet.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=TEXT_MUTED,
            ).grid(row=base_row, column=0, sticky="w")
        else:
            for i, (name, qty, v, tr) in enumerate(vel_data[:15]):
                self._vel_row(self._pred_inner, name, qty, v, tr, base_row + i)

    def _pred_row(self, parent, p: dict, row: int):
        urgency = (ACCENT_RED   if p["days_until_zero"] <= 3 else
                   ACCENT_AMBER if p["days_until_zero"] <= 7 else TEXT_MUTED)
        card = ctk.CTkFrame(
            parent, fg_color=BG_ELEVATED, corner_radius=10,
            border_width=1, border_color=BORDER_COLOR)
        card.grid(row=row, column=0, sticky="ew", pady=3)
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card, text=f"~{p['days_until_zero']}d",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=urgency, width=68,
        ).grid(row=0, column=0, rowspan=2, padx=(16, 8), pady=12)

        ctk.CTkLabel(
            card, text=p["item_name"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_PRIMARY, anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=(12, 2))

        trend_icon  = _TREND_ICONS.get(p.get("trend", "stable"), "→")
        trend_color = _TREND_COLORS.get(p.get("trend", "stable"), TEXT_MUTED)
        meta = (f"{p['current_quantity']} units  ·  "
                f"{p['velocity']}/day  ·  "
                f"to minimum in ~{p['days_until_min']}d  "
                f"{trend_icon}")
        ctk.CTkLabel(
            card, text=meta,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=trend_color, anchor="w",
        ).grid(row=1, column=1, sticky="w", pady=(0, 12))

        # Simple bar showing days remaining
        bar_width = min(int(p["days_until_zero"] / 30 * 200), 200)
        bar_bg = ctk.CTkFrame(card, fg_color=BG_OVERLAY, corner_radius=4,
                              width=200, height=4)
        bar_bg.grid(row=0, column=2, rowspan=2, padx=(0, 16), sticky="e")
        bar_bg.grid_propagate(False)
        ctk.CTkFrame(bar_bg, fg_color=urgency,
                     corner_radius=4, width=bar_width, height=4).place(x=0, y=0)

    def _vel_row(self, parent, name: str, qty: int,
                 velocity: float, trend: str, row: int):
        card = ctk.CTkFrame(
            parent, fg_color=BG_ELEVATED, corner_radius=8,
            border_width=1, border_color=BORDER_COLOR)
        card.grid(row=row, column=0, sticky="ew", pady=2)
        card.grid_columnconfigure(1, weight=1)

        t_icon  = _TREND_ICONS.get(trend, "→")
        t_color = _TREND_COLORS.get(trend, TEXT_MUTED)

        ctk.CTkLabel(
            card, text=t_icon, width=30,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=t_color,
        ).grid(row=0, column=0, padx=(14, 6), pady=9)

        ctk.CTkLabel(
            card, text=name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_PRIMARY, anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=9)

        ctk.CTkLabel(
            card, text=f"{velocity:.2f}/day  ·  {qty} units",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED, anchor="e",
        ).grid(row=0, column=2, padx=(0, 14), pady=9, sticky="e")

    def _populate_anomalies(self):
        for w in self._anom_inner.winfo_children():
            w.destroy()
        self._pe._load()
        row = 0

        def section(title, color=ACCENT_AMBER):
            nonlocal row
            ctk.CTkLabel(
                self._anom_inner, text=title,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                text_color=color, anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=(16, 6))
            row += 1

        # Shrinkage
        losses = self._pe.loss_indicators()
        section("Shrinkage / Loss Indicators", ACCENT_RED)
        if not losses:
            ctk.CTkLabel(
                self._anom_inner, text="No loss patterns detected.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_MUTED,
            ).grid(row=row, column=0, sticky="w"); row += 1
        else:
            for l in losses[:8]:
                card = ctk.CTkFrame(
                    self._anom_inner, fg_color=BG_ELEVATED,
                    corner_radius=8, border_width=1, border_color=BORDER_COLOR)
                card.grid(row=row, column=0, sticky="ew", pady=2)
                card.grid_columnconfigure(1, weight=1)
                ctk.CTkLabel(
                    card, text=f"×{l['ratio']}",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
                    text_color=ACCENT_RED, width=56,
                ).grid(row=0, column=0, rowspan=2, padx=(14, 6), pady=10)
                ctk.CTkLabel(
                    card, text=l["item_name"],
                    font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                    text_color=TEXT_PRIMARY, anchor="w",
                ).grid(row=0, column=1, sticky="w", pady=(10, 2))
                ctk.CTkLabel(
                    card,
                    text=(f"{l['total_out']} units out  ·  "
                          f"{l['total_in']} units in  ·  "
                          f"Net: −{l['net_loss']} units (30 days)"),
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                    text_color=ACCENT_RED, anchor="w",
                ).grid(row=1, column=1, sticky="w", pady=(0, 10))
                row += 1

        # Qty anomalies
        anom = self._pe.anomalous_transactions()
        section("Unusual Transaction Quantities")
        if not anom:
            ctk.CTkLabel(
                self._anom_inner, text="No statistical outliers detected.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_MUTED,
            ).grid(row=row, column=0, sticky="w"); row += 1
        else:
            for a in anom:
                card = ctk.CTkFrame(
                    self._anom_inner, fg_color=BG_ELEVATED,
                    corner_radius=8, border_width=1, border_color=BORDER_COLOR)
                card.grid(row=row, column=0, sticky="ew", pady=2)
                card.grid_columnconfigure(1, weight=1)
                ctk.CTkLabel(
                    card, text=f"z={a['z_score']}",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                    text_color=ACCENT_AMBER, width=56,
                ).grid(row=0, column=0, padx=(14, 6), pady=10)
                ctk.CTkLabel(
                    card,
                    text=(f"{a['item_name']}  —  {a['quantity']} units "
                          f"(avg {a['mean']})  ·  {a['username']}  ·  "
                          f"{a['timestamp'][:16]}"),
                    font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                    text_color=TEXT_PRIMARY, anchor="w",
                ).grid(row=0, column=1, sticky="w", padx=(0, 14), pady=10)
                row += 1

        # Duplicate scans
        dupes = self._pe.duplicate_scans()
        section("Possible Duplicate Scans")
        if not dupes:
            ctk.CTkLabel(
                self._anom_inner, text="No duplicate scans detected.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_MUTED,
            ).grid(row=row, column=0, sticky="w"); row += 1
        else:
            for d in dupes:
                card = ctk.CTkFrame(
                    self._anom_inner, fg_color=BG_ELEVATED,
                    corner_radius=8, border_width=1, border_color=BORDER_COLOR)
                card.grid(row=row, column=0, sticky="ew", pady=2)
                card.grid_columnconfigure(1, weight=1)
                ctk.CTkLabel(
                    card,
                    text=(f"{d['item_name']}  —  {d['username']}  ·  "
                          f"{d['timestamp'][:16]}  ·  gap: {d['gap_seconds']}s"),
                    font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                    text_color=TEXT_PRIMARY, anchor="w",
                ).grid(row=0, column=0, padx=14, pady=10)
                row += 1

        # After-hours
        ah = self._pe.after_hours_transactions()
        section("After-Hours Transactions (outside 07:00–19:00)")
        if not ah:
            ctk.CTkLabel(
                self._anom_inner, text="No after-hours transactions found.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_MUTED,
            ).grid(row=row, column=0, sticky="w"); row += 1
        else:
            for t in ah:
                card = ctk.CTkFrame(
                    self._anom_inner, fg_color=BG_ELEVATED,
                    corner_radius=8, border_width=1, border_color=BORDER_COLOR)
                card.grid(row=row, column=0, sticky="ew", pady=2)
                card.grid_columnconfigure(1, weight=1)
                ctk.CTkLabel(
                    card,
                    text=(f"{t['item_name']}  ·  {t['transaction_type']}  ·  "
                          f"{t['username']}  ·  {t['timestamp'][:16]}"),
                    font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                    text_color=TEXT_PRIMARY, anchor="w",
                ).grid(row=0, column=0, padx=14, pady=10)
                row += 1

        # User anomalies
        u_anom = self._pe.user_anomalies()
        section("User Volume Anomalies")
        if not u_anom:
            ctk.CTkLabel(
                self._anom_inner,
                text="No unusual user behaviour detected.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_MUTED,
            ).grid(row=row, column=0, sticky="w"); row += 1
        else:
            for u in u_anom:
                card = ctk.CTkFrame(
                    self._anom_inner, fg_color=BG_ELEVATED,
                    corner_radius=8, border_width=1, border_color=BORDER_COLOR)
                card.grid(row=row, column=0, sticky="ew", pady=2)
                card.grid_columnconfigure(1, weight=1)
                ctk.CTkLabel(
                    card, text=u["username"],
                    font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                    text_color=TEXT_PRIMARY, anchor="w",
                ).grid(row=0, column=0, padx=14, pady=(10, 2), sticky="w")
                ctk.CTkLabel(
                    card,
                    text=(f"{u['ratio']}× normal  ·  "
                          f"Recent avg: {u['recent_avg']} units/day  ·  "
                          f"Historical: {u['historical_avg']} units/day"),
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                    text_color=ACCENT_AMBER, anchor="w",
                ).grid(row=1, column=0, padx=14, pady=(0, 10), sticky="w")
                row += 1

    # ------------------------------------------------------------------
    # Ask Ava
    # ------------------------------------------------------------------

    def _ask_preset(self, question: str):
        self._switch_tab("ask")
        self._q_var.set(question)
        self._ask()

    def _ask(self):
        q = self._q_var.get().strip()
        if not q:
            return
        self._q_var.set("")
        self._add_chat_bubble(q, is_user=True)
        # Show a placeholder bubble immediately so users see progress,
        # then run answer() off the Tk main thread. Otherwise the whole
        # window freezes for seconds while the AI/database work happens.
        self._add_chat_bubble("…thinking…", is_user=False)
        thinking_row = self._chat_row - 1  # row of the placeholder we just added

        result: dict = {"answer": None}
        done = threading.Event()

        def _worker():
            try:
                result["answer"] = self._ai.answer(q)
            except Exception as exc:  # noqa: BLE001
                result["answer"] = f"Sorry, I hit an error: {exc}"
            finally:
                done.set()

        threading.Thread(target=_worker, daemon=True).start()

        def _poll():
            try:
                if not self.winfo_exists():
                    return
            except Exception:
                return
            if not done.is_set():
                self.after(80, _poll)
                return
            try:
                self._replace_chat_bubble(
                    thinking_row, result["answer"] or "(no response)"
                )
            except Exception:
                pass

        self.after(80, _poll)

    def _replace_chat_bubble(self, row: int, text: str) -> None:
        """Replace the text in an existing bot chat bubble (used to swap
        the '…thinking…' placeholder for the actual answer)."""
        for child in self._chat_log.grid_slaves(row=row):
            child.destroy()
        prev_row = self._chat_row
        self._chat_row = row
        self._add_chat_bubble(text, is_user=False)
        self._chat_row = prev_row

    def _add_chat_bubble(self, text: str, is_user: bool):
        fg  = ACCENT if is_user else BG_OVERLAY
        fg2 = BG_BASE if is_user else TEXT_PRIMARY
        anchor = "e" if is_user else "w"

        outer = ctk.CTkFrame(self._chat_log, fg_color="transparent")
        outer.grid(row=self._chat_row, column=0, sticky="ew", pady=4)
        outer.grid_columnconfigure(0, weight=1)

        bubble = ctk.CTkFrame(outer, fg_color=fg, corner_radius=10)
        bubble.grid(row=0, column=0, sticky=anchor, padx=10)

        ctk.CTkLabel(
            bubble, text=text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=fg2, wraplength=460,
            justify="left", padx=12, pady=9,
        ).pack()

        self._chat_row += 1
