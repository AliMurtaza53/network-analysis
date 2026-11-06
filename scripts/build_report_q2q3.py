"""Build docs/Report_Q2_Q3.docx (Questions 2 and 3) with native Word equations."""
import re
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

FIG = 'outputs/revised/figures'
OUT = 'docs/Report_Q2_Q3.docx'
FONT = 'Times New Roman'
doc = Document()
for s in doc.sections:
    s.page_width, s.page_height = Inches(8.5), Inches(11)
    s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Inches(1)
st = doc.styles['Normal']; st.font.name = FONT; st.font.size = Pt(11)
st.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
for nm, sz in (('Heading 1', 14), ('Heading 2', 12)):
    h = doc.styles[nm]; h.font.name = FONT; h.font.size = Pt(sz); h.font.bold = True; h.font.color.rgb = RGBColor(0, 0, 0)
    rf = h.element.rPr.rFonts
    for a in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]
    rf.set(qn('w:ascii'), FONT); rf.set(qn('w:hAnsi'), FONT)
    h.paragraph_format.space_before = Pt(10); h.paragraph_format.space_after = Pt(3); h.paragraph_format.keep_with_next = True

# footer page number
fp = doc.sections[0].footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
fp._p.append(parse_xml('<w:fldSimple xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:instr="PAGE"><w:r><w:t>1</w:t></w:r></w:fldSimple>'))


def rich(par, text, size=None):
    for tok in re.split(r'(\*\*.+?\*\*|\^\{.+?\})', text):
        if not tok:
            continue
        if tok.startswith('**'):
            r = par.add_run(tok[2:-2]); r.bold = True
        elif tok.startswith('^{'):
            r = par.add_run(tok[2:-1]); r.font.superscript = True
        else:
            r = par.add_run(tok)
        r.font.name = FONT
        if size:
            r.font.size = Pt(size)


def para(text, after=4, align=WD_ALIGN_PARAGRAPH.JUSTIFY, size=None, keep=False):
    p = doc.add_paragraph(); p.alignment = align
    p.paragraph_format.space_after = Pt(after); p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.keep_with_next = keep
    rich(p, text, size); return p


def bullet(text):
    p = doc.add_paragraph(style='List Bullet'); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(2); rich(p, text); return p


def figure(name, caption):
    doc.add_picture(f'{FIG}/{name}', width=Inches(6.5))
    pic = doc.paragraphs[-1]; pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic.paragraph_format.space_after = Pt(2); pic.paragraph_format.keep_with_next = True
    para(caption, after=8, size=9.5)


# ---------- OMML helpers ----------
MNS = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
def R(t, up=False):
    t = t.replace('&', '&amp;').replace('<', '&lt;')
    pr = '<m:rPr><m:sty m:val="p"/></m:rPr>' if up else ''
    return f'<m:r>{pr}<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr><m:t xml:space="preserve">{t}</m:t></m:r>'
def SUB(b, s): return f'<m:sSub><m:e>{b}</m:e><m:sub>{s}</m:sub></m:sSub>'
def SUP(b, s): return f'<m:sSup><m:e>{b}</m:e><m:sup>{s}</m:sup></m:sSup>'
def SUBSUP(b, s, p): return f'<m:sSubSup><m:e>{b}</m:e><m:sub>{s}</m:sub><m:sup>{p}</m:sup></m:sSubSup>'
def FRAC(n, d): return f'<m:f><m:num>{n}</m:num><m:den>{d}</m:den></m:f>'
def NARY(ch, lo, hi, body):
    hide = '' if hi != R('') else '<m:supHide m:val="1"/>'
    return (f'<m:nary><m:naryPr><m:chr m:val="{ch}"/><m:limLoc m:val="undOvr"/>{hide}</m:naryPr><m:sub>{lo}</m:sub><m:sup>{hi}</m:sup><m:e>{body}</m:e></m:nary>')
