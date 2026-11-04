"""Offline tests: no network, no real API. Run: python -m unittest discover -s tests -v"""
import io, json, sys, tempfile, unittest, copy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hr_vision_core as C

TMP = Path(tempfile.mkdtemp())
C.FILES_DIR = TMP / "files"

CV_FA = [
    "نام: علی رضایی",
    "کارشناس ایمنی پروژه مترو - شرکت نمونه از 1398/04 تا 1401/06",
    "در این پروژه بازرسی روزانه گودبرداری و کنترل مجوز کار را انجام دادم و گزارش حوادث را تهیه کردم.",
    "ناظر ایمنی پروژه برج - شرکت دوم از 1400/01 تا اکنون",
    "برگزاری جلسات Toolbox Talk برای نیروهای اجرایی و پیگیری اقدامات اصلاحی.",
    "کارشناسی مهندسی ایمنی صنعتی، دانشگاه تهران 1395",
    "تسلط به Word و Excel برای تهیه گزارش های روزانه",
]


def make_docx(lines):
    from docx import Document
    d = Document()
    for l in lines:
        d.add_paragraph(l)
    b = io.BytesIO(); d.save(b); return b.getvalue()


def make_text_pdf(lines, password=None):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import pdfencrypt
    b = io.BytesIO()
    enc = pdfencrypt.StandardEncryption(password, canPrint=1) if password else None
    c = canvas.Canvas(b, pagesize=A4, encrypt=enc)
    y = 800
    for l in lines:
        c.drawString(50, y, l); y -= 20
    c.save(); return b.getvalue()


def make_scan_pdf():
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (1240, 1754), "white")
    ImageDraw.Draw(img).text((100, 100), "scanned page", fill="black")
    b = io.BytesIO(); img.save(b, "PDF", resolution=150); return b.getvalue()


def pos2():
    p = C.new_position_template("ctrl", "کارشناس کنترل پروژه")
    p["code"] = "CTRL"
    p["description"] = "کنترل پروژه"
    p["criteria"] = [
        {"id": "k1", "label": "برنامه‌ریزی", "weight": 60.0, "subcriteria": [
            {"id": "k1_a", "label": "تهیه برنامه زمانی", "allow_course": False},
            {"id": "k1_b", "label": "نرم‌افزار", "allow_course": True}]},
        {"id": "k2", "label": "گزارش‌دهی", "weight": 40.0, "subcriteria": [
            {"id": "k2_a", "label": "گزارش پیشرفت", "allow_course": False}]}]
    p["experience_tracks"] = [{"id": "pc", "label": "کنترل پروژه", "min_months": 12}]
    return p


class FakeClient:
    def __init__(self, builder):
        self.builder, self.calls = builder, 0
        self.chat = self
        self.completions = self

    def create(self, **kw):
        self.calls += 1
        self.last = kw
        raw = self.builder(kw)
        class M: pass
        m = M(); m.content = raw
        ch = M(); ch.message = m; ch.finish_reason = "stop"
        u = M(); u.prompt_tokens = 1000; u.completion_tokens = 500
        r = M(); r.choices = [ch]; r.usage = u
        return r


def hse_answer(levels=None, quote_ok=True):
    levels = levels or {}
    subs = []
    P = C.get_position  # noqa
    pos = json.loads(Path(C.POLICY_FILE).read_text(encoding="utf8"))["positions"][0]
    for c, s in C.all_subs(pos):
        lv = levels.get(s["id"], 0)
        q = "بازرسی روزانه گودبرداری و کنترل مجوز کار را انجام دادم" if quote_ok else "عبارتی که هرگز در رزومه نبوده است اصلاً"
        subs.append({"sub_id": s["id"], "level": lv, "evidence_kind": "action" if lv else "none", "claim": "ادعا",
                     "evidence": [{"quote": q, "page": 1}] if lv else []})
    return json.dumps({
        "candidate_name": "علی رضایی", "legibility": "خوب", "information_sufficiency": "کافی", "subcriteria": subs,
        "employment_history": [
            {"employer": "الف", "role": "HSE", "start": "1398/04", "end": "1401/06", "tracks": ["hse", "construction"],
             "activity": "x", "quote": "کارشناس ایمنی پروژه مترو - شرکت نمونه از 1398/04 تا 1401/06", "page": 1},
            {"employer": "ب", "role": "HSE", "start": "1400/01", "end": "اکنون", "tracks": ["hse"],
             "activity": "y", "quote": "ناظر ایمنی پروژه برج - شرکت دوم از 1400/01 تا اکنون", "page": 1}],
        "conditions": {"degree_training": {"status": "احراز مستند", "note": "", "quote": "کارشناسی مهندسی ایمنی صنعتی، دانشگاه تهران 1395", "page": 1}},
        "strengths": [{"text": "بازرسی گود", "quote": "بازرسی روزانه گودبرداری", "page": 1}],
        "uncertainties": ["نوع پروژه مبهم"],
        "interview_questions": [{"question": "q1", "purpose": "p"}, {"question": "q2", "purpose": "p"}, {"question": "q3", "purpose": "p"}],
        "summary": "s"}, ensure_ascii=False)


