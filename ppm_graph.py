"""Plot saved PPM readings and 5-second-ahead forecasts from ppm_ai_log.xlsx."""
from pathlib import Path
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from openpyxl import load_workbook

root = Path(__file__).resolve().parent
path = root / 'ppm_ai_log.xlsx'
if not path.exists():
    raise SystemExit(f'엑셀 파일을 찾을 수 없습니다: {path}\nppm_graph.py를 monitor_ai.py와 같은 폴더에 넣으세요.')
wb = load_workbook(path, read_only=True, data_only=True)
ws = wb['측정기록']
records = []
for row in ws.iter_rows(min_row=2, values_only=True):
    if not row or not isinstance(row[1], (int, float)):
        continue
    try:
        t = row[0] if isinstance(row[0], datetime) else datetime.strptime(str(row[0]), '%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        continue
    pred = row[3] if len(row) > 3 and isinstance(row[3], (int, float)) else None
    records.append((t, row[1], pred))
if not records:
    raise SystemExit('측정기록 시트에 데이터가 없습니다. 먼저 --demo를 실행하세요.')
records = records[-300:]
times = [r[0] for r in records]
actual = [r[1] for r in records]
pred_times = [r[0] + timedelta(seconds=5) for r in records if r[2] is not None]
pred = [r[2] for r in records if r[2] is not None]
plt.figure(figsize=(11, 5))
plt.plot(times, actual, label='Actual PPM', linewidth=2)
if pred:
    plt.plot(pred_times, pred, label='AI forecast (+5 sec)', linewidth=1.7, linestyle='--')
for y, label in [(250, 'SAFE'), (500, 'CAUTION'), (750, 'WARNING')]:
    plt.axhline(y, linewidth=0.8, linestyle=':', alpha=0.6)
plt.ylim(0, 1023)
plt.xlabel('Time')
plt.ylabel('Simulated PPM')
plt.title('PPM readings vs AI 5-second forecast')
plt.legend()
plt.grid(alpha=0.2)
plt.gcf().autofmt_xdate()
plt.tight_layout()
out = root / 'ppm_ai_graph.png'
plt.savefig(out, dpi=160)
print(f'그래프 저장 완료: {out}')
plt.show()
