<!-- Header banner -->
<p align="center">
  <img src="demo.jpg" alt="Pigeon Patrol locking onto a pigeon" width="80%"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Raspberry%20Pi-5-A22846?style=for-the-badge&logo=raspberrypi&logoColor=white" alt="Raspberry Pi 5"/>
  <img src="https://img.shields.io/badge/YOLO11n-Ultralytics-00C8FF?style=for-the-badge" alt="YOLO11n"/>
  <img src="https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white" alt="OpenCV"/>
  <img src="https://img.shields.io/badge/Supabase-3FCF8E?style=for-the-badge&logo=supabase&logoColor=white" alt="Supabase"/>
  <img src="https://img.shields.io/badge/status-in%20development-FFC107?style=for-the-badge" alt="Status"/>
</p>

<p align="center">
  <b>Spot it. Track it. Splash it.</b>
</p>

---

<!-- Swap this for a real GIF of the turret once it's on the roof -->
<p align="center">
  <img src="docs/demo.gif" width="720" alt="Pigeon Patrol tracking a pigeon"/>
</p>

## 🐦 The problem

My apartment complex has a pigeon problem, and my neighbors are tired of it. People walking into the building get hit with poop. Balconies get plastered with white splats. It's gross, and it's been going on for months.

After months of watching this happen, I walked into my leasing office and pitched them a solution, which is this project. Turns out they were actually planning to poison all the pigeons. They told me that if I could make this work, they'd rather go with it. So they agreed, and now I'm building it to save the pigeons from a sudden death and make my apartment a little less gross.

The idea is simple. The turret sees a pigeon, confirms it's actually a pigeon, aims, and gives it a short harmless spray of water. Pigeons hate getting wet, are easily startled, and they learn fast. Nobody gets poisoned, and nobody gets pooped on.

```yaml
project:    Pigeon Patrol
builder:    Sierra Ryan
hardware:   Raspberry Pi 5 + Camera Module 3 Wide + pan/tilt servos + 12V pump
model:      YOLO11n (COCO class 14, "bird")
runs:       fully on device, no cloud inference
reports_to: Supabase (event log + snapshots for building maintenance)
approved:   yes, by my leasing office (instead of poisoning the pigeons)
```

## ⚙️ How it works

Every frame goes through the same loop. The turret only fires after the same bird shows up in 5 frames in a row, so a single bad detection never sets it off.

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> TRACKING: bird detected
    TRACKING --> IDLE: bird lost
    TRACKING --> FIRING: same bird for 5 frames
    FIRING --> COOLDOWN: burst finished
    COOLDOWN --> IDLE: cooldown over
```

| Stage | What happens |
|---|---|
| **Detect** | YOLO11n looks for birds in each 1280x720 frame from the wide camera |
| **Track** | Sticks to the bird closest to where it was last frame, and resets if it jumps too far |
| **Confirm** | Needs 5 frames in a row (about 1 second) before it commits |
| **Aim** | Converts the bird's pixel position into pan and tilt servo angles |
| **Fire** | Pump runs for a short burst through a MOSFET on GPIO17 |
| **Log** | Saves a clean and an annotated snapshot, then uploads both to Supabase |

```mermaid
flowchart LR
    A[Camera Module 3 Wide] --> B[YOLO11n on Pi 5]
    B --> C{Confirmed bird?}
    C -- yes --> D[Servos aim]
    D --> E[Pump fires]
    C -- yes --> F[Snapshots + event]
    F --> G[(Supabase)]
    G --> H[Maintenance dashboard]
```

## 🛠️ Built with

<p align="left">
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg" width="45" height="45" alt="Python"/>
  &nbsp;
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/opencv/opencv-original.svg" width="45" height="45" alt="OpenCV"/>
  &nbsp;
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/raspberrypi/raspberrypi-original.svg" width="45" height="45" alt="Raspberry Pi"/>
  &nbsp;
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/supabase/supabase-original.svg" width="45" height="45" alt="Supabase"/>
  &nbsp;
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/postgresql/postgresql-original.svg" width="45" height="45" alt="PostgreSQL"/>
  &nbsp;
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/git/git-original.svg" width="45" height="45" alt="Git"/>
</p>

### Hardware

| Part | Job |
|---|---|
| Raspberry Pi 5 (8GB) + active cooler | The brain. Runs detection, tracking and control |
| Camera Module 3 Wide | Wide view of the roof with continuous autofocus |
| PCA9685 servo driver (I2C) | Drives the servos with clean PWM |
| 2x DS3225 25kg servos + pan/tilt bracket | Aim the nozzle |
| 12V diaphragm pump + MOSFET module | Water on, water off |
| Buck converter (12V to 6V) | Powers the servos |
| Float switch | Stops the pump when the tank runs dry |
| Kill switch + inline fuse | Because water and electricity |
| Gutted toy water gun | Mostly for looks, honestly |

## 📁 Repo layout

```
pigeon_patrol/
├── detect.py      # main loop: detection, tracking, state machine, logging
├── turret.py      # real servo + pump control
├── uploader.py    # background uploads to Supabase
├── data/          # test videos (not committed)
├── snapshots/     # local shot images (not committed)
└── .env           # Supabase keys, lives only on the Pi (never committed)
```

## 🚀 Running it

```bash
git clone https://github.com/sryanprograms/pigeon_patrol.git
cd pigeon_patrol

# On the Pi, include system packages so picamera2 works
python -m venv --system-site-packages .venv
source .venv/bin/activate
pip install ultralytics opencv-python adafruit-circuitpython-servokit supabase python-dotenv

# Test on a video
python detect.py data/pigeons.mov

# Live camera on the Pi
python detect.py camera
```

To upload events, make a `.env` file on the Pi with `SUPABASE_URL` and `SUPABASE_SECRET_KEY`. Without it the turret still runs and just skips uploading.

## 🗺️ Roadmap

- [x] Bird detection on recorded video
- [x] Live detection on the Pi camera
- [x] Sticky tracking and 5 frame confirmation
- [x] Snapshot logging (clean and annotated)
- [x] Event and snapshot uploads to Supabase
- [ ] Servos and pump wired and bench tested
- [ ] Pixel to angle calibration
- [ ] Safety checks (person detection, firing zone, servo limits)
- [ ] Weatherproof enclosure and roof install
- [ ] Video clips of each spray
- [ ] Maintenance dashboard with daily stats
- [ ] Faster inference (NCNN export)

## 🛡️ Safety

- Water only, short bursts, aimed at birds that are on the roof
- The pump always shuts off when the program stops or crashes
- The turret will not fire if a person is in view (in progress)
- Snapshots go to a private bucket that only signed in building staff can see

## 👋 About me

I'm Sierra, a Data Science student at Arizona State with a concentration in Geospatial AI Systems and I love building computer vision, GIS, and autonomy projects!

<p align="left">
  <a href="https://github.com/sryanprograms"><img src="https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"/></a>
  <!-- Add your LinkedIn URL below -->
  <a href="https://www.linkedin.com/in/YOUR-LINKEDIN"><img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn"/></a>
</p>

<!-- Footer banner -->
<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0050A0,100:00C8FF&height=120&section=footer" alt="footer"/>
</p>