def INT(lo, hi, body):
    return (f'<m:nary><m:naryPr><m:chr m:val="∫"/><m:limLoc m:val="subSup"/></m:naryPr><m:sub>{lo}</m:sub><m:sup>{hi}</m:sup><m:e>{body}</m:e></m:nary>')
def D(inner, b='(', e=')'):
    return f'<m:d><m:dPr><m:begChr m:val="{b}"/><m:endChr m:val="{e}"/></m:dPr><m:e>{inner}</m:e></m:d>'
def RAD(inner): return f'<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{inner}</m:e></m:rad>'


def eq(*parts, number=None):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4); p.paragraph_format.space_before = Pt(2)
    body = ''.join(parts)
    xml = f'<m:oMathPara {MNS}><m:oMathParaPr><m:jc m:val="center"/></m:oMathParaPr><m:oMath>{body}</m:oMath></m:oMathPara>'
    p._p.append(parse_xml(xml)); return p


def table(rows, widths, header=True, size=9.5):
    t = doc.add_table(rows=len(rows), cols=len(rows[0])); t.style = 'Table Grid'; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j); c.width = Inches(widths[j]); c.text = ''
            pp = c.paragraphs[0]; pp.paragraph_format.space_after = Pt(0)
            pp.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            rich(pp, val, size)
            if i == 0 and header:
                for r in pp.runs:
                    r.bold = True
    return t


# =========================================================================== TITLE
tp = para('**Transport network resilience on the Anaheim benchmark: scenario results and sensitivity (Questions 2 and 3)**',
          after=2, align=WD_ALIGN_PARAGRAPH.LEFT, size=15)
para('Ali Murtaza  |  November 2026', after=6, align=WD_ALIGN_PARAGRAPH.LEFT, size=10.5)
para('**Setting.** The TNTP Anaheim network^{1} has 416 nodes, 914 links and 38 zones, with 104,694 vehicles per hour of peak demand. '
     'Link delay follows the Bureau of Public Roads (BPR) curve^{2} (below), so delay rises sharply as flow f approaches and exceeds capacity u. '
     'In the baseline, total travel time is 23,662 vehicle-hours per peak hour and a trip takes 13.6 minutes on average. '
     'Every “ratio” below is a disrupted result divided by the baseline solved the same way, so 1.50 means 50% worse.', after=2)
eq(SUB(R('t'), R('a')), D(SUB(R('f'), R('a'))), R('='), SUBSUP(R('t'), R('a'), R('0')),
   D(R('1+')+R('α')+SUP(D(FRAC(SUB(R('f'), R('a')), SUB(R('u'), R('a')))), R('β')), '[', ']'))
para('Here t⁰ is the free-flow time of link a, and the standard parameters are α = 0.15 and β = 4. All results use user-equilibrium traffic assignment, '
     'in which no traveller can save time by switching route.', after=4)

# =========================================================================== Q2
doc.add_heading('Question 2. Scenario results', level=1)
para('Seventy-nine disruptions in five families were solved to equilibrium: S1 random closure of 1, 5 or 10 links (61 runs), '
     'S2 targeted closure of the 1, 3 or 5 most harmful links, S3 flood footprints of 1–3 km radius (depth model of Pregnolato et al.^{3}), '
     'S4 capacity loss to 75%, 50% or 25% of normal (on all links, S4a, or on the busiest 10% of links, S4b), and S5 demand surges of ×1.2 and ×1.4, alone or combined with a disruption.', after=3)

doc.add_heading('2.1 Which disruptions hurt most', level=2)
para('Total system travel time (TSTT) adds up the time every vehicle spends on every link. Because it falls when demand goes unserved and rises when '
     'demand grows, it is read together with the mean time per served trip.', after=2, keep=True)