class TestText(unittest.TestCase):
    pages = {1: {"text": "ك\u200cار با ۱۳۹۸ كارشناس ايمنی پروژه مترو و گودبرداری عمیق را انجام دادم و گزارش تهیه كردم", "ok": True}}

    def test_normalization_variants_exact(self):
        v = C.verify_quote("کار با 1398 کارشناس ایمنی پروژه مترو", 1, self.pages)
        self.assertEqual(v["status"], "verified_exact")

    def test_ellipsis_fragments(self):
        v = C.verify_quote("کارشناس ایمنی پروژه مترو ... گزارش تهیه کردم", 1, self.pages)
        self.assertEqual(v["status"], "verified_exact")

    def test_real_mismatch_not_hidden(self):
        v = C.verify_quote("مسئول ایمنی کارگاه سد با تجربه ده ساله", 1, self.pages)
        self.assertEqual(v["status"], "mismatch")

    def test_paraphrase_with_different_words_is_mismatch(self):
        v = C.verify_quote("بازرس ارشد ایمنی در پروژه قطار شهری فعالیت داشت", 1, self.pages)
        self.assertEqual(v["status"], "mismatch")

    def test_unreadable_text_layer_is_visual_only_not_verified(self):
        v = C.verify_quote("هر عبارت دلخواه با طول کافی برای آزمون", 1, {1: {"text": "", "ok": False}})
        self.assertEqual(v["status"], "visual_only")
        self.assertNotIn(v["status"], ("verified_exact", "verified_approx"))

    def test_wrong_page_cited_but_found(self):
        pg = {1: {"text": "x" * 80, "ok": True}, 2: self.pages[1]}
        v = C.verify_quote("کارشناس ایمنی پروژه مترو", 1, pg)
        self.assertEqual((v["status"], v["found_page"]), ("verified_exact", 2))

    def test_short_or_empty_quote(self):
        self.assertEqual(C.verify_quote("", 1, self.pages)["status"], "no_quote")
        self.assertEqual(C.verify_quote("کار", 1, self.pages)["status"], "no_quote")

    def test_health_detector(self):
        self.assertFalse(C.page_text_health("")[0])
        self.assertFalse(C.page_text_health("(cid:12)(cid:13) " * 30)[0])
        self.assertTrue(C.page_text_health(" ".join(["کارشناس ایمنی پروژه ساختمانی"] * 6))[0])


class TestDatesExperience(unittest.TestCase):
    def test_jalali(self):
        self.assertEqual(C.gregorian_to_jalali(2026, 3, 21), (1405, 1, 1))
        self.assertEqual(C.gregorian_to_jalali(2026, 10, 25), (1405, 8, 3))

    def test_union_no_double_count(self):
        self.assertEqual(C.union_months([(1, 12), (6, 18), (30, 31)]), 18 + 2)
        self.assertEqual(C.union_months([(1, 10), (3, 5)]), 10)
        self.assertEqual(C.union_months([(1, 5), (6, 9)]), 9)  # adjacent months merge

    def test_parse(self):
        a = (1405, 8)
        self.assertEqual(C.parse_jmonth("۱۳۹۸/۰۴", a)[0], 1398 * 12 + 3)
        self.assertEqual(C.parse_jmonth("اکنون", a)[0], 1405 * 12 + 7)
        self.assertIsNone(C.parse_jmonth("1398", a)[0])   # year only: never guessed
        self.assertIsNone(C.parse_jmonth("نامشخص", a)[0])
        self.assertIsNone(C.parse_jmonth("2019/05", a)[0])


