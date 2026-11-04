"""TPG HR Agent (Vision) - Streamlit UI. Run: RUN_VISION.bat  (port 8518).

No API request is made unless the user ticks the data-transfer consent AND presses the
start button. Everything else (scoring, reweighting, review, Excel) is local.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import hr_vision_core as C

load_dotenv(C.ROOT / ".env")
st.set_page_config(page_title="TPG HR Agent - Vision", page_icon="📋", layout="wide")
st.markdown("""<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {direction: rtl; font-family: Tahoma, "Vazirmatn", sans-serif;}
textarea, input {direction: rtl;} [data-testid="stDataFrame"], code, pre {direction: ltr;}
</style>""", unsafe_allow_html=True)

INBOX = C.ROOT / "inbox"
STATE_FA = {"new": "جدید - نیازمند API", "cached": "ذخیره‌شده - بدون API", "cached_failed": "پاسخ ذخیره‌شده ناخوانا",
            "cached_other": "تحلیل‌شده با مدل/نسخه دیگر", "duplicate": "تکراری در همین فهرست"}


@st.cache_resource
def get_con():
    con = C.db_connect()
    C.seed_positions(con)
    return con


con = get_con()
positions = C.list_positions(con)


def pick_position(label, key):
    if not positions:
        st.warning("هیچ سمتی تعریف نشده است؛ از تب «سمت‌ها» یکی بسازید.")
        return None
    ids = [p["id"] for p in positions]
    pid = st.selectbox(label, ids, key=key, format_func=lambda i: next(p["title"] for p in positions if p["id"] == i))
    return next(p for p in positions if p["id"] == pid)


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown(f"**TPG HR Agent Vision** `{C.APP_VERSION}`")
    key_ok = bool(os.getenv("GAPGPT_API_KEY"))
    st.caption("کلید API: " + ("✅ در .env تنظیم است" if key_ok else "❌ تنظیم نشده (فایل .env)"))
    base_url = st.text_input("نشانی پایه API", os.getenv("GAPGPT_BASE_URL", ""), type="default")
    model = st.selectbox("مدل (باید ورودی تصویر را پشتیبانی کند)", list(C.MODELS), index=0)
    with st.expander("تنظیمات تصویر صفحات"):
        st.caption("تغییر این‌ها کلید حافظه نهان را عوض می‌کند و برای فایل‌های قبلی تحلیل جدید (هزینه‌دار) لازم می‌شود.")
        render = {"dpi": st.slider("DPI", 80, 200, C.DEFAULT_RENDER["dpi"], 10),
                  "max_side": st.slider("حداکثر ضلع بلند (px)", 1000, 2400, C.DEFAULT_RENDER["max_side"], 100),
                  "quality": st.slider("کیفیت JPEG", 50, 95, C.DEFAULT_RENDER["quality"], 5),
                  "max_pages": st.slider("حداکثر صفحات هر رزومه", 1, 12, C.DEFAULT_RENDER["max_pages"])}
    st.caption("نرخ‌های هزینه تخمینی و تأییدنشده‌اند.")

tab_pos, tab_run, tab_res, tab_out = st.tabs(["۱. سمت‌ها", "۲. تحلیل رزومه‌ها", "۳. نتایج و رتبه‌بندی", "۴. خروجی و گزارش مصرف"])

# ------------------------------------------------------------------ positions
with tab_pos:
    st.subheader("مدیریت سمت‌های شغلی")
    opts = ["➕ سمت جدید"] + [p["id"] for p in positions]
    sel = st.selectbox("سمت برای ویرایش", opts, key="edit_pid",
                       format_func=lambda i: i if i.startswith("➕") else f"{i} — {next(p['title'] for p in positions if p['id'] == i)}")
    cur = C.new_position_template() if sel.startswith("➕") else json.loads(json.dumps(C.get_position(con, sel)))
    up = st.file_uploader("درون‌ریزی سمت از JSON", key="pos_json")
    if up is not None and st.button("اعتبارسنجی و ذخیره JSON درون‌ریزی‌شده"):
        try:
            imp = json.loads(up.getvalue().decode("utf-8"))
            for p in (imp["positions"] if isinstance(imp, dict) and "positions" in imp else [imp]):
                C.save_position(con, p)
            st.success("ذخیره شد.")
            st.rerun()
        except Exception as e:
            st.error(f"JSON نامعتبر: {e}")
    with st.form(f"pos_form_{sel}"):
        c1, c2, c3 = st.columns(3)
        pid = c1.text_input("شناسه (a-z، 0-9، _)", cur["id"], disabled=not sel.startswith("➕"))
        code = c2.text_input("پیشوند شناسه متقاضی", cur["code"])
        title = c3.text_input("عنوان سمت", cur["title"])
        desc = st.text_area("شرح شغل (برای مدل ارسال می‌شود)", cur.get("description", ""), height=220)
        instr = st.text_area("دستورالعمل ارزیابی اختصاصی این سمت", cur.get("instructions", ""), height=220)
        th = cur["grade_thresholds"]
        t1, t2, t3 = st.columns(3)
        thA = t1.number_input("آستانه A", value=float(th["A"]))
        thB = t2.number_input("آستانه B", value=float(th["B"]))
        thC = t3.number_input("آستانه C", value=float(th["C"]))
        st.markdown("**معیارها و وزن‌ها** (جمع وزن‌ها باید ۱۰۰ باشد؛ تغییر وزن نیازی به تحلیل مجدد ندارد)")
        crit_df = st.data_editor(pd.DataFrame([{"criterion_id": c["id"], "label": c["label"], "weight": c["weight"]} for c in cur["criteria"]]),
                                 num_rows="dynamic", key=f"ed_crit_{sel}")
        st.markdown("**زیرمعیارها** (criterion_id باید با جدول بالا یکی باشد)")
        sub_df = st.data_editor(pd.DataFrame([{"criterion_id": c["id"], "sub_id": s["id"], "label": s["label"],
                                               "allow_course": bool(s.get("allow_course"))}
                                              for c in cur["criteria"] for s in c["subcriteria"]]), num_rows="dynamic", key=f"ed_sub_{sel}")
        st.markdown("**شرایط اولیه** (بدون امتیاز)")
        cond_df = st.data_editor(pd.DataFrame(cur.get("conditions") or [], columns=["id", "label"]), num_rows="dynamic", key=f"ed_cond_{sel}")
        st.markdown("**مسیرهای سابقه** (min_months اختیاری)")
        trk_df = st.data_editor(pd.DataFrame(cur.get("experience_tracks") or [], columns=["id", "label", "min_months"]),
                                num_rows="dynamic", key=f"ed_trk_{sel}")
        st.markdown("**سؤالات مشترک مصاحبه**")
        q_df = st.data_editor(pd.DataFrame(cur.get("common_questions") or [], columns=["question", "purpose"]), num_rows="dynamic", key=f"ed_q_{sel}")
        saved = st.form_submit_button("اعتبارسنجی و ذخیره سمت")
    if saved:
        def rows(df):
            return [{k: (None if pd.isna(v) else v) for k, v in r.items()} for r in df.to_dict("records")]
        crits = []
        for r in rows(crit_df):
            if not r["criterion_id"]:
                continue
            crits.append({"id": str(r["criterion_id"]).strip(), "label": str(r["label"] or "").strip(), "weight": r["weight"],
                          "subcriteria": [{"id": str(s["sub_id"]).strip(), "label": str(s["label"] or "").strip(),
                                           "allow_course": bool(s["allow_course"])}
                                          for s in rows(sub_df) if s["sub_id"] and str(s["criterion_id"]).strip() == str(r["criterion_id"]).strip()]})
        orphans = {str(s["criterion_id"]) for s in rows(sub_df) if s["sub_id"]} - {c["id"] for c in crits}
        new = {**cur, "id": pid.strip(), "code": code.strip(), "title": title.strip(), "description": desc, "instructions": instr,
               "grade_thresholds": {"A": thA, "B": thB, "C": thC}, "criteria": crits,
               "conditions": [{"id": str(r["id"]).strip(), "label": str(r["label"] or "")} for r in rows(cond_df) if r["id"]],
               "experience_tracks": [{"id": str(r["id"]).strip(), "label": str(r["label"] or ""),
                                      "min_months": None if r["min_months"] is None else float(r["min_months"])}
                                     for r in rows(trk_df) if r["id"]],
               "common_questions": [{"question": str(r["question"] or ""), "purpose": str(r["purpose"] or "")}
                                    for r in rows(q_df) if r["question"]]}
        errs = C.validate_position(new) + [f"زیرمعیار برای معیار ناموجود: {o}" for o in orphans]
        if errs:
            for e in errs:
                st.error(e)
        else:
            old = None if sel.startswith("➕") else C.get_position(con, sel)
            C.save_position(con, new)
            if old and C.prompt_hash(old) != C.prompt_hash(new):
                st.warning("شرح/دستورالعمل/ساختار معیارها تغییر کرد؛ نتایج قبلی حفظ می‌شوند اما «نسخه قدیمی» علامت می‌خورند و تحلیل جدید فقط با تأیید شما انجام می‌شود.")
            else:
                st.success("ذخیره شد (بدون نیاز به تحلیل مجدد).")
            st.rerun()
    if not sel.startswith("➕"):
        b1, b2 = st.columns(2)
        b1.download_button("خروجی JSON این سمت", json.dumps(cur, ensure_ascii=False, indent=1), file_name=f"{sel}.json", mime="application/json")
        if b2.button("بایگانی این سمت (نتایج حذف نمی‌شوند)"):
            C.archive_position(con, sel)
            st.rerun()

# ------------------------------------------------------------------ analysis
with tab_run:
    st.subheader("بارگذاری و تحلیل")
    pos = pick_position("سمت هدف", "pos_run")
    if pos:
        ups = st.file_uploader("رزومه‌ها (PDF، Word، تصویر) — همه قالب‌ها پذیرفته می‌شوند و محتوا در برنامه بررسی می‌شود",
                               accept_multiple_files=True, key="uploader")
        use_inbox = st.checkbox(f"خواندن فایل‌ها از پوشه {INBOX.name}/ (اگر بارگذاری مرورگر مشکل داشت)")
        raw_files = [(u.name, u.getvalue()) for u in (ups or [])]
        if use_inbox and INBOX.exists():
            raw_files += [(f.name, f.read_bytes()) for f in sorted(INBOX.iterdir()) if f.is_file() and not f.name.startswith(".")]
        infos, errors = [], []
        for name, data in raw_files:
            try:
                infos.append(C.store_file(con, name, data))
            except C.DocError as e:
                errors.append((name, str(e)))
            except Exception as e:
                errors.append((name, f"خطای ناشناخته در خواندن فایل: {str(e)[:150]}"))
        for n, e in errors:
            st.error(f"{n}: {e}")
        if infos:
            st.markdown("**بررسی محلی فایل‌ها (بدون API)**")
            st.dataframe(pd.DataFrame([{"فایل": i["name"], "نوع": i["kind"], "صفحه": i["page_count"],
                                        "صفحات با متن معتبر": sum(1 for p in i["pages"].values() if p["ok"]),
                                        "حجم KB": i["size"] // 1024, "SHA": i["sha"][:8], "هشدار": "؛ ".join(i["warnings"])} for i in infos]))
            plan = C.plan_batch(con, pos, infos, model, render)
            redo = st.multiselect("تحلیل مجدد با API (هزینه‌دار؛ فقط فایل‌های ذخیره‌شده با مدل/نسخه دیگر یا ناخوانا)",
                                  [p["name"] for p in plan if p["state"] in ("cached_other", "cached_failed")])
            todo = [p for p in plan if p["state"] == "new" or (p["state"] in ("cached_other", "cached_failed") and p["name"] in redo)]
            st.dataframe(pd.DataFrame([{"فایل": p["name"], "وضعیت": STATE_FA[p["state"]], "تخمین توکن ورودی": p["tokens_in"],
                                        "هزینه تخمینی USD": round(p["cost"], 4)} for p in plan]))
            tot = sum(p["cost"] for p in todo)
            st.info(f"درخواست API لازم: **{len(todo)}** از {len(plan)} فایل — هزینه تخمینی ≈ {tot:.3f} دلار (نرخ و مصرف تصویر تأییدنشده)")
            if todo:
                limit = st.number_input("سقف تعداد درخواست در این اجرا", 1, 200, min(len(todo), 10))
                consent = st.checkbox("با ارسال تصویر صفحات رزومه‌های فهرست‌شده (شامل اطلاعات شخصی) به سرویس API موافقم")
                confirm = st.checkbox(f"{min(len(todo), int(limit))} درخواست هزینه‌دار را تأیید می‌کنم")
                if st.button("شروع تحلیل", disabled=not (consent and confirm and key_ok and base_url) or st.session_state.get("running", False)):
                    st.session_state["running"] = True
                    try:
                        client = C.make_client(os.getenv("GAPGPT_API_KEY", ""), base_url)
                        prog, fails, done = st.progress(0.0), 0, 0
                        batch = todo[:int(limit)]
                        for i, p in enumerate(batch, 1):
                            info = next(x for x in infos if x["sha"] == p["sha"])
                            try:
                                r = C.analyze_file(con, client, pos, model, info, render, force=p["state"] != "new")
                                st.write(f"✅ {p['name']}" + (" (از حافظه)" if r["cached"] else f" — هزینه تخمینی {r.get('cost', 0):.4f}$"))
                                if r.get("finish") == "length":
                                    st.warning(f"{p['name']}: خروجی مدل قطع شد؛ ممکن است ناقص باشد.")
                                fails = 0
                            except Exception as e:
                                fails += 1
                                st.error(f"❌ {p['name']}: {str(e)[:300]}")
                                if fails >= 3:
                                    st.error("سه خطای پیاپی؛ اجرا متوقف شد تا اعتبار هدر نرود. کلید/مدل/پشتیبانی تصویر را بررسی کنید.")
                                    break
                            prog.progress(i / len(batch))
                    finally:
                        st.session_state["running"] = False
                    st.success("پایان اجرا. نتایج در تب ۳ و ذخیره‌شده‌اند.")

# ------------------------------------------------------------------ results
def page_preview(sha, n):
    row = con.execute("SELECT * FROM files WHERE sha=?", (sha,)).fetchone()
    info = C.file_info(row)
    if info["kind"] == "docx":
        st.text(info["pages"].get(n, {}).get("text", ""))
        return
    pages = C.render_pages(Path(info["path"]).read_bytes(), info["kind"], {**render, "max_pages": max(n, render["max_pages"])})
    for p in pages:
        if p["n"] == n:
            st.image(p["jpeg"])


with tab_res:
    st.subheader("نتایج، تحلیل گروهی و بازبینی")
    pos = pick_position("سمت", "pos_res")
    results = C.load_results(con, pos) if pos else []
    if pos and not results:
        st.info("برای این سمت هنوز تحلیلی ذخیره نشده است.")
    if results:
        g = C.group_analysis(results, pos)
        m = st.columns(6)
        m[0].metric("کل", g["total"]); m[1].metric("رتبه‌دار", g["valid"]); m[2].metric("ناقص/خطا", g["incomplete"])
        m[3].metric("میانگین", g["score_mean"]); m[4].metric("میانه", g["score_median"]); m[5].metric("نیازمند بازبینی", len(g["needs_review"]))
        st.bar_chart(pd.DataFrame({"تعداد": g["grades"]}))
        st.dataframe(pd.DataFrame([{"معیار": c["label"], "وزن": c["weight"], "میانگین": c["mean"], "بیشترین": c["best"],
                                    "بهترین": "، ".join(c["best_ids"])} for c in g["criteria"]]))
        if g["close_pairs"]:
            st.caption("امتیازهای نزدیک (<۲): " + "؛ ".join(f"{a}/{b} ({d})" for a, b, d in g["close_pairs"]))
        st.dataframe(pd.DataFrame([{"رتبه": r["rank"], "شناسه": r["stable_id"], "نام": r["candidate_name"], "امتیاز": r["score"],
                                    "گروه": r.get("group_label"), "وضعیت": r["status"], "کفایت": r["sufficiency"],
                                    "سابقه کل": C.months_text((r["experience"].get("total") or {}).get("months")) if r["experience"] else "",
                                    "مغایرت": r["mismatch_count"], "فقط تصویری": r["visual_only_count"],
                                    "اصلاح دستی": "✓" if r["manual_edits"] else "", "نسخه قدیمی": "✓" if r["stale"] else "",
                                    "فایل": r["file_name"]} for r in results]))
        sid = st.selectbox("بررسی جزئیات متقاضی", [r["stable_id"] for r in results],
                           format_func=lambda s: f"{s} — {next(r['candidate_name'] for r in results if r['stable_id'] == s)}")
        r = next(x for x in results if x["stable_id"] == sid)
        if r["stale"]:
            st.warning("این نتیجه با نسخه قدیمی شرح/دستورالعمل سمت تولید شده است.")
        for i in r["issues"]:
            st.warning(i)
        st.markdown(f"**امتیاز:** {r['score']} — **گروه:** {r.get('group_label')} — **خلاصه:** {r['summary']}")
        st.dataframe(pd.DataFrame([{"معیار": c["label"], "وزن": c["weight"], "میانگین سطح": c["mean_level"], "امتیاز": c["points"]} for c in r["criteria"]]))
        for s in r["subs"]:
            with st.expander(f"{s['label']} — مدل: {s['claimed']} | مؤثر: {s['effective']} {'⚠️' if s['flags'] else ''}"):
                st.write(s["claim"])
                for f in s["flags"]:
                    st.caption("⚠️ " + f)
                for j, e in enumerate(s["evidence"]):
                    st.markdown(f"> {e['quote']}  \nصفحه {e['page']} — **{C.STATUS_FA.get(e['status'], e['status'])}** {e.get('note', '')}")
                    if e.get("found_page") or e.get("page"):
                        if st.checkbox(f"نمایش صفحه {e.get('found_page') or e['page']}", key=f"pv_{sid}_{s['sub_id']}_{j}"):
                            try:
                                page_preview(r["file_sha"], int(e.get("found_page") or e["page"]))
                            except Exception as ex:
                                st.error(f"نمایش صفحه ممکن نشد: {ex}")
        st.markdown("**سوابق شغلی** (ماه‌های هم‌پوشان یک‌بار شمرده شده‌اند)")
        st.dataframe(pd.DataFrame([{"#": j["index"], "کارفرما": j["employer"], "سمت": j["role"], "شروع": j["start"], "پایان": j["end"], "ماه": j["months"],
                                    "مسیرها": "، ".join(j["tracks"]), "در محاسبه": "✓" if j["counted"] else "✗",
                                    "نقل‌قول": C.STATUS_FA.get(j["evidence_status"], ""), "توضیح": j["note"]} for j in r["history"]]))
        st.dataframe(pd.DataFrame([{"مسیر": v["label"], "اجتماع بازه‌ها": C.months_text(v["months"]), "جمع ساده": v["naive_months"],
                                    "هم‌پوشان حذف‌شده (ماه)": v["overlap_months"]} for v in (r["experience"] or {}).values()]))
        st.dataframe(pd.DataFrame([{"شرط": c["label"], "وضعیت": c["status"], "توضیح": c["note"]} for c in r["conditions"]] +
                                  [{"شرط": "حداقل سابقه: " + m["track"], "وضعیت": m["status"], "توضیح": m["note"]} for m in r["min_checks"]]))
        a, b = st.columns(2)
        a.markdown("**نقاط قوت**\n\n" + "\n".join(f"- {s['text']}" + ("" if s["documented"] else " *(مستندنشده)*") for s in r["strengths"]))
        b.markdown("**ابهامات**\n\n" + "\n".join(f"- {u}" for u in r["uncertainties"]))
        st.markdown("**سؤالات مصاحبه**")
        for q in r["interview_questions"]:
            st.markdown(f"- ({q['type']}) {q['question']}" + (f"  \n  هدف: {q['purpose']}" if q["purpose"] else ""))
        with st.expander("اصلاح دستی (بدون تحلیل مجدد و بدون هزینه API)"):
            kind = st.selectbox("نوع اصلاح", ["سطح زیرمعیار", "تأیید/ردّ شاهد", "تاریخ/مسیر شغل", "نام متقاضی", "وضعیت شرط"], key="rv_kind")
            note = st.text_input("یادداشت (الزامی برای ردیابی)", key="rv_note")
            sha, pid_ = r["file_sha"], pos["id"]
            apply = None
            if kind == "سطح زیرمعیار":
                s_ = st.selectbox("زیرمعیار", [s["sub_id"] for s in r["subs"]], key="rv_sub")
                lv = st.selectbox("سطح جدید", [0, 1, 2, 3, 4], key="rv_lv")
                apply = (f"sub:{s_}", "level", lv)
            elif kind == "تأیید/ردّ شاهد":
                s_ = st.selectbox("زیرمعیار", [s["sub_id"] for s in r["subs"] if s["evidence"]], key="rv_sub2")
                n_ev = len(next(s for s in r["subs"] if s["sub_id"] == s_)["evidence"])
                idx = st.selectbox("شماره شاهد", list(range(n_ev)), key="rv_ev")
                dec = st.radio("تصمیم", ["confirm", "reject"], horizontal=True, key="rv_dec")
                apply = (f"ev:{s_}:{idx}", "decision", dec)
            elif kind == "تاریخ/مسیر شغل":
                if r["history"]:
                    j = st.selectbox("شغل #", [h["index"] for h in r["history"]], key="rv_job")
                    fld = st.selectbox("فیلد", ["start", "end", "tracks", "decision"], key="rv_fld")
                    val = st.text_input("مقدار (تاریخ YYYY/MM؛ مسیرها با ویرگول؛ decision: confirm/reject)", key="rv_val")
                    apply = (f"hist:{j}", fld, val)
            elif kind == "نام متقاضی":
                apply = ("name", "value", st.text_input("نام", r["candidate_name"], key="rv_name"))
            else:
                if r["conditions"]:
                    cid = st.selectbox("شرط", [c["id"] for c in r["conditions"]], key="rv_cond")
                    apply = (f"cond:{cid}", "status", st.selectbox("وضعیت", list(C.CONDITION_STATES), key="rv_cst"))
            c1, c2 = st.columns(2)
            if c1.button("ثبت اصلاح") and apply:
                if not note.strip():
                    st.error("یادداشت لازم است.")
                else:
                    C.save_review(con, sha, pid_, apply[0], apply[1], apply[2], note)
                    st.rerun()
            if c2.button("بازگردانی همین اصلاح به خروجی مدل") and apply:
                C.save_review(con, sha, pid_, apply[0], apply[1], None, "بازگردانی")
                st.rerun()

# ------------------------------------------------------------------ export
with tab_out:
    st.subheader("خروجی اکسل فارسی و مصرف API")
    pos = pick_position("سمت", "pos_out")
    if pos:
        res = C.load_results(con, pos)
        if res and st.button("ساخت فایل اکسل (محلی)"):
            st.session_state["xlsx"] = (pos["id"], C.export_excel(res, pos))
        if st.session_state.get("xlsx", (None,))[0] == pos["id"]:
            st.download_button("دانلود اکسل", st.session_state["xlsx"][1], file_name=f"TPG_{pos['code']}_{C.now_iso()[:10]}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    log = pd.read_sql_query("SELECT ts, model, status, tokens_in, tokens_out, error FROM api_log ORDER BY id DESC LIMIT 200", con)
    ok = log[log["status"].isin(["ok", "truncated"])]
    st.metric("درخواست‌های موفق ثبت‌شده", len(ok))
    st.dataframe(log)
    st.caption(f"داده‌ها: {C.DB_PATH} — برای پشتیبان‌گیری پوشه data/ را کپی کنید.")
