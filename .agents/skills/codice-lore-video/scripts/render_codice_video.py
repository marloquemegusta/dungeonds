#!/usr/bin/env python3
"""Render a 1080x1920 vertical Códice lore video from a JSON episode config."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from PIL import Image, ImageDraw

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "tools", "video_theme"))
from theme import render_box, wrap as theme_wrap  # tema visual: ningun texto de video fuera del tema

ELEVEN_EXE = shutil.which("elevenlabs") or shutil.which("elevenlabs.exe") or "elevenlabs"


def get_duration(path: str) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        text=True,
    ).strip()
    return float(out)


def extract_frames_on_black(src_gif: str):
    im_g = Image.open(src_gif)
    frames = []
    try:
        while True:
            bg = Image.new("RGBA", im_g.size, (0, 0, 0, 255))
            fr = im_g.convert("RGBA")
            bg.alpha_composite(fr)
            rgb = bg.convert("RGB")
            px = rgb.load()
            for yy in range(rgb.height):
                for xx in range(rgb.width):
                    r, g, b = px[xx, yy]
                    if r <= 24 and g <= 24 and b <= 30:
                        px[xx, yy] = (0, 0, 0)
            frames.append(rgb)
            im_g.seek(im_g.tell() + 1)
    except EOFError:
        pass
    return frames


def save_gif(frames, dst_gif: str, duration: int = 120):
    frames[0].save(
        dst_gif,
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
    )


def fmt_ass(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def main():
    parser = argparse.ArgumentParser(description="Render Códice vertical lore video")
    parser.add_argument("--config", required=True, help="Path to episode JSON config")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    work_dir = cfg["work_dir"]
    os.makedirs(work_dir, exist_ok=True)

    voice_id = cfg.get("voice_id", "5egO01tkUjEzu7xSSE8M")
    stability = str(cfg.get("stability", 0.28))
    similarity = str(cfg.get("similarity_boost", 0.80))
    style = str(cfg.get("style", 0.60))

    # Prepare character GIF on pure black
    char_frames = extract_frames_on_black(cfg["character_gif"])
    char_blk = os.path.join(work_dir, "char_black.gif")
    save_gif(char_frames, char_blk)

    # Prepare clean DS card PNG (optional mask rectangle for removing role tag)
    clean_card_path = os.path.join(work_dir, "card_clean.png")
    im_card = Image.open(cfg["card_png"]).convert("RGB")
    mask_rect = cfg.get("card_mask_rect")
    if mask_rect:
        ImageDraw.Draw(im_card).rectangle(mask_rect, fill=(0, 0, 0))
    im_card.save(clean_card_path)

    # Prepare 2x2 mosaic GIF on pure black
    mosaic_list = [extract_frames_on_black(p) for p in cfg["mosaic_gifs"]]
    n_mos = max(len(fr) for fr in mosaic_list)
    mosaic_frames = []
    positions = [(0, 0), (160, 0), (0, 160), (160, 160)]
    for i in range(n_mos):
        canvas = Image.new("RGB", (320, 320), (0, 0, 0))
        for idx, fr_list in enumerate(mosaic_list[:4]):
            canvas.paste(fr_list[i % len(fr_list)], positions[idx])
        mosaic_frames.append(canvas)
    mosaic_blk = os.path.join(work_dir, "codice_mosaic_black.gif")
    save_gif(mosaic_frames, mosaic_blk)

    # Generate phrase-by-phrase audio at speed 1.0
    clips = []
    for p in cfg["phrases"]:
        pid = p["id"]
        mp3_path = os.path.join(work_dir, f"vo_{pid}.mp3")
        if not os.path.exists(mp3_path):
            subprocess.run(
                [
                    ELEVEN_EXE,
                    "text-to-speech",
                    "convert",
                    "--voice-id",
                    voice_id,
                    "--model-id",
                    "eleven_multilingual_v2",
                    "--voice-settings.stability",
                    stability,
                    "--voice-settings.similarity-boost",
                    similarity,
                    "--voice-settings.style",
                    style,
                    "--voice-settings.speed",
                    "1.0",
                    "--text",
                    p["text"],
                    "-o",
                    mp3_path,
                ],
                check=True,
            )
        dur = get_duration(mp3_path)
        clips.append((pid, mp3_path, dur, float(p["pause"]), p["segment"], p["subtitles"]))

    # Concatenate VO with real silence pauses and build ASS subtitles
    lead_in = 0.40
    t = lead_in
    seg_bounds = {}
    sub_events = []
    wav_list = []

    sil_lead = os.path.join(work_dir, "sil_lead.wav")
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", f"{lead_in:.3f}", sil_lead, "-loglevel", "error",
        ],
        check=True,
    )
    wav_list.append(sil_lead)

    for pid, mp3_path, dur, pause, seg, chunks in clips:
        if seg not in seg_bounds:
            seg_bounds[seg] = [t, t + dur + pause]
        else:
            seg_bounds[seg][1] = t + dur + pause

        total_chars = sum(len(c.replace("\\N", " ")) for c in chunks)
        ct = t
        for idx, c in enumerate(chunks):
            c_dur = dur * (len(c.replace("\\N", " ")) / max(1, total_chars))
            sub_events.append((ct, ct + c_dur + (0.15 if idx == len(chunks) - 1 else 0.0), c))
            ct += c_dur

        wav_path = os.path.join(work_dir, f"vo_{pid}.wav")
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", mp3_path,
                "-af", f"apad=pad_dur={pause:.3f}",
                "-ar", "44100", "-ac", "1", wav_path, "-loglevel", "error",
            ],
            check=True,
        )
        wav_list.append(wav_path)
        t += dur + pause

    total_dur = t
    seg_bounds["char_1"][0] = 0.0
    d_v1 = seg_bounds["card"][0] - 0.0
    d_v2 = seg_bounds["char_2"][0] - seg_bounds["card"][0]
    d_v3 = seg_bounds["outro"][0] - seg_bounds["char_2"][0]
    d_v4 = total_dur - seg_bounds["outro"][0]

    concat_txt = os.path.join(work_dir, "vo_concat.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for w in wav_list:
            f.write(f"file '{os.path.basename(w)}'\n")

    vo_full = os.path.join(work_dir, "vo_full.wav")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", vo_full, "-loglevel", "error"],
        check=True,
    )

    overlays = []   # (png, x, y, t0, t1)

    def box_png(name, lines, **kw):
        im = render_box(lines, **kw)
        path = os.path.abspath(os.path.join(work_dir, name))
        im.save(path)
        return path, im.size

    for k_, (st, en, txt) in enumerate(sub_events):
        pth, (bw, bh) = box_png(f"sub_{k_:03d}.png", theme_wrap(txt.replace("\\N", " ").replace("\\n", " "), 186))
        overlays.append((pth, (1080 - bw) // 2, 1145, st, en))
    hdr_png, (hw, hh) = box_png("hdr.png", [[(cfg["codice_header"], "ash")]] + theme_wrap(cfg["character_name"], 186))
    pro_png, (pw_, ph_) = box_png("pro.png", ["PRÓXIMAMENTE", [("en tu Nintendo DS", "ash")]])
    t1, t2, t3 = d_v1, d_v1 + d_v2, d_v1 + d_v2 + d_v3
    overlays.append((hdr_png, (1080 - hw) // 2, 150, 0.0, t1))
    overlays.append((hdr_png, (1080 - hw) // 2, 150, t2, t3))
    overlays.append((pro_png, (1080 - pw_) // 2, 1100, t3, total_dur))
    ov_chain, last = "", "cc"
    for k, (_, ox, oy, o0, o1) in enumerate(overlays):
        ov_chain += f"[{last}][{6 + k}:v]overlay={ox}:{oy}:enable='between(t,{o0:.3f},{o1:.3f})'[o{k}];\n"
        last = f"o{k}"

    filter_complex = f"""
