"""Stub-based smoke test of app_vision.py: runs the script top to bottom against a fake
`streamlit` (real Streamlit is not required). It only proves the script's own logic runs
without NameError/KeyError on seeded data; it does NOT test real browser/widget behaviour."""
import sys, types, tempfile, json, runpy, io, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hr_vision_core as C
import test_core as T

tmp = Path(tempfile.mkdtemp())
C.DB_PATH, C.FILES_DIR = tmp / "db.sqlite3", tmp / "files"
os.environ["GAPGPT_API_KEY"] = "dummy"; os.environ["GAPGPT_BASE_URL"] = "http://invalid.local"
con = C.db_connect(); C.seed_positions(con)
hse = C.get_position(con, "hse")
info = C.store_file(con, "cv.docx", T.make_docx(T.CV_FA))
C.analyze_file(con, T.FakeClient(lambda kw: T.hse_answer({"civil_site": 3})), hse, "gpt-6-luna", info)
con.close()

PRESS = set(sys.argv[1:])
class Ctx:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __getattr__(self, n): return getattr(ST, n)
class Sess(dict):
    __getattr__ = dict.get
class FakeUpload:
    def __init__(self, name, data): self.name, self._d = name, data
    def getvalue(self): return self._d
ST = types.ModuleType("streamlit")
ST.session_state = Sess()
def sel(label, options=(), *a, **k):
    options = list(options)
    if "edit" in PRESS and label.startswith("سمت برای ویرایش"):
        return options[1]
    return options[k.get("index", 0)] if options else None
ST.set_page_config = lambda **k: None
ST.subheader = ST.header = ST.title = lambda *a, **k: None
ST.__getattr__ = lambda n: (lambda *a, **k: None)
MSGS = []
def _cap(kind):
    return lambda *a, **k: MSGS.append((kind, str(a[0]) if a else ""))
ST.error, ST.warning, ST.info, ST.success, ST.write = _cap("error"), _cap("warning"), _cap("info"), _cap("success"), _cap("write")
ST.markdown = ST.caption = ST.text = ST.dataframe = ST.bar_chart = ST.image = ST.rerun = lambda *a, **k: None
ST.metric = lambda *a, **k: None
ST.progress = lambda *a, **k: Ctx()
ST.cache_resource = lambda f: f
ST.cache_data = lambda *a, **k: (lambda f: f)
ST.sidebar = Ctx(); ST.expander = lambda *a, **k: Ctx(); ST.form = lambda *a, **k: Ctx()
ST.tabs = lambda labels: [Ctx() for _ in labels]
ST.columns = lambda n, **k: [Ctx() for _ in range(n if isinstance(n, int) else len(n))]
ST.selectbox = sel
ST.multiselect = lambda *a, **k: []
ST.radio = sel
ST.text_input = lambda label, value="", *a, **k: value
ST.text_area = lambda label, value="", *a, **k: value
ST.number_input = lambda label, *a, **k: k.get("value", a[2] if len(a) > 2 else 1)
ST.slider = lambda label, lo, hi, v=None, *a, **k: v
ST.checkbox = lambda label, *a, **k: any(p in label for p in PRESS)
ST.button = lambda label, *a, **k: any(p in label for p in PRESS) and not k.get("disabled")
ST.form_submit_button = lambda label, *a, **k: any(p in label for p in PRESS)
ST.download_button = lambda *a, **k: None
ST.data_editor = lambda df, *a, **k: df
UP = {"files": []}
ST.file_uploader = lambda label, *a, **k: (UP["files"] if k.get("accept_multiple_files") else None)
ST.column_config = types.SimpleNamespace()
sys.modules["streamlit"] = ST
if "upload" in PRESS:
    UP["files"] = [FakeUpload("good.docx", T.make_docx(["رزومه دوم " * 20])), FakeUpload("bad.pdf", b"garbage"),
                   FakeUpload("scan.pdf", T.make_scan_pdf())]
if "run" in PRESS:
    FC = T.FakeClient(lambda kw: T.hse_answer({"civil_site": 2}))
    C.make_client = lambda key, base: FC
runpy.run_path(str(Path(__file__).resolve().parents[1] / "app_vision.py"), run_name="__main__")
print("UI smoke OK; pressed:", sorted(PRESS))
if "edit" in PRESS:
    c2 = C.db_connect(); p2 = C.get_position(c2, "hse")
    print("roundtrip same prompt hash:", C.prompt_hash(p2) == C.prompt_hash(hse), "| criteria equal:", p2["criteria"] == hse["criteria"],
          "| tracks equal:", p2["experience_tracks"] == hse["experience_tracks"], "| conds equal:", p2["conditions"] == hse["conditions"],
          "| thresholds:", p2["grade_thresholds"] == hse["grade_thresholds"], "| common_q equal:", p2["common_questions"] == hse["common_questions"])

for k, m in MSGS:
    print(k, "|", m[:150])
if "run" in PRESS:
    print("fake API calls:", FC.calls)
