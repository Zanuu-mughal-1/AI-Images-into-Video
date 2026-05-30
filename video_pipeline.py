"""
video_pipeline.py
-----------------
Complete, API-free cinematic video generation tool.
Interpolates keyframes from scene folders using local Optical Flow techniques.
"""

import os
import sys
import cv2
import glob
import yaml
import math
import shutil
import subprocess
import numpy as np
from pathlib import Path
from tqdm import tqdm
from pydub import AudioSegment
import imageio_ffmpeg
# Ok

# Python 3.13 compatibility: audioop was removed, use audioop-lts if available
try:
    import audioop
except ImportError:
    try:
        import audioop_lts as audioop  # type: ignore
        sys.modules['audioop'] = audioop
    except ImportError:
        pass

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
# Configure pydub to use our FFmpeg binary
AudioSegment.converter = FFMPEG_EXE

# Force UTF-8 for Windows console emojis
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ==============================================================================
# 1. CORE FUNCTIONS
# ==============================================================================

def load_config():
    # Ok - loading config
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def get_scenes():
    # Ok - scanning scenes directory
    scene_dir = Path("scenes")
    if not scene_dir.exists():
        scene_dir.mkdir()
        print("📁 Created 'scenes/' directory. Add subfolders (scene_01, scene_02) with images.")
        sys.exit(0)
    
    scenes = sorted([d for d in scene_dir.iterdir() if d.is_dir()])
    return scenes

def get_scene_images(scene_path):
    # Ok - collecting image files
    exts = ('.png', '.jpg', '.jpeg', '.webp')
    images = sorted([p for p in scene_path.iterdir() if p.suffix.lower() in exts])
    return images