eq(R('TSTT', up=True), R('='), NARY('∑', R('a∈A'), R(''), SUB(R('f'), R('a')) + SUB(R('t'), R('a')) + D(SUB(R('f'), R('a')))))
para('Accessibility loss is the fall in the gravity-weighted number of reachable destinations^{4}.', after=4)
table([['Scenario', 'Total travel time, veh-h (change)', 'Ratio', 'Time per trip, min (ratio)', 'BPR range of trip ratio'],
       ['Baseline', '23,662', '1.00', '13.6 (1.00)', '–'],
       ['S1 random, median of 61', '24,006 (+344)', '1.02', '13.8 (1.02)', '–'],
       ['S2 top-1 / top-3 / top-5', '28,830 / 32,982 / 36,255 (+5,168 / +9,320 / +12,592)', '1.22 / 1.39 / 1.53', '16.5 / 18.9 / 20.8', '1.06–3.4 / 1.13–5.0 / 1.21–5.7'],
       ['S3 flood, r = 3 km', '25,533 (+1,871)', '1.08', '14.6 (1.08)', '1.08–1.09'],
       ['S4a all links, 50% / 25%', '49,499 (+25,837) / 424,577 (+400,914)', '2.09 / 17.94', '28.4 / 243.3', '1.5–8.4 / 4.6–243'],
       ['S4b busiest 10%, 50% / 25%', '45,908 (+22,246) / 365,792 (+342,130)', '1.94 / 15.46', '26.3 / 209.6', '1.4–7.8 / 3.8–222'],
       ['S5 demand ×1.4', '40,967 (+17,305)', '1.73', '16.8 (1.24)', '1.24–2.9'],
       ['S5 ×1.4 + top-3 closure', '87,209 (+63,547)', '3.69', '35.7 (2.63)', '2.0–32.5']],
      [1.45, 2.0, 0.85, 1.1, 1.1], size=8.5)
para('**Table 1 | Absolute and relative impact (veh-h = vehicle-hours per peak hour).**', after=6, size=9.5)
figure('F3_family_comparison.png',
       '**Figure 1 | Network-wide capacity loss dominates; random closures barely register.** Dots are individual scenarios. '
       'Lines show the range across BPR parameters; for S1 the diamond is the median with its 95% interval.')
bullet('**Capacity loss is the most damaging stress.** Halving capacity doubles trip time (13.6 to 28.4 min, +25,837 veh-h); quartering it multiplies it by 18 (243 min). '
       'Delay grows with the fourth power of flow-to-capacity, so damage is convex. A uniform cut to a fraction c of capacity is mathematically equivalent to demand ×1/c: '
       'a ×4 demand run reproduces the 17.94 ratio exactly. Cutting only the busiest 10% of links is nearly as harmful (1.94× and 15.5×), so the network has little spare capacity where it matters.')
bullet('**Targeted closure beats random closure.** The single worst link adds 5,168 veh-h (+21.8%); five greedily chosen links add 12,592 veh-h (+53%). '
       'The median random closure adds only 344 veh-h (+1.5%). A few links carry a disproportionate share of flow, and random failures mostly miss them.')
bullet('**Random closures can hide a different harm.** Of 61 runs, 25 isolate at least one zone (7 of 30 with 5 links closed, 18 of 30 with 10), leaving up to 16% of demand (about 16,700 veh/h) unserved. '
       'TSTT drops below baseline in 14 runs only because those trips vanish, which is why unserved demand must be reported alongside travel time.')
bullet('**Floods are local but nonlinear.** A 3 km flood adds 1,871 veh-h (+7.9%) and cuts accessibility 7.9%, while 1–2 km floods add under 1.6%. '
       '**Demand surges compound with damage:** ×1.4 demand alone raises trip time 1.24×, a top-3 closure alone 1.39×, but together 2.63×, against 1.72× if the effects simply multiplied.')
bullet('**Uncertainty grows with severity.** Moving BPR α from 0.15 to 0.50 and β from 3 to 5 changes mild scenarios little (flood: 1.08–1.09) but severe ones enormously '
       '(S4a at 25%: 4.6× to 243×). The ordering of scenarios is stable; the size of severe outcomes is not.')