class TestFiles(unittest.TestCase):
    def test_docx_text_pdf_scan_and_errors(self):
        d = C.inspect_document("a.docx", make_docx(CV_FA))
        self.assertEqual(d["kind"], "docx")
        t = C.inspect_document("a.pdf", make_text_pdf(["Safety engineer on a metro excavation project 2019 to 2022. " * 3] * 3))
        self.assertEqual(t["kind"], "pdf"); self.assertTrue(t["pages"][1]["ok"])
        s = C.inspect_document("scan.pdf", make_scan_pdf())
        self.assertFalse(s["pages"][1]["ok"])
        self.assertTrue(any("بدون لایه متنی" in w for w in s["warnings"]))
        with self.assertRaises(C.DocError): C.inspect_document("x.pdf", b"")
        with self.assertRaises(C.DocError): C.inspect_document("x.pdf", b"not a pdf at all")
        with self.assertRaises(C.DocError): C.inspect_document("x.pdf", make_text_pdf(["secret"], password="pw")[:0] or b"%PDF-1.4 broken")

    def test_leading_junk_before_pdf_header(self):
        data = b"\r\n\r\n  junk " + make_scan_pdf()
        self.assertEqual(C.sniff_kind(data), "pdf")
        self.assertEqual(C.inspect_document("j.pdf", data)["page_count"], 1)

    def test_encrypted_pdf_clear_error(self):
        with self.assertRaises(C.DocError) as cm:
            C.inspect_document("e.pdf", make_text_pdf(["hello world " * 10], password="pw"))
        self.assertIn("رمز", str(cm.exception))

    def test_render_scan_without_tesseract(self):
        out = C.render_pages(make_scan_pdf(), "pdf", {"max_pages": 2})
        self.assertEqual(out[0]["jpeg"][:3], b"\xff\xd8\xff")
        self.assertLessEqual(max(out[0]["w"], out[0]["h"]), C.DEFAULT_RENDER["max_side"])


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.con = C.db_connect(TMP / f"t_{self._testMethodName}.sqlite3")
        C.seed_positions(self.con)
        self.hse = C.get_position(self.con, "hse")
        self.data = make_docx(CV_FA)
        self.info = C.store_file(self.con, "cv.docx", self.data)

    def run_one(self, pos, client, model="gpt-6-luna", **kw):
        return C.analyze_file(self.con, client, pos, model, self.info, **kw)

    def test_seed_does_not_overwrite_user_edits(self):
        p = C.get_position(self.con, "hse"); p["title"] = "ویرایش‌شده"; C.save_position(self.con, p)
        C.seed_positions(self.con)
        self.assertEqual(C.get_position(self.con, "hse")["title"], "ویرایش‌شده")

    def test_cache_prevents_duplicate_api_call(self):
        cl = FakeClient(lambda kw: hse_answer({"civil_site": 3}))
        self.assertFalse(self.run_one(self.hse, cl)["cached"])
        self.assertTrue(self.run_one(self.hse, cl)["cached"])
        self.assertEqual(cl.calls, 1)
        plan = C.plan_batch(self.con, self.hse, [self.info, self.info], "gpt-6-luna")
        self.assertEqual([p["state"] for p in plan], ["cached", "duplicate"])

    def test_reweight_and_review_without_api(self):
        cl = FakeClient(lambda kw: hse_answer({"civil_site": 4, "structure_site": 4}))
        self.run_one(self.hse, cl)
        r1 = C.load_results(self.con, self.hse, (1405, 8))[0]
        self.assertEqual(r1["status"], "معتبر")
        # criterion 2 weight 10 -> mean level 4 -> 10 points (evidence 1 only => level 4 capped to 3 -> 7.5)
        self.assertAlmostEqual(r1["criteria"][1]["points"], 10 * 3 / 4, places=2)
        h2 = copy.deepcopy(self.hse)
        h2["criteria"][1]["weight"] = 20.0; h2["criteria"][0]["weight"] = 15.0
        C.save_position(self.con, h2)
        self.assertEqual(C.plan_batch(self.con, h2, [self.info], "gpt-6-luna")[0]["state"], "cached")
        r2 = C.load_results(self.con, h2, (1405, 8))[0]
        self.assertAlmostEqual(r2["criteria"][1]["points"], 20 * 3 / 4, places=2)
        C.save_review(self.con, r2["file_sha"], "hse", "sub:civil_site", "level", 2, "بازبینی")
        r3 = C.load_results(self.con, h2, (1405, 8))[0]
        self.assertLess(r3["criteria"][1]["points"], r2["criteria"][1]["points"])
        self.assertTrue(r3["manual_edits"])
        self.assertEqual(cl.calls, 1)

    def test_mismatch_not_hidden_and_not_approved(self):
        cl = FakeClient(lambda kw: hse_answer({"civil_site": 3}, quote_ok=False))
        self.run_one(self.hse, cl)
        r = C.load_results(self.con, self.hse, (1405, 8))[0]
        sub = [s for s in r["subs"] if s["sub_id"] == "civil_site"][0]
        self.assertEqual(sub["claimed"], 3); self.assertEqual(sub["effective"], 0)
        self.assertEqual(sub["evidence"][0]["status"], "mismatch")
        self.assertGreaterEqual(r["mismatch_count"], 1); self.assertIn("(موقت)", r["group_label"])
        C.save_review(self.con, r["file_sha"], "hse", "ev:civil_site:0", "decision", "confirm", "HR دید")
        r2 = C.load_results(self.con, self.hse, (1405, 8))[0]
        s2 = [s for s in r2["subs"] if s["sub_id"] == "civil_site"][0]
        self.assertEqual(s2["effective"], 3)
        self.assertEqual(s2["evidence"][0]["status"], "reviewer_confirmed")
        self.assertEqual(cl.calls, 1)

    def test_kind_caps_and_course(self):
        raw = json.loads(hse_answer({"civil_site": 4}))
        for s in raw["subcriteria"]:
            if s["sub_id"] == "civil_site": s["evidence_kind"] = "title"
            if s["sub_id"] == "excel":
                s.update(level=4, evidence_kind="course", evidence=[{"quote": "تسلط به Word و Excel برای تهیه گزارش", "page": 1}])
            if s["sub_id"] == "certificates":
                s.update(level=4, evidence_kind="course", evidence=[{"quote": "تسلط به Word و Excel برای تهیه گزارش", "page": 1}])
        r = C.assess(self.hse, json.dumps(raw, ensure_ascii=False), self.info["pages"], {}, (1405, 8))
        g = {s["sub_id"]: s for s in r["subs"]}
        self.assertEqual(g["civil_site"]["effective"], 1)
        self.assertEqual(g["excel"]["effective"], 0)          # course not accepted for Excel
        self.assertEqual(g["certificates"]["effective"], 2)   # accepted, capped at 2

    def test_experience_overlap_counted_once(self):
        self.run_one(self.hse, FakeClient(lambda kw: hse_answer()))
        r = C.load_results(self.con, self.hse, (1405, 8))[0]
        hse = r["experience"]["hse"]
        # 1398/04-1401/06 = 39 months; 1400/01-now(1405/08)= 68 months; overlap 1400/01-1401/06 = 18
        self.assertEqual(hse["naive_months"], 39 + 68)
        self.assertEqual(hse["months"], 39 + 68 - 18)
        self.assertEqual(hse["overlap_months"], 18)
        self.assertEqual(r["min_checks"][0]["status"], "احراز اولیه")

    def test_incomplete_not_ranked_and_failed_parse_not_recalled(self):
        cl = FakeClient(lambda kw: "نه JSON")
        self.run_one(self.hse, cl); self.run_one(self.hse, cl)
        self.assertEqual(cl.calls, 1)
        self.assertEqual(C.plan_batch(self.con, self.hse, [self.info], "gpt-6-luna")[0]["state"], "cached_failed")
        r = C.load_results(self.con, self.hse)[0]
        self.assertEqual(r["status"], "خطای تحلیل"); self.assertFalse(r["rankable"])
        raw = json.loads(hse_answer()); raw["subcriteria"] = raw["subcriteria"][:-2]
        r2 = C.assess(self.hse, json.dumps(raw, ensure_ascii=False), self.info["pages"], {}, (1405, 8))
        self.assertEqual(r2["status"], "ناقص"); self.assertIsNone(r2["score"])

    def test_truncated_json_repair_flagged(self):
        raw = hse_answer()
        obj, notes = C.parse_model_json(raw[:-60])
        self.assertTrue(notes)

    def test_other_model_and_changed_prompt_need_explicit_new_call(self):
        cl = FakeClient(lambda kw: hse_answer())
        self.run_one(self.hse, cl)
        self.assertEqual(C.plan_batch(self.con, self.hse, [self.info], "gpt-5.4")[0]["state"], "cached_other")
        h2 = copy.deepcopy(self.hse); h2["description"] += " تغییر"
        self.assertEqual(C.plan_batch(self.con, h2, [self.info], "gpt-6-luna")[0]["state"], "cached_other")

    def test_two_positions_independent(self):
        p2 = pos2(); C.save_position(self.con, p2)
        def b(kw):
            if "سمت: کارشناس کنترل پروژه" in kw["messages"][0]["content"]:
                subs = [{"sub_id": i, "level": 3, "evidence_kind": "action", "claim": "c",
                         "evidence": [{"quote": "بازرسی روزانه گودبرداری و کنترل مجوز کار", "page": 1}]} for i in ("k1_a", "k1_b", "k2_a")]
                return json.dumps({"candidate_name": "علی", "information_sufficiency": "کافی", "subcriteria": subs,
                                   "employment_history": [], "conditions": {}, "strengths": [], "uncertainties": [], "interview_questions": [], "summary": ""}, ensure_ascii=False)
            return hse_answer({"civil_site": 3})
        cl = FakeClient(b)
        self.run_one(self.hse, cl); self.run_one(p2, cl)
        self.assertEqual(cl.calls, 2)
        r_h = C.load_results(self.con, self.hse)[0]; r_c = C.load_results(self.con, p2)[0]
        self.assertAlmostEqual(r_c["score"], 60 * 0.75 + 40 * 0.75, places=1)
        self.assertNotEqual(r_h["score"], r_c["score"])
        self.assertTrue(r_c["stable_id"].startswith("CTRL-")); self.assertTrue(r_h["stable_id"].startswith("HSE-"))
        sysmsg = cl.last["messages"][0]["content"]
        self.assertNotIn("geo_excavation", sysmsg)  # HSE criteria must not leak into the other position

    def test_request_is_vision_payload_for_pdf(self):
        pdf = make_scan_pdf()
        info = C.store_file(self.con, "scan.pdf", pdf)
        cl = FakeClient(lambda kw: hse_answer())
        C.analyze_file(self.con, cl, self.hse, "gpt-6-luna", info)
        parts = cl.last["messages"][1]["content"]
        imgs = [p for p in parts if p["type"] == "image_url"]
        self.assertEqual(len(imgs), 1)
        self.assertTrue(imgs[0]["image_url"]["url"].startswith("data:image/jpeg;base64,"))
        r = [x for x in C.load_results(self.con, self.hse) if x["file_name"] == "scan.pdf"][0]
        self.assertTrue(all(e["status"] in ("visual_only", "mismatch", "no_quote")
                            for s in r["subs"] for e in s["evidence"]))

    def test_excel_export(self):
        self.run_one(self.hse, FakeClient(lambda kw: hse_answer({"civil_site": 3}).replace("علی رضایی", "=HYPERLINK(x)")))
        res = C.load_results(self.con, self.hse, (1405, 8))
        data = C.export_excel(res, self.hse)
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(data))
        for name in ("رتبه‌بندی", "زیرمعیارها و شواهد", "سوابق شغلی", "سابقه بدون دوباره‌شماری", "نقاط قوت و ابهام",
                     "سؤالات مصاحبه", "تحلیل گروهی", "کنترل فنی"):
            self.assertIn(name, wb.sheetnames)
            self.assertTrue(wb[name].sheet_view.rightToLeft)
        ws = wb["رتبه‌بندی"]
        self.assertEqual(ws.cell(1, 1).value, "رتبه")
        self.assertEqual(ws.cell(2, 3).data_type, "s")  # formula injection neutralised
        self.assertTrue(str(ws.cell(2, 3).value).startswith("=HYPER"))
        self.assertEqual(ws.cell(2, 1).value, 1)


if __name__ == "__main__":
    unittest.main()