def interpolate_frames(img1, img2, num_frames, flow=None):
    """
    Interpolate between two frames using Farneback Optical Flow.
    Applies median blur to flow to reduce 'twinkling' artifacts.
    """
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # Compute flow if not provided (re-use for efficiency if possible)
    # Ok - computing optical flow
    if flow is None:
        flow = cv2.calcOpticalFlowFarneback(gray1, gray2, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        # Apply median blur to flow field as requested
        flow[..., 0] = cv2.medianBlur(flow[..., 0], 5)
        flow[..., 1] = cv2.medianBlur(flow[..., 1], 5)

    frames = []
    h, w = img1.shape[:2]
    
    for i in range(num_frames):
        t = (i + 1) / (num_frames + 1)
        # Ease-in-out alpha curve
        alpha = 0.5 - 0.5 * math.cos(math.pi * t)
        
        # Warp both images towards each other
        map_f = np.zeros((h, w, 2), dtype=np.float32)
        map_b = np.zeros((h, w, 2), dtype=np.float32)
        
        # Create meshgrid for remapping
        grid_y, grid_x = np.indices((h, w))
        
        map_f[..., 0] = grid_x + flow[..., 0] * alpha
        map_f[..., 1] = grid_y + flow[..., 1] * alpha
        
        map_b[..., 0] = grid_x - flow[..., 0] * (1 - alpha)
        map_b[..., 1] = grid_y - flow[..., 1] * (1 - alpha)
        
        warped1 = cv2.remap(img1, map_f, None, cv2.INTER_LANCZOS4)
        warped2 = cv2.remap(img2, map_b, None, cv2.INTER_LANCZOS4)
        
        # Blend warped frames
        # Ok - blending warped frames
        blended = cv2.addWeighted(warped1, 1 - alpha, warped2, alpha, 0)
        frames.append(blended)
        
    return frames, flow

def grade_frame(frame, vignette, color_shift):
    """Applies smooth, continuous cinematic grading.""" 
    # Ok - grading frame
    f = frame.astype(np.float32) / 255.0
    f = f * color_shift
    
    # Smooth cinematic contrast (Soft S-Curve)
    # This replaces the discontinuous 'np.where' that caused horrific banding.
    smooth = f * f * (3.0 - 2.0 * f)
    f = f * 0.8 + smooth * 0.2  # subtle 20% blend for a safe cinematic pop
    
    f = f * vignette
    return np.clip(f * 255, 0, 255).astype(np.uint8)

def deflicker(frames_dir):
    """Temporal smoothing pass over written PNGs."""
    # Ok - starting deflicker pass
    print("✨ Running deflicker pass ...")
    files = sorted(glob.glob(f"{frames_dir}/frame_*.png"))
    if len(files) < 5: return
    
    for i in tqdm(range(2, len(files)-2), desc="Smoothing"):
        center = cv2.imread(files[i]).astype(np.float32)
        # Sum 4 neighbors
        neighbors = (
            cv2.imread(files[i-2]).astype(np.float32) +
            cv2.imread(files[i-1]).astype(np.float32) +
            cv2.imread(files[i+1]).astype(np.float32) +
            cv2.imread(files[i+2]).astype(np.float32)
        ) / 4
        smoothed = 0.75 * center + 0.25 * neighbors
        cv2.imwrite(files[i], np.clip(smoothed, 0, 255).astype(np.uint8))

# ==============================================================================
# 2. AUDIO & ENCODING
# ==============================================================================

def handle_audio(video_duration, output_wav):
    # Ok - handling audio
    audio_path = Path("audio/background.mp3")
    if audio_path.exists():
        print(f"🎵 Using background audio: {audio_path}")
        try:
            sound = AudioSegment.from_file(str(audio_path))
            target_ms = video_duration * 1000
            
            if len(sound) < target_ms:
                # Loop
                sound = (sound * (int(target_ms / len(sound)) + 1))[:int(target_ms)]
            else:
                # Trim
                sound = sound[:int(target_ms)]
            
            # 1s fade out
            sound = sound.fade_out(1000)
            sound.export(output_wav, format="wav")
            return output_wav
        except Exception as e:
            print(f"⚠️ Audio processing failed: {e}. Generating ambient.")

    # Generate Ambient
    # Ok - generating ambient drone audio
    print("🎵 No audio/background.mp3 found. Generating ambient drone...")
    sr = 48000
    t = np.linspace(0, video_duration, int(sr * video_duration), False)
    # 55Hz fundamental + harmonics
    wave = (0.4 * np.sin(2 * np.pi * 55 * t) + 0.2 * np.sin(2 * np.pi * 110 * t))
    # Envelope
    env = np.ones_like(wave)
    env[:sr*2] = np.linspace(0, 1, sr*2) # 2s fade in
    env[-sr:] = np.linspace(1, 0, sr)   # 1s fade out
    wave = (wave * env * 0.3 * 32767).astype(np.int16)
    
    import wave as wav_lib
    with wav_lib.open(str(output_wav), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(wave.tobytes())
    return output_wav

# ==============================================================================
# 3. MAIN PIPELINE
# ==============================================================================

def main():
    # Ok - starting main pipeline
    cfg = load_config()
    H, W = cfg['resolution'][1], cfg['resolution'][0]
    FPS = cfg['fps']
    
    # Pre-compute Grading Masks
    # Ok - pre-computing vignette and color masks
    print("🎨 Pre-computing color grading masks...")
    Y, X = np.ogrid[:H, :W]
    cx, cy = W/2, H/2
    r = np.sqrt(((X-cx)/cx)**2 + ((Y-cy)/cy)**2)
    vignette = np.stack([(1.0 - cfg['vignette_strength']*r**2).clip(0,1)]*3, axis=-1).astype(np.float32)
    color_shift = np.array(cfg['warm_shift'], dtype=np.float32) # BGR

    # Setup directories
    output_dir = Path("output")
    frames_dir = output_dir / "frames"
    if frames_dir.exists(): shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)

    scenes = get_scenes()
    if not scenes:
        print("❌ No scenes found in scenes/ directory.")
        return

    all_keyframes = []
    for s in scenes:
        imgs = get_scene_images(s)
        if imgs: all_keyframes.append(imgs)

    if not all_keyframes:
        print("❌ No images found in any scene folder.")
        return

    print(f"🎬 Processing {len(all_keyframes)} scenes...")
    
    frame_idx = 1
    batch = []

    def flush_batch(batch_list, start_idx):
        for i, f in enumerate(batch_list):
            graded = grade_frame(f, vignette, color_shift)
            path = frames_dir / f"frame_{start_idx + i:06d}.png"
            cv2.imwrite(str(path), graded, [cv2.IMWRITE_PNG_COMPRESSION, cfg['png_compression']])
        batch_list.clear()

    # We need to chain all keyframes across all scenes
    flattened_keyframes = []
    for scene_imgs in all_keyframes:
        flattened_keyframes.extend(scene_imgs)

    # Process all transitions
    for i in range(len(flattened_keyframes) - 1):
        img_a_path = flattened_keyframes[i]
        img_b_path = flattened_keyframes[i+1]
        
        img_a = cv2.resize(cv2.imread(str(img_a_path)), (W, H), interpolation=cv2.INTER_LANCZOS4)
        img_b = cv2.resize(cv2.imread(str(img_b_path)), (W, H), interpolation=cv2.INTER_LANCZOS4)

        # ─── DURATION CALCULATION ───
        # Find which scene img_a belongs to
        scene_idx = 0
        cumulative = 0
        for idx, s_imgs in enumerate(all_keyframes):
            cumulative += len(s_imgs)
            if i < cumulative:
                scene_idx = idx
                break
        
        is_boundary = i == (cumulative - 1)
        scene_imgs_count = len(all_keyframes[scene_idx])

        if is_boundary:
            # Transition between scenes uses the full configured duration
            num_interp = int(cfg['seconds_per_scene'] * FPS)
        else:
            # Internal scene transitions divide the duration by number of gaps
            num_interp = int(cfg['seconds_per_scene'] * FPS / max(1, scene_imgs_count - 1))

        # Write first keyframe
        if i == 0:
            batch.append(img_a)
            if len(batch) >= cfg['batch_size']:
                num_written = len(batch)
                flush_batch(batch, frame_idx)
                frame_idx += num_written

        # Generate interpolated frames
        print(f"🎞️  Interpolating {img_a_path.name} -> {img_b_path.name}")
        interp_list, _ = interpolate_frames(img_a, img_b, num_interp)
        
        # Scene transition logic: Cross-dissolve at boundary
        if is_boundary:
            t_frames = num_interp
            dissolve_frames = []
            for j in range(t_frames):
                t = (j + 1) / (t_frames + 1)
                alpha = 0.5 - 0.5 * math.cos(math.pi * t)
                blended = cv2.addWeighted(img_a, 1 - alpha, img_b, alpha, 0)
                dissolve_frames.append(blended)
            batch.extend(dissolve_frames)
        else:
            batch.extend(interp_list)
        
        batch.append(img_b)
        
        if len(batch) >= cfg['batch_size']:
            num_written = len(batch)
            flush_batch(batch, frame_idx)
            frame_idx += num_written
    
    # Final flush
    if batch:
        # Re-calculating indices for simplicity
        files = sorted(frames_dir.glob("*.png"))
        start = len(files) + 1
        for i, f in enumerate(batch):
            graded = grade_frame(f, vignette, color_shift)
            path = frames_dir / f"frame_{start + i:06d}.png"
            cv2.imwrite(str(path), graded, [cv2.IMWRITE_PNG_COMPRESSION, cfg['png_compression']])

    # Correct frame numbering if needed
    final_files = sorted(frames_dir.glob("*.png"))
    total_frames = len(final_files)
    video_duration = total_frames / FPS

    # Deflicker
    deflicker(str(frames_dir))

    # Audio
    audio_out = output_dir / "temp_audio.wav"
    audio_path = handle_audio(video_duration, audio_out)

    # Encode
    print(f"🎬 Encoding {total_frames} frames to MP4...")
    subprocess.run([
        FFMPEG_EXE, '-y',
        '-framerate', str(FPS),
        '-i', str(frames_dir / 'frame_%06d.png'),
        '-i', str(audio_path),
        '-c:v', 'libx264',
        '-profile:v', 'high',
        '-crf', str(cfg['crf']),
        '-preset', 'slow',
        '-bf', '2',
        '-g', '48',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-ar', '48000',
        '-ac', '2',
        '-movflags', '+faststart',
        '-shortest',
        'output/final_video.mp4'
    ])
    
    print(f"\n✅ DONE! Video saved to output/final_video.mp4")
    if audio_out.exists(): os.remove(audio_out)

if __name__ == "__main__":
    main()
# okay
# okay
# okay
# okay
# okay
# okay
# okay
# okay
# okay
# okay