doc.add_heading('2.2 Link criticality', level=2)
figure('F4_criticality.png',
       '**Figure 2 | One corridor accounts for the most harmful closures.** Each link was closed alone (60 highest-flow links screened). Colour and bar length show the rise in total travel time.')
para('Closing link 92→91 alone adds 5,150 veh-h per peak hour (+21.8%), and its neighbours 91→90 and 90→89 are almost as harmful (+21.8%, +21.2%); '
     'ranks 1–3 are consecutive links of a single corridor carrying 7,800–8,500 veh/h. Ranks 4–5 add +9.8% (about 2,330 veh-h each), and even the 15th link adds +2.7% (about 640 veh-h). '
     'These links sit close together because both directions of a road share one geometry on the map. Criticality is therefore concentrated, so protecting or duplicating one corridor '
     'buys more resilience than spreading effort evenly^{5,6}. Two cautions: the screen covers 60 of 914 links, and 17 of the 60 show a negative effect because closing them cuts zones off, '
     'so travel time understates their harm.', after=4)

doc.add_heading('2.3 Recovery', level=2)
para('System performance Q compares served demand and trip time with the baseline, and the resilience index R averages it over the 90-day horizon^{7}:', after=2, keep=True)
eq(R('Q'), D(R('t')), R('='), FRAC(SUB(R('D'), R('served')) + D(R('t')), SUB(R('D'), R('base'))), R('×'),
   FRAC(SUB(R('τ'), R('base')), R('τ') + D(R('t'))))
eq(R('R'), R('='), FRAC(R('1'), R('T')), INT(R('0'), R('T'), R('Q') + D(R('t')) + R('dt')))
para('Here D is the demand served, τ the mean trip time, and T = 90 days. Capacity is restored linearly and equilibrium re-solved every 5 days. '
     '(1 − R) × 90 gives the full-outage-equivalent days lost.', after=4)
figure('F6_recovery.png', '**Figure 3 | Recovery is front-loaded for closures and slow for capacity loss.**')
para('For the top-1 closure Q starts at 0.82 (an 18% shortfall) and passes 0.95 within 9 days, giving R = 0.98, equivalent to 1.5 days of total outage. '
     'The top-5 closure starts at 0.65 and recovers in 26 days (R = 0.95, 4.5 days lost); the 3 km flood starts at 0.93 and takes 24 days (R = 0.97, 3.2 days). '
     'Capacity loss on the busiest links recovers slowly: at 50%, Q starts at 0.52, takes 69 days to pass 0.95 and loses 15.6 days (R = 0.83); at 25%, Q starts at 0.06, takes 76 days and loses 32 days (R = 0.64). '
     'The pattern follows from the convex delay curve: restoring a closed link to even 10% of capacity recovers most of its value, so the first repairs matter most. '
     'The linear schedule is an assumption; real repairs are staged.', after=4)
para('**Key takeaways, Q2.** (i) Severity is set by how much capacity is removed, not how many links fail. (ii) A single corridor carries the worst closures. '
     '(iii) Early partial restoration is worth most. (iv) Report unserved demand and per-trip time, not total travel time alone.', after=4)

# =========================================================================== Q3
doc.add_heading('Question 3. Sensitivity analysis', level=1)
para('Three methods test how far the conclusions depend on assumptions. Each run is compared with a baseline solved with the same parameter values; otherwise, changing α, β or demand '
     'mostly moves the baseline itself, which an earlier version of this analysis did not account for. Two reference disruptions were used: a 3 km flood (impact ratio 1.08) and the top-3 closure (1.39).', after=3)