[0:v]fps=30,scale=840:840:flags=neighbor,pad=1080:1920:120:400:black,
fade=t=in:st=0:d=0.5,trim=duration={d_v1:.3f},setpts=PTS-STARTPTS[v1];

[1:v]fps=30,scale=768:1152:flags=neighbor,pad=1080:1920:156:250:black,
fade=t=in:st=0:d=0.35,trim=duration={d_v2:.3f},setpts=PTS-STARTPTS[v2];

[2:v]fps=30,scale=840:840:flags=neighbor,pad=1080:1920:120:400:black,
fade=t=in:st=0:d=0.35,trim=duration={d_v3:.3f},setpts=PTS-STARTPTS[v3];

[3:v]fps=30,scale=800:800:flags=neighbor,pad=1080:1920:140:280:black,
fade=t=in:st=0:d=0.35,fade=t=out:st={max(0.1, d_v4-1.2):.3f}:d=1.2,trim=duration={d_v4:.3f},setpts=PTS-STARTPTS[v4];

[v1][v2][v3][v4]concat=n=4:v=1:a=0[cc];
{ov_chain}[{last}]format=yuv420p[vout];

[4:a]volume=1.15[vo];
[5:a]volume=0.09,afade=t=in:st=0:d=1.5,afade=t=out:st={max(0.1, total_dur-2.5):.3f}:d=2.5[bg];
[vo][bg]amix=inputs=2:duration=first:normalize=0,atrim=0:{total_dur:.3f}[aout]
"""

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-ignore_loop", "0", "-i", char_blk,
            "-loop", "1", "-i", clean_card_path,
            "-ignore_loop", "0", "-i", char_blk,
            "-ignore_loop", "0", "-i", mosaic_blk,
            "-i", vo_full,
            "-stream_loop", "-1", "-i", cfg["bgm_wav"],
            *[x for ov in overlays for x in ("-i", ov[0])],
            "-filter_complex", filter_complex,
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-t", f"{total_dur:.3f}", cfg["output_mp4"],
        ],
        check=True,
    )
    print("OK:", cfg["output_mp4"])

    # Centralize video in assets/videos/
    videos_dir = "assets/videos"
    os.makedirs(videos_dir, exist_ok=True)
    dst_central = os.path.join(videos_dir, os.path.basename(cfg["output_mp4"]))
    if os.path.abspath(cfg["output_mp4"]) != os.path.abspath(dst_central):
        shutil.copyfile(cfg["output_mp4"], dst_central)
        print("Copied to central video repository:", dst_central)


if __name__ == "__main__":
    main()
