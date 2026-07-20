"""Generate the public, sanitized Codex Coordinator demo GIFs.

The frames are composed deterministically so product copy stays exact and no
private project names, task messages, or identifiers enter the public assets.
Requires Pillow only at asset-generation time; the shipped plugin is unchanged.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site" / "assets" / "demos"
LOGO = ROOT / "plugins" / "codex-coordinator" / "assets" / "logo.png"
SIZE = (960, 600)

NAVY = "#07152D"
NAVY_2 = "#0B1D3B"
PANEL = "#102647"
PANEL_2 = "#162E53"
LINE = "#284468"
PAPER = "#F4F8FF"
MUTED = "#AFC0D8"
CYAN = "#6FE1DC"
PURPLE = "#9A7BFF"
GREEN = "#70E0AE"
YELLOW = "#FFD477"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)


F12 = font(12, True)
F14 = font(14)
F14B = font(14, True)
F16 = font(16)
F16B = font(16, True)
F18 = font(18)
F18B = font(18, True)
F22B = font(22, True)
F28B = font(28, True)


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, outline: str = LINE, radius: int = 12) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=1)


def text_lines(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, *, chars: int, fill: str = PAPER, face: ImageFont.FreeTypeFont = F16, gap: int = 6) -> int:
    x, y = xy
    lines: list[str] = []
    for paragraph in text.split("\n"):
        lines.extend(wrap(paragraph, width=chars) or [""])
    line_height = face.size + gap
    for line in lines:
        draw.text((x, y), line, font=face, fill=fill)
        y += line_height
    return y


def base(title: str, active: str = "Coordinator") -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", SIZE, NAVY)
    draw = ImageDraw.Draw(image)
    # A quiet grid gives the demo the same visual language as the public site.
    for x in range(0, SIZE[0], 40):
        draw.line((x, 0, x, SIZE[1]), fill="#0B1C38", width=1)
    for y in range(0, SIZE[1], 40):
        draw.line((0, y, SIZE[0], y), fill="#0B1C38", width=1)

    draw.rectangle((0, 0, 960, 52), fill="#061126")
    draw.ellipse((18, 19, 28, 29), fill="#FF7B72")
    draw.ellipse((34, 19, 44, 29), fill=YELLOW)
    draw.ellipse((50, 19, 60, 29), fill=GREEN)
    draw.text((78, 15), "Codex", font=F16B, fill=PAPER)
    draw.text((823, 17), "SANITIZED DEMO", font=F12, fill=CYAN)

    draw.rectangle((0, 52, 230, 600), fill="#081831")
    logo = Image.open(LOGO).convert("RGBA")
    logo.thumbnail((34, 34), Image.Resampling.LANCZOS)
    image.paste(logo, (20, 72), logo)
    draw.text((64, 77), "Codex Coordinator", font=F16B, fill=PAPER)
    draw.text((20, 128), "YOUR TASKS", font=F12, fill="#7890AE")
    items = ["Coordinator", "Task A · App", "Task B · Docs", "Task C · Check"]
    for index, item in enumerate(items):
        y = 157 + index * 54
        if item.startswith(active):
            rounded(draw, (12, y, 218, y + 42), PANEL_2, "#4C668C", 8)
            draw.rectangle((12, y + 9, 15, y + 33), fill=CYAN)
        draw.text((28, y + 11), item, font=F14B if item.startswith(active) else F14, fill=PAPER if item.startswith(active) else MUTED)

    draw.line((230, 52, 230, 600), fill=LINE, width=1)
    draw.text((260, 73), title, font=F22B, fill=PAPER)
    draw.text((260, 106), "The lead Codex task keeps the work together", font=F14, fill=MUTED)
    draw.line((260, 136, 930, 136), fill=LINE, width=1)
    return image, draw


def bubble(draw: ImageDraw.ImageDraw, top: int, label: str, copy: str, *, user: bool = False, height: int = 118) -> None:
    left, right = (410, 930) if user else (260, 890)
    fill = "#19355E" if user else PANEL
    outline = "#41638C" if user else LINE
    rounded(draw, (left, top, right, top + height), fill, outline, 12)
    draw.text((left + 20, top + 15), label.upper(), font=F12, fill=CYAN if not user else PURPLE)
    text_lines(draw, (left + 20, top + 42), copy, chars=56 if not user else 44, face=F16, fill=PAPER)


def task_chip(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, detail: str, status: str, color: str) -> None:
    rounded(draw, (x, y, x + 198, y + 88), PANEL_2, LINE, 10)
    draw.ellipse((x + 15, y + 16, x + 25, y + 26), fill=color)
    draw.text((x + 34, y + 12), label, font=F14B, fill=PAPER)
    draw.text((x + 15, y + 40), detail, font=F14, fill=MUTED)
    draw.text((x + 15, y + 64), status.upper(), font=F12, fill=color)


def save_gif(name: str, frames: list[Image.Image], durations: list[int]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUT / name,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )


def demo_ask() -> None:
    frames: list[Image.Image] = []
    for step in range(6):
        image, draw = base("1 · Ask for the outcome")
        bubble(draw, 160, "You", "Get this release ready. Fix the app, update the docs, and check everything before we ship.", user=True, height=116)
        if step >= 1:
            bubble(draw, 298, "Coordinator", "I’ll run this from one place. I’m splitting the work into three focused Codex tasks.", height=104)
        chips = [
            ("Task A", "Fix the app", "Starting", CYAN),
            ("Task B", "Update the docs", "Starting", PURPLE),
            ("Task C", "Check the work", "Starting", YELLOW),
        ]
        for index, chip in enumerate(chips):
            if step >= index + 2:
                task_chip(draw, 260 + index * 217, 432, *chip)
        frames.append(image)
    save_gif("01-ask-and-split.gif", frames, [900, 1150, 700, 700, 1500, 2200])


def worker_panel(draw: ImageDraw.ImageDraw, x: int, y: int, title: str, job: str, status: str, update: str, color: str) -> None:
    rounded(draw, (x, y, x + 205, y + 310), PANEL, LINE, 12)
    draw.ellipse((x + 18, y + 20, x + 30, y + 32), fill=color)
    draw.text((x + 40, y + 16), title, font=F16B, fill=PAPER)
    draw.text((x + 18, y + 54), job, font=F18B, fill=PAPER)
    draw.line((x + 18, y + 91, x + 187, y + 91), fill=LINE, width=1)
    draw.text((x + 18, y + 111), status.upper(), font=F12, fill=color)
    text_lines(draw, (x + 18, y + 145), update, chars=22, face=F14, fill=MUTED, gap=7)


def demo_work() -> None:
    states = [
        ("Working", "Opening the app and running its checks.", "Queued", "Waiting for its turn.", "Queued", "Waiting for the finished work."),
        ("Working", "Fixing the release issue and checking the change.", "Working", "Making the setup guide easier to follow.", "Queued", "Waiting for the finished work."),
        ("Done", "Fix complete. The focused app checks pass.", "Working", "Updating the README and website instructions.", "Working", "Reviewing the app and docs together."),
        ("Done", "Fix complete. The focused app checks pass.", "Done", "README and website now match the release.", "Working", "Running the final independent check."),
        ("Done", "Fix complete. The focused app checks pass.", "Done", "README and website now match the release.", "Done", "No blocking issue found. Ready to report."),
    ]
    frames: list[Image.Image] = []
    for state in states:
        image, draw = base("2 · Focused tasks do the work")
        draw.text((260, 158), "Coordinator keeps each task on a different part", font=F18B, fill=PAPER)
        worker_panel(draw, 260, 202, "Task A", "Fix the app", state[0], state[1], GREEN if state[0] == "Done" else CYAN)
        worker_panel(draw, 480, 202, "Task B", "Update docs", state[2], state[3], GREEN if state[2] == "Done" else PURPLE)
        worker_panel(draw, 700, 202, "Task C", "Check it", state[4], state[5], GREEN if state[4] == "Done" else YELLOW)
        draw.text((260, 535), "You do not have to open each task or carry updates between them.", font=F14B, fill=CYAN)
        frames.append(image)
    save_gif("02-tasks-at-work.gif", frames, [1300, 1300, 1400, 1400, 2600])


def checklist(draw: ImageDraw.ImageDraw, y: int, copy: str, color: str = GREEN) -> None:
    draw.ellipse((278, y + 3, 294, y + 19), fill=color)
    draw.text((282, y + 1), "✓", font=F12, fill=NAVY)
    draw.text((309, y), copy, font=F16, fill=PAPER)


def demo_result() -> None:
    frames: list[Image.Image] = []
    updates = [
        ("Task A is finished",),
        ("Task A is finished", "Task B is finished"),
        ("Task A is finished", "Task B is finished", "Task C checked the combined work"),
    ]
    for step in range(5):
        image, draw = base("3 · Get one checked answer")
        if step < 3:
            bubble(draw, 160, "Coordinator", "The task updates are coming back here. I’m checking them before I give you the result.", height=104)
            for index, copy in enumerate(updates[step]):
                checklist(draw, 298 + index * 43, copy)
        else:
            rounded(draw, (260, 158, 920, 508), PANEL, "#3D6B77", 14)
            draw.text((284, 181), "COORDINATOR · FINAL UPDATE", font=F12, fill=CYAN)
            draw.text((284, 216), "Release-ready work is complete", font=F28B, fill=PAPER)
            checklist(draw, 278, "The app fix is complete and its checks pass")
            checklist(draw, 322, "The README and website match the release")
            checklist(draw, 366, "The combined work received an independent check")
            draw.line((284, 414, 896, 414), fill=LINE, width=1)
            draw.text((284, 438), "You have one result to review—not three chats to combine.", font=F16B, fill=CYAN)
            if step == 4:
                rounded(draw, (714, 527, 920, 568), CYAN, CYAN, 8)
                draw.text((746, 538), "READY FOR YOU", font=F14B, fill=NAVY)
        frames.append(image)
    save_gif("03-one-result.gif", frames, [1100, 1100, 1800, 1800, 2600])


if __name__ == "__main__":
    demo_ask()
    demo_work()
    demo_result()
    for path in sorted(OUT.glob("*.gif")):
        print(f"{path.relative_to(ROOT)}\t{path.stat().st_size} bytes")