doc.add_heading('3.1 What matters depends on the disruption (one-at-a-time sweep)', level=2)
para('Each parameter is swept over its range while others stay fixed; the swing is the resulting spread in the output y:', after=2, keep=True)
eq(SUB(R('S'), R('i')), R('='), SUB(R('max', up=True), R('k')) + SUB(R('y'), R('k')) + R('−') + SUB(R('min', up=True), R('k')) + SUB(R('y'), R('k')))
figure('F8_tornado.png', '**Figure 4 | Flood impact is set by the hazard; closure impact is set by the congestion curve.**')
para('For the flood, only its size matters: radius swings the impact ratio by 0.65 (1.001 at 1 km to 1.65 at 5 km) and depth by 0.06, while BPR β, demand and α each move it by under 0.01. '
     'For the closure the order reverses: β swings it by 6.0, demand by 0.93 and α by 0.62, while the solver tolerance moves it by 0.002 in both cases. '
     'The reason is physical. A flood changes how many links are affected; a closure forces traffic onto fewer roads, pushing flow-to-capacity to about 4.6, '
     'where the β-th power amplifies every assumption. A parameter that is irrelevant for one hazard therefore dominates for another, so sensitivity results do not transfer between hazards. '
     'Value of time, truck share and passenger-car equivalents only scale the economic cost linearly and are excluded.', after=4)

doc.add_heading('3.2 Nonlinearity and interactions (Morris screening)', level=2)
para('Morris screening^{8,9} moves one parameter at a time along random paths and records the elementary effect EE. Its mean absolute value μ* measures importance and its '
     'spread σ measures nonlinearity or interaction with other parameters^{10}:', after=2, keep=True)
eq(SUB(R('EE'), R('i')), R('='), FRAC(R('y') + D(R('x+Δ') + SUB(R('e'), R('i'))) + R('−y') + D(R('x')), R('Δ')))
eq(SUBSUP(R('μ'), R('i'), R('*')), R('='), FRAC(R('1'), R('r')), NARY('∑', R('j=1'), R('r'), R('|') + SUBSUP(R('EE'), R('i'), R('(j)')) + R('|')), R(',    '),
   SUB(R('σ'), R('i')), R('='),
   RAD(FRAC(R('1'), R('r−1')) + NARY('∑', R('j=1'), R('r'), SUP(D(SUBSUP(R('EE'), R('i'), R('(j)')) + R('−') + SUB(R('EE'), R('i'))), R('2')))))
para('With r = 16 paths (112 runs, run with SALib^{11}) on the flood reference, flood radius has μ* = 0.53 and σ = 0.86, flood depth 0.38 and 0.73, and β 0.17 and 0.48; demand, α and the solver gap stay below 0.04. '
     'In all three leading cases σ exceeds μ*, so effects are nonlinear or interact: the harm from a larger flood depends on how large the footprint is, and vice versa. '
     'For accessibility loss, radius (μ* = 0.26, σ = 0.16) and depth (0.15, 0.12) are closer to additive. '
     'One-at-a-time sweeps therefore understate combined effects. The bars are wide (95% intervals of ±0.4 for radius), so the ranking is reliable but the exact values are not.', after=3)
figure('F10_morris.png', '**Figure 5 | Flood size and the BPR exponent act nonlinearly (σ above μ*).** Points above the dashed line interact or respond nonlinearly.')

doc.add_heading('3.3 Numerical choices', level=2)
para('The Frank–Wolfe solver^{12} stops when the relative gap falls below ε. Sweeping ε from 10⁻² to 10⁻⁵ shows that absolute travel time needs ε ≤ 10⁻³ '
     '(baseline error +1.19% at 10⁻², +0.07% at 10⁻³, −0.01% at 10⁻⁴), while impact ratios are already stable at 10⁻² (error ≤ 0.12%) and ≤ 0.07% from 10⁻³ down^{13}. '
     'Each tenfold tightening costs 2–5 times more iterations (12–50 at 10⁻⁴, 33–260 at 10⁻⁵). A single assignment iteration with no equilibrium overstates the impact by 1.0% for the flood, 0.1% for the closure '
     'and 5.3% for the arterial capacity cut (2.04 versus 1.94), so it is an acceptable screening shortcut except under heavy congestion.', after=3)
