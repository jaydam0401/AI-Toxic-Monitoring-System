"""Arduino PPM logger + 5-second-ahead ML prediction.
Usage: python monitor_ai.py --port /dev/cu.usbmodemXXXX
Demo:  python monitor_ai.py --demo
"""
import argparse
import csv
import math
import random
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import numpy as np
from openpyxl import Workbook, load_workbook
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

ROOT = Path(__file__).resolve().parent
LOG = ROOT / 'ppm_ai_log.xlsx'
SHEET = '측정기록'
EVENTS = '경고이력'
HEADERS = ['측정시간', 'PPM', '현재단계', '5초후_AI예측PPM', '예측단계', 'AI사전경고']
EVENT_HEADERS = ['발생시간', '이벤트', 'PPM', '내용']
HORIZON = 5
WINDOW = 5


def level(v):
    if v <= 250: return 'SAFE'
    if v <= 500: return 'CAUTION'
    if v <= 750: return 'WARNING'
    return 'DANGER'


def features(vals):
    a = np.asarray(vals[-WINDOW:], dtype=float)
    dif = np.diff(a)
    return np.array([*a, *dif, float(np.mean(a)), float(np.std(a))], dtype=float)


def load_book():
    if LOG.exists():
        wb = load_workbook(LOG)
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = SHEET
        ws.append(HEADERS)
        ws.freeze_panes = 'A2'
        ev = wb.create_sheet(EVENTS)
        ev.append(EVENT_HEADERS)
        ev.freeze_panes = 'A2'
        wb.save(LOG)
    if SHEET not in wb:
        wb.create_sheet(SHEET).append(HEADERS)
    if EVENTS not in wb:
        wb.create_sheet(EVENTS).append(EVENT_HEADERS)
    return wb


def train_model(series):
    # 시계열 순서 유지: 과거 80% 학습, 이후 20% 평가
    xs, ys = [], []
    for i in range(WINDOW - 1, len(series) - HORIZON):
        xs.append(features(series[i-WINDOW+1:i+1]))
        ys.append(series[i+HORIZON])
    if len(xs) < 30:
        return None, None
    cut = max(1, int(len(xs) * 0.8))
    if cut >= len(xs): return None, None
    x, y = np.array(xs), np.array(ys)
    evaluator = RandomForestRegressor(n_estimators=80, random_state=42, min_samples_leaf=2)
    evaluator.fit(x[:cut], y[:cut])
    mae = mean_absolute_error(y[cut:], evaluator.predict(x[cut:]))
    # 실제 운용 모델은 평가 후 전체 데이터로 재학습
    model = RandomForestRegressor(n_estimators=80, random_state=42, min_samples_leaf=2)
    model.fit(x, y)
    return model, mae


def demo_values():
    rng = random.Random(42)
    t = 0
    while True:
        # 상승/하강 반복하는 시뮬레이션 데이터
        v = 510 + 350 * math.sin(t / 19) + 70 * math.sin(t / 6) + rng.uniform(-12, 12)
        yield max(0, min(1023, round(v)))
        t += 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--port', help='Arduino serial port, e.g. /dev/cu.usbmodem1101 or COM3')
    p.add_argument('--baud', type=int, default=9600)
    p.add_argument('--demo', action='store_true', help='simulate without Arduino')
    p.add_argument('--interval', type=float, default=1.0, help='demo sample interval seconds')
    args = p.parse_args()
    if not args.demo and not args.port:
        p.error('--port required unless --demo')
    wb = load_book()
    series = []
    # 기존 저장 데이터로 재학습 가능
    for row in wb[SHEET].iter_rows(min_row=2, values_only=True):
        if isinstance(row[1], (int, float)):
            series.append(int(row[1]))
    model, mae = train_model(series)
    last_level = None
    last_pred_alert = False
    samples_since_train = 0
    serial_obj = None
    if args.demo:
        stream = demo_values()
        print('DEMO mode (simulated values)')
    else:
        import serial
        serial_obj = serial.Serial(args.port, args.baud, timeout=2)
        time.sleep(2)  # UNO resets on serial connection
        serial_obj.reset_input_buffer()
        stream = None
        print(f'Connected to {args.port}')
    print('Saving:', LOG)
    try:
        while True:
            if args.demo:
                ppm = next(stream)
            else:
                line = serial_obj.readline().decode('utf-8', errors='ignore').strip()
                if not line.startswith('PPM,'):
                    continue  # ignore existing diagnostic Serial.print lines
                try:
                    ppm = int(line.split(',', 1)[1])
                except ValueError:
                    continue
                if not 0 <= ppm <= 1023:
                    continue
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            series.append(ppm)
            current = level(ppm)
            prediction = None
            predicted_level = ''
            alert = ''
            if model is not None and len(series) >= WINDOW:
                prediction = round(float(np.clip(model.predict([features(series)])[0], 0, 1023)))
                predicted_level = level(prediction)
                # pre-alert only if predicted WARNING/DANGER is above current level
                if predicted_level in ('WARNING', 'DANGER') and current in ('SAFE', 'CAUTION'):
                    alert = f'AI 사전경고: 5초 후 {predicted_level} 예상'
            wb[SHEET].append([now, ppm, current, prediction, predicted_level, alert])
            if current != last_level:
                wb[EVENTS].append([now, '단계변경', ppm, f'{last_level or "시작"} → {current}'])
                last_level = current
            pred_alert_now = bool(alert)
            if pred_alert_now and not last_pred_alert:
                wb[EVENTS].append([now, 'AI 사전경고', ppm, alert])
            last_pred_alert = pred_alert_now
            wb.save(LOG)
            print(f'{now} | {ppm:4d} | {current:7s} | AI+5s: {str(prediction):>4s} | {alert}')
            samples_since_train += 1
            if samples_since_train >= 30:
                model, mae = train_model(series)
                samples_since_train = 0
                if mae is not None:
                    print(f'AI trained | chronological holdout MAE: {mae:.1f} PPM')
            if args.demo:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print('\nStopped. Excel saved:', LOG)
    finally:
        if serial_obj:
            serial_obj.close()
        wb.save(LOG)

if __name__ == '__main__':
    main()
