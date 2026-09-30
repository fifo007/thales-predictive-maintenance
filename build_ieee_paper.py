"""Generate an IEEE-style two-column version of the project research paper."""
from pathlib import Path
import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

ROOT = Path(__file__).parent
OUT = ROOT / "deliverables" / "predictive_maintenance_research_paper.docx"
df = pd.read_csv(ROOT / "Thales_Group_Manufacturing.csv")
df["event_time"] = pd.to_datetime(df["Date"] + " " + df["Timestamp"], dayfirst=True)

def set_font(run, size=10, bold=False, italic=False):
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    run.font.size = Pt(size); run.bold = bold; run.italic = italic

def set_columns(section, count=2, space=360):
    sectPr = section._sectPr
    cols = sectPr.first_child_found_in("w:cols")
    if cols is None:
        cols = OxmlElement("w:cols"); sectPr.append(cols)
    cols.set(qn("w:num"), str(count)); cols.set(qn("w:space"), str(space)); cols.set(qn("w:equalWidth"), "1")

def para(doc, text="", align=None, before=0, after=3, first_indent=0):
    p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(before); p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.0
    if first_indent: p.paragraph_format.first_line_indent = Inches(first_indent)
    if align is not None: p.alignment = align
    if text: set_font(p.add_run(text))
    return p

def heading(doc, numeral, title):
    p = para(doc, "", align=WD_ALIGN_PARAGRAPH.CENTER, before=7, after=4)
    set_font(p.add_run(f"{numeral}. {title.upper()}"), 10, bold=True)

def cite_para(doc, text):
    p = para(doc, "", after=2, first_indent=0)
    set_font(p.add_run(text), 8)
    return p

doc = Document()
sec = doc.sections[0]
sec.top_margin = Inches(0.72); sec.bottom_margin = Inches(0.72)
sec.left_margin = Inches(0.72); sec.right_margin = Inches(0.72)
set_columns(sec, 1)
styles = doc.styles
styles["Normal"].font.name = "Times New Roman"
styles["Normal"]._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
styles["Normal"].font.size = Pt(10)

p = para(doc, "", align=WD_ALIGN_PARAGRAPH.CENTER, after=5)
set_font(p.add_run("Predictive Maintenance Analytics Using Machine Specific Baselines and Isolation Forest"), 16, bold=True)
p = para(doc, "", align=WD_ALIGN_PARAGRAPH.CENTER, after=1)
set_font(p.add_run("Author Name"), 10)
p = para(doc, "", align=WD_ALIGN_PARAGRAPH.CENTER, after=8)
set_font(p.add_run("Department or Institution, City, Country\nemail@example.com"), 9)

p = para(doc, "", align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=4)
set_font(p.add_run("Abstract—"), 9, bold=True)
set_font(p.add_run(
    f"This paper presents an unsupervised predictive-maintenance workflow for {len(df):,} manufacturing telemetry readings from {df.Machine_ID.nunique()} machines. "
    "The workflow estimates machine-specific rolling baselines, engineers deviations and temporal features, and uses Isolation Forest to rank uncommon multivariate behavior. "
    "The resulting 0–100 anomaly score is mapped to low, medium, and high maintenance-risk categories and delivered through a Streamlit decision-support dashboard. "
    "The approach is intended to surface early warning signals before broad efficiency degradation is visible, while retaining a human maintenance professional in the response loop."), 9, italic=True)
p = para(doc, "", align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=8)
set_font(p.add_run("Index Terms—"), 9, bold=True)
set_font(p.add_run("predictive maintenance, anomaly detection, Isolation Forest, industrial IoT, manufacturing analytics."), 9, italic=True)

body = doc.add_section(WD_SECTION.CONTINUOUS)
body.top_margin = sec.top_margin; body.bottom_margin = sec.bottom_margin
body.left_margin = sec.left_margin; body.right_margin = sec.right_margin
set_columns(body, 2, 360)

heading(doc, "I", "Introduction")
para(doc, "Unplanned machine failures are infrequent but costly because they interrupt production and can require urgent repair. Conventional rule-based thresholds are difficult to maintain in heterogeneous fleets: a reading that is routine for one asset or operating mode may be abnormal for another. The supplied manufacturing dataset contains timestamped temperature, vibration, power, network, quality, production, maintenance-score, and error-rate observations. It therefore supports an anomaly-detection framing in which rare combinations of measurements provide inspection signals before a confirmed failure occurs.")
para(doc, "The contribution of this work is a transparent, dashboard-oriented workflow that couples robust machine-specific baselines with multivariate anomaly scoring. Rather than treating the score as an automated shutdown decision, the application uses it to prioritize inspection and to show the sensor context and escalation history that led to an alert.")

heading(doc, "II", "Related Work")
para(doc, "Isolation Forest identifies anomalies by recursively partitioning data; observations isolated in fewer random splits are considered more unusual [1]. Its suitability for high-dimensional anomaly detection and its ensemble structure make it practical for operational telemetry. The implementation used here follows the IsolationForest estimator provided by scikit-learn [2]. Industrial predictive-maintenance research consistently emphasizes the need to combine sensor data, operational context, and maintenance outcomes when moving from detection toward failure prediction [3], [4].")