figure('F13_numerical.png', '**Figure 6 | Solver tolerance is a negligible source of error compared with parameter choice.**')

doc.add_heading('Implications for the reliability of risk assessments and resilience planning', level=2)
bullet('**Parameter uncertainty dwarfs numerical error.** Solver tolerance changes impacts by 0.1% or less; plausible BPR parameters change severe outcomes by factors of 5 to 200. '
       'Assessments should report ranges, and BPR curves should be calibrated on local speed–flow data, especially where flow-to-capacity exceeds 2 (our severe scenarios reach 4.6–7.6, outside the range the curve was built for).')
bullet('**Rankings are more reliable than magnitudes.** The order of hazards and of critical links is stable across parameters, so the results are sound for prioritising where to act, '
       'but absolute delay and cost figures for severe events should not feed cost–benefit analysis without calibration.')
bullet('**Sensitivity does not transfer across hazards, and effects interact.** Each hazard needs its own sensitivity analysis, and global methods such as Morris screening should replace one-at-a-time sweeps.')
bullet('**Choice of metric changes the conclusion.** Total travel time alone misses isolated zones and demand growth; reports should pair it with unserved demand and per-trip time.')
bullet('**For resilience planning,** concentrate redundancy on the few critical corridors, schedule repairs so the earliest partial restorations go to the most loaded links, '
       'and treat network-wide capacity stress as a demand-management problem. Limits: no demand response or queue spill-back, a synthetic flood, and assumed economic parameters.')

# =========================================================================== references
doc.add_heading('References', level=2)
refs = [
    'Transportation Networks for Research Core Team. Transportation Networks for Research (TNTP): Anaheim. https://github.com/bstabler/TransportationNetworks',
    'Bureau of Public Roads. Traffic Assignment Manual (U.S. Department of Commerce, 1964).',
    'Pregnolato, M., Ford, A., Wilkinson, S. M. & Dawson, R. J. The impact of flooding on road transport: a depth-disruption function. Transp. Res. D 55, 67–81 (2017).',
    'Hansen, W. G. How accessibility shapes land use. J. Am. Inst. Plann. 25, 73–76 (1959).',
    'Jenelius, E., Petersen, T. & Mattsson, L.-G. Importance and exposure in road network vulnerability analysis. Transp. Res. A 40, 537–560 (2006).',
    'Scott, D. M., Novak, D. C., Aultman-Hall, L. & Guo, F. Network Robustness Index: a new method for identifying critical links and evaluating the performance of transportation networks. J. Transp. Geogr. 14, 215–227 (2006).',
    'Bruneau, M. et al. A framework to quantitatively assess and enhance the seismic resilience of communities. Earthq. Spectra 19, 733–752 (2003).',
    'Morris, M. D. Factorial sampling plans for preliminary computational experiments. Technometrics 33, 161–174 (1991).',
    'Campolongo, F., Cariboni, J. & Saltelli, A. An effective screening design for sensitivity analysis of large models. Environ. Model. Softw. 22, 1509–1518 (2007).',
    'Saltelli, A. et al. Global Sensitivity Analysis: The Primer (Wiley, 2008).',
    'Herman, J. & Usher, W. SALib: an open-source Python library for sensitivity analysis. J. Open Source Softw. 2, 97 (2017).',
    'Frank, M. & Wolfe, P. An algorithm for quadratic programming. Nav. Res. Logist. Q. 3, 95–110 (1956).',
    'Boyce, D., Ralevic-Dekic, B. & Bar-Gera, H. Convergence of traffic assignments: how much is enough? J. Transp. Eng. 130, 49–55 (2004).',
]
for i, t in enumerate(refs, 1):
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.left_indent = Inches(0.25); p.paragraph_format.first_line_indent = Inches(-0.25)
    rich(p, f'{i}. {t}', 9)

doc.save(OUT); print('saved', OUT)
