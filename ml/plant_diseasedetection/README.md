# Plant Disease Detection — YOLOv11x (116 classes)

This package wraps the
[Multi-Domain Plant Disease Detection: A YOLOv11x Benchmark on 116 Classes](https://github.com/SIV-TK/A-YOLOv11x-Benchmark-on-116-Classes-Using-Combined-Laboratory-and-Field-Images)
model (trained weights hosted on Hugging Face: `Ananthakrishnanmzen/PlantDiseaseDetection`).

## Model card

| Item | Value |
|------|-------|
| Architecture | YOLOv11x (57 M parameters) |
| Input size | 640 × 640 px |
| Total classes | 116 (major food crops) |
| Total images | 23,689 (train 16,582 / val 4,737 / test 2,370) |
| mAP50 | 69.8% |
| mAP50-95 | 68.4% |
| Precision | 62.2% |
| Recall | 69.5% |
| License | MIT |

## Quick start

```bash
# from the repo root
pip install -r ml/plant_diseasedetection/requirements.txt
```

```python
from ml.plant_diseasedetection import PlantDiseaseDetector

detector = PlantDiseaseDetector()  # downloads weights on first use
results = detector.predict("path/to/leaf.jpg", conf=0.25)
for r in results:
    for box in r.boxes:
        print(detector.class_name(int(box.cls[0])), f"{float(box.conf[0]):.2%}")
```

## Weight files

Pre-trained weights (`PlantDiseaseDetection.pt`) are fetched automatically from
Hugging Face on first load via `ultralytics` / `huggingface_hub`. To bundle weights
locally, place `PlantDiseaseDetection.pt` (and any other `.pt`) in
`ml/plant_diseasedetection/weights/`.

```
ml/plant_diseasedetection/
├── __init__.py
├── model.py
├── inference.py
├── requirements.txt
├── data.yaml
├── README.md
└── weights/
    └── .gitkeep
```

## Citation

```
@software{kariuki_2026_plant_disease,
  author = {Kariuki, James Kariuki},
  title  = {Multi-Domain Plant Disease Detection: A YOLOv11x Benchmark on 116 Classes},
  year   = {2026},
  url    = {https://github.com/SIV-TK/A-YOLOv11x-Benchmark-on-116-Classes-Using-Combined-Laboratory-and-Field-Images},
}
```