heading(doc, "III", "Dataset and Exploratory Analysis")
start, end = df.event_time.min(), df.event_time.max()
mode_counts = ", ".join(f"{mode} ({count:,})" for mode, count in df.Operation_Mode.value_counts().items())
status_counts = ", ".join(f"{label} ({count:,})" for label, count in df.Efficiency_Status.value_counts().items())
para(doc, f"The dataset contains {len(df):,} readings from {df.Machine_ID.nunique()} machines, recorded from {start:%d %b %Y %H:%M} through {end:%d %b %Y %H:%M}. The observed operating modes are {mode_counts}. Efficiency labels are distributed as {status_counts}. Fields include physical sensors, network latency and packet loss, product quality, production speed, an existing predictive-maintenance score, and error rate.")
para(doc, "No confirmed breakdown date, work-order outcome, repair cost, or remaining-useful-life target is available. Accordingly, the analysis evaluates behavioral abnormality rather than a calibrated probability of failure. This distinction is important for safe deployment: alerts should guide inspection priority and be validated against maintenance outcomes.")

heading(doc, "IV", "Methodology")
para(doc, "A rolling median baseline is calculated separately for each Machine_ID over the preceding 30 readings for temperature, vibration, power consumption, and error rate. The absolute difference from the baseline is divided by the rolling standard deviation, yielding a robust normalized deviation. A vibration-to-power ratio captures mechanical behavior relative to load, while a ten-observation error-rate difference represents short-term deterioration.")
para(doc, "The model input contains the original sensor, connectivity, quality, speed, maintenance-score, and error-rate fields plus the engineered deviations, ratio, and error trend. Robust scaling reduces the effect of heavy-tailed measurements. An Isolation Forest with 180 trees and an 8% contamination setting is fitted on a deterministic representative sample of at most 50,000 readings. Scores are transformed linearly to a 0–100 anomaly scale. Scores of 0–45 are Low, 45–70 are Medium, and values above 70 are High risk; users can change the operational alert threshold in the dashboard.")

heading(doc, "V", "Dashboard Design")
para(doc, "The Streamlit application supplies four modules: a predictive-maintenance overview, a machine anomaly dashboard, a maintenance alert panel, and historical risk analysis. Users select machine identifiers, a time window, operation modes, and an alert threshold. The overview presents risk distribution and the latest score per asset. The anomaly module displays score and sensor-deviation trends. The alert module provides inspection-priority recommendations and CSV export. The historical module aggregates hourly risk scores and compares behavior across operating modes.")

heading(doc, "VI", "Discussion and Recommendations")
para(doc, "Machine-specific deviations avoid assuming that a single global threshold represents normal behavior. Multivariate scoring can identify subtle combinations of high vibration, changing power, rising error rate, and degraded connectivity that may not cross a univariate limit. However, unsupervised anomalies may also be explained by planned process changes, instrument drift, or changes in operating mode. The dashboard therefore exposes the underlying context and does not automatically issue a shutdown command.")
para(doc, "A controlled pilot should connect alert records to inspections and work orders. Key measures include the proportion of high-risk alerts inspected, warning lead time, false-alert rate, avoided downtime, and avoided cost. As outcomes are recorded, the organization can evaluate threshold performance by mode and machine type, retrain models, and progress toward supervised failure-risk estimation.")

heading(doc, "VII", "Conclusion")
para(doc, "The proposed workflow turns manufacturing telemetry into an interpretable maintenance-prioritization process. Rolling machine baselines provide local context, engineered temporal features capture change, and Isolation Forest ranks rare multivariate behavior. The resulting dashboard supports a shift from reactive intervention to earlier, evidence-based inspection while retaining appropriate human oversight.")

heading(doc, "", "References")
refs = [
    "[1] F. T. Liu, K. M. Ting, and Z.-H. Zhou, “Isolation Forest,” in Proc. 8th IEEE Int. Conf. Data Mining, Pisa, Italy, 2008, pp. 413–422, doi: 10.1109/ICDM.2008.17.",
    "[2] scikit-learn developers, “IsolationForest,” scikit-learn documentation. [Online]. Available: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html. Accessed: Sep. 30, 2026.",
    "[3] A. Carvalho, S. O. R. da Silva, R. M. Brito, and A. M. D. S. Ribeiro, “A systematic literature review of machine learning methods applied to predictive maintenance,” Comput. Ind. Eng., vol. 137, 2019, Art. no. 106024, doi: 10.1016/j.cie.2019.106024.",
    "[4] M. Compare, P. Baraldi, and E. Zio, “Challenges to IoT-enabled predictive maintenance for industry 4.0,” IEEE Internet Things J., vol. 7, no. 5, pp. 4585–4597, May 2020, doi: 10.1109/JIOT.2019.2957029.",
]
for ref in refs: cite_para(doc, ref)

doc.core_properties.title = "Predictive Maintenance Analytics Using Machine Specific Baselines and Isolation Forest"
doc.core_properties.author = "Author Name"
doc.save(OUT)
print(OUT)
