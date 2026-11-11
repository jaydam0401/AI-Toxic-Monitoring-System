# AI-Toxic-Monitoring-System
Arduino-based monitoring and AI concentration prediction system
# AI 기반 독성물질 모니터링 및 농도 예측 시스템

### Arduino UNO × Python × Machine Learning

> **현재 농도를 감지하고, AI로 미래 위험 단계를 예측하는 임베디드 모니터링 프로젝트**

Arduino UNO와 Python 머신러닝을 연동하여 모의 농도 데이터를 수집하고, 위험 단계를 표시하며, 미래 농도를 예측하는 시스템입니다.

본 프로젝트는 **가변저항을 활용한 모의 농도 측정 시스템**으로, 실제 유해가스 센서를 이용한 측정 장비는 아닙니다.

---

## 01. 프로젝트 개요

| 항목 | 내용 |
|---|---|
| 프로젝트 | AI 기반 독성물질 모니터링 및 농도 예측 시스템 |
| 개발 환경 | Arduino IDE, Python, VS Code |
| 하드웨어 | Arduino UNO, LCD, NeoPixel, 7-Segment, Buzzer, HC-06 |
| AI 모델 | Random Forest Regressor |
| 통신 방식 | USB Serial, Bluetooth |
| 데이터 관리 | Excel 자동 기록 및 Matplotlib 그래프 |

## 02. 주요 기능

- **실시간 모니터링:** 가변저항 입력값을 기반으로 모의 농도 표시
- **4단계 위험 분류:** SAFE / CAUTION / WARNING / DANGER
- **시각·청각 경고:** LCD, NeoPixel, 7-Segment, 부저 연동
- **Bluetooth 통신:** HC-06을 통한 스마트폰 앱 데이터 전송
- **AI 농도 예측:** 최근 측정 데이터를 이용해 약 5초 후 농도 예측
- **AI 사전경고:** 현재보다 높은 위험 단계가 예측되는 일부 상황에서 경고 생성
- **데이터 자동 기록:** 측정값과 AI 예측값, 경고 이력을 Excel 파일로 저장

## 03. 시스템 구성

```text
가변저항(A2)
     |
     v
Arduino UNO
     |
     +---- LCD / NeoPixel / 7-Segment / Buzzer
     |
     +---- HC-06 Bluetooth → 스마트폰 앱
     |
     +---- USB Serial → Python
                           |
                           v
                    Random Forest AI
                           |
                    농도 예측 및 사전경고
                           |
                           v
                     Excel 데이터 기록
                           |
                           v
                    Matplotlib 그래프
```

## 04. AI 예측 시스템

### Random Forest Regressor

Python의 `scikit-learn` 라이브러리를 활용해 농도 예측 모델을 구현했습니다.

1. Arduino에서 모의 농도 데이터를 수신합니다.
2. 최근 5개 측정값과 변화량, 평균, 표준편차를 특징값으로 구성합니다.
3. Random Forest 모델을 학습시킵니다.
4. 5개 샘플 이후의 농도값을 예측합니다.
5. 예측 위험 단계가 현재보다 높아지는 일부 상황에서 사전경고를 기록합니다.

데이터 수집 간격이 약 1초일 때 예측 시점은 **약 5초 후**에 해당합니다.

학습 시 시간 순서를 유지하여 과거 80% 데이터를 학습에, 이후 20% 데이터를 평가에 사용하며, 모델 평가 후 전체 데이터로 재학습합니다.

### AI 사전경고 사례

| 항목 | 값 |
|---|---|
| 현재 모의 농도 | 478 |
| 현재 위험 단계 | CAUTION |
| AI 예측 농도 | 593 |
| 예측 위험 단계 | WARNING |
| 결과 | AI 사전경고 생성 |

*실제 기록에서 확인된 예측 사례이며, 예측 정확도를 입증하는 수치는 아닙니다.*

## 05. 위험 단계 분류

| 모의 농도값 | 단계 | 표시 |
|---|---|---|
| 0–250 | SAFE | 초록색 |
| 251–500 | CAUTION | 노란색 |
| 501–750 | WARNING | 주황색 |
| 751–1023 | DANGER | 빨간색 |



## 06. 프로그램 실행 방법 (macOS)

### 1. 필요한 Python 라이브러리 설치

```bash
python3 -m pip install -r requirements.txt
```

### 2. Arduino USB 포트 확인

Arduino UNO를 맥북에 연결하고 VS Code 터미널에서 실행합니다.

```bash
ls /dev/cu.usb*
```

### 3. AI 농도 예측 프로그램 실행

```bash
python3 monitor_ai.py --port /dev/cu.usbmodem1101
```

**주의:** `/dev/cu.usbmodem1101`은 예시이므로 실제 확인된 포트 이름으로 변경해야 합니다.

프로그램 실행 시 Arduino의 모의 농도 데이터를 수신하고 AI 예측값과 위험 단계를 출력하며 Excel에 자동 기록합니다.

### 4. 측정 종료 및 Excel 파일 열기

터미널에서 `Control + C`를 눌러 측정을 종료합니다.

```bash
open ppm_ai_log.xlsx
```

### 5. AI 예측 그래프 생성

```bash
python3 ppm_graph.py
```

측정값과 AI 예측값을 비교한 그래프가 표시되며 `ppm_ai_graph.png`로 저장됩니다.

### 6. Arduino 없이 AI 테스트하기

```bash
python3 monitor_ai.py --demo
```

**실행 전 확인:** Arduino IDE 시리얼 모니터를 닫고, VS Code 터미널에서 Python 파일들이 저장된 폴더로 이동해야 합니다.

## 07. 프로젝트 결과

- Arduino와 Python 간 USB 시리얼 데이터 연동
- AI 예측값 및 위험 단계 출력
- Excel 측정기록·경고이력 자동 저장
- 실제 측정값과 AI 예측값 비교 그래프 생성

## 08. 프로젝트 시연 영상

유튜브 시연 영상 링크를 여기에 추가할 예정입니다.

## 09. 주요 소스코드

| 파일 | 설명 |
|---|---|
| `PPM_AI.ino` | Arduino 하드웨어 제어 및 데이터 송신 |
| `monitor_ai.py` | 머신러닝 예측 및 Excel 기록 |
| `ppm_graph.py` | 측정값과 AI 예측값 그래프 |
| `requirements.txt` | Python 실행 라이브러리 |

---

**참고:** 본 시스템의 PPM 표기는 가변저항으로 생성한 0~1023 범위의 모의 수치입니다. 실제 독성물질 농도 측정이나 안전 판단을 위한 시스템이 아닙니다.
