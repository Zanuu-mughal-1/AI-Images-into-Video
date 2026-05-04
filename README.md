# Cinematic Video Generation Pipeline (API-Free)

This tool generates smooth, professional cinematic videos from keyframe images using local optical flow interpolation. No paid APIs, no cloud dependencies.

## 📂 Folder Structure

Organize your images into scenes like this:

```text
scenes/
├── scene_01/
│   ├── 01.png
│   ├── 02.png
│   └── 03.png
├── scene_02/
│   ├── 01.png
│   └── 02.png
audio/
└── background.mp3 (Optional)
config.yaml
video_pipeline.py
```

- **Scenes**: Subfolders are processed alphabetically. Images inside are interpolated in order.
- **Interpolation**: The tool uses Farneback Optical Flow to create smooth movement between your keyframes.
- **Transitions**: A 1-second cross-dissolve is automatically added between scene folders.

## 🚀 How to Run

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Generate Video**:
   ```bash
   python video_pipeline.py
   ```

3. **Check Output**:
   The final video will be saved at `output/final_video.mp4`.

## 🎨 Creative Guide

### 1. Generating Keyframes (Free Tools)
Use these free AI tools to generate consistent keyframes for your scenes:
- **Ideogram**: Excellent for typography and stylistic consistency.
- **Playground AI**: Great for cinematic realistic environments.
- **Adobe Firefly**: High-quality artistic textures and lighting.

*Tip: Use "Image-to-Image" or "Reference Image" features in these tools to keep the character or environment the same across keyframes.*

### 2. Adding Audio
- **Pixabay / Mixkit**: Download free cinematic background music.
- **Suno / Udio**: Generate your own custom AI music tracks.
- Place your file at `audio/background.mp3`. If no file is found, the script will generate a subtle ambient drone automatically.

## ⚙️ Configuration

Edit `config.yaml` to change:
- **FPS**: Set to 24 for a cinematic look.
- **Seconds per scene**: Control the pacing of your video.
- **CRF**: Adjust video quality (18 is high quality, 24 is standard).
- **Color Grading**: Tweak the `vignette_strength` or `warm_shift` (BGR format).

---
*Built with OpenCV, NumPy, and FFmpeg.*
