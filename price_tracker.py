"""
Amazon Price Tracker 
pip install customtkinter requests beautifulsoup4 resend
"""

import resend
import requests
import threading
import time
import math
import random
from datetime import datetime
from bs4 import BeautifulSoup
import customtkinter as ctk
import tkinter as tk

resend.api_key = ""

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG_DEEP      = "#080e1a" 
BG_MID       = "#0d1628" 
FROST_1      = "#111e35"  
FROST_2      = "#162440" 
BORDER       = "#1e3356"  
ACCENT_ICE   = "#a8d8f0" 
ACCENT_SNOW  = "#deeeff" 
ACCENT_GLOW  = "#4da6d6"   
GREEN_FROST  = "#5ddba5"   
ORANGE_EMBER = "#f09060"   
TEXT_PRIMARY = "#deeeff"   
TEXT_MUTED   = "#4a6a8a"  
TEXT_DIM     = "#2a4a6a"   


def send_email(subject: str, body: str, to: str) -> None:
    try:
        resend.Emails.send({
            "from":    "onboarding@resend.dev",
            "to":      to,
            "subject": subject,
            "html":    body,
        })
    except Exception as e:
        print("Email error:", e)


def grab_price(url: str) -> float | None:
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        whole    = soup.find("span", class_="a-price-whole")
        fraction = soup.find("span", class_="a-price-fraction")

        if whole and fraction:
            price_str    = whole.get_text().strip().replace(",", "").replace(".", "")
            fraction_str = fraction.get_text().strip()
            return float(f"{price_str}.{fraction_str}")

        offscreen = soup.find("span", class_="a-offscreen")
        if offscreen:
            text = offscreen.get_text().strip().replace("$", "").replace(",", "")
            return float(text)

        return None
    except Exception:
        return None


class SnowCanvas(tk.Canvas):
    """Animated snowflakes drawn on a tkinter Canvas."""

    FLAKE_CHARS = ["·", "•", "❄", "❅", "❆", "✦", "*"]

    def __init__(self, master, width, height, **kwargs):
        super().__init__(
            master,
            width=width, height=height,
            bg=BG_DEEP,
            highlightthickness=0,
            **kwargs,
        )
        self.w = width
        self.h = height
        self._flakes = []
        self._running = True
        self._init_flakes(55)
        self._animate()

    def _init_flakes(self, n: int):
        for _ in range(n):
            self._flakes.append(self._new_flake(random.randint(0, self.h)))

    def _new_flake(self, y=None):
        size  = random.choice([7, 8, 9, 10, 11, 13])
        speed = random.uniform(0.3, 1.1)
        drift = random.uniform(-0.3, 0.3)
        char  = random.choice(self.FLAKE_CHARS)
        alpha_level = random.choice(["#1a2e44", "#1e3450", "#243d5a", "#1a2840", "#152030"])
        return {
            "x": random.uniform(0, self.w),
            "y": random.uniform(0, self.h) if y is None else y,
            "speed": speed,
            "drift": drift,
            "char": char,
            "size": size,
            "color": alpha_level,
            "id": None,
            "wobble": random.uniform(0, math.pi * 2),
        }

    def _animate(self):
        if not self._running:
            return
        self.delete("flake")
        for f in self._flakes:
            f["wobble"] += 0.03
            f["x"] += f["drift"] + math.sin(f["wobble"]) * 0.4
            f["y"] += f["speed"]
            if f["y"] > self.h + 20:
                f["x"] = random.uniform(0, self.w)
                f["y"] = -10
                f["color"] = random.choice(["#1a2e44", "#1e3450", "#243d5a", "#1a2840", "#152030"])
                f["speed"] = random.uniform(0.3, 1.1)
            self.create_text(
                f["x"], f["y"],
                text=f["char"],
                font=("Helvetica", f["size"]),
                fill=f["color"],
                tags="flake",
            )
        self.after(40, self._animate)

    def stop(self):
        self._running = False


class FrostEntry(ctk.CTkEntry):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            height=44,
            fg_color=FROST_2,
            border_color=BORDER,
            border_width=1,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_DIM,
            font=ctk.CTkFont(family="Consolas", size=13),
            corner_radius=10,
            **kwargs,
        )


class PriceTrackerApp(ctk.CTk):

    WIN_W = 660
    WIN_H = 780

    def __init__(self):
        super().__init__()

        self.title("❄  Price Tracker")
        self.geometry(f"{self.WIN_W}x{self.WIN_H}")
        self.resizable(False, False)
        self.configure(fg_color=BG_DEEP)

        self._tracking    = False
        self._thread      = None
        self._last_price  = None
        self._check_count = 0
        self._start_price = None

        self._build_ui()


    def _build_ui(self):
        self.snow = SnowCanvas(self, self.WIN_W, self.WIN_H)
        self.snow.place(x=0, y=0)

        overlay = ctk.CTkFrame(self, fg_color="transparent")
        overlay.place(x=0, y=0, relwidth=1, relheight=1)

        ctk.CTkLabel(
            overlay,
            text="❄",
            font=ctk.CTkFont(size=36),
            text_color=ACCENT_ICE,
        ).pack(pady=(32, 0))

        ctk.CTkLabel(
            overlay,
            text="PRICE TRACKER",
            font=ctk.CTkFont(family="Consolas", size=24, weight="bold"),
            text_color=ACCENT_SNOW,
        ).pack(pady=(4, 2))

        ctk.CTkLabel(
            overlay,
            text="Amazon price monitor  ·  email alerts",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=TEXT_MUTED,
        ).pack(pady=(0, 22))

        ctk.CTkFrame(overlay, height=1, fg_color=BORDER).pack(fill="x", padx=36, pady=(0, 20))

        card = ctk.CTkFrame(overlay, fg_color=FROST_1, corner_radius=16,
                            border_width=1, border_color=BORDER)
        card.pack(fill="x", padx=28, pady=(0, 16))

        self._field_label(card, "❄  YOUR EMAIL")
        self.email_entry = FrostEntry(card, placeholder_text="you@example.com")
        self.email_entry.pack(fill="x", padx=18, pady=(0, 14))

        self._field_label(card, "❄  AMAZON PRODUCT URL")
        self.url_entry = FrostEntry(card, placeholder_text="https://www.amazon.com/dp/...")
        self.url_entry.pack(fill="x", padx=18, pady=(0, 14))

        self._field_label(card, "❄  CHECK INTERVAL")
        slider_row = ctk.CTkFrame(card, fg_color="transparent")
        slider_row.pack(fill="x", padx=18, pady=(0, 18))

        self.interval_slider = ctk.CTkSlider(
            slider_row,
            from_=30, to=3600,
            number_of_steps=71,
            button_color=ACCENT_GLOW,
            button_hover_color=ACCENT_ICE,
            progress_color=ACCENT_GLOW,
            fg_color=FROST_2,
            width=440,
        )
        self.interval_slider.set(60)
        self.interval_slider.pack(side="left", expand=True, fill="x")
        self.interval_slider.configure(command=self._update_interval_label)

        self.interval_lbl = ctk.CTkLabel(
            slider_row,
            text="60s",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=ACCENT_ICE,
            width=52,
        )
        self.interval_lbl.pack(side="right")

        self.start_btn = ctk.CTkButton(
            overlay,
            text="▶   START TRACKING",
            height=52,
            font=ctk.CTkFont(family="Consolas", size=15, weight="bold"),
            fg_color=ACCENT_GLOW,
            hover_color=ACCENT_ICE,
            text_color=BG_DEEP,
            corner_radius=12,
            command=self._toggle_tracking,
        )
        self.start_btn.pack(fill="x", padx=28, pady=(0, 16))

        stats = ctk.CTkFrame(overlay, fg_color=FROST_1, corner_radius=14,
                             border_width=1, border_color=BORDER)
        stats.pack(fill="x", padx=28, pady=(0, 14))

        col_l = ctk.CTkFrame(stats, fg_color="transparent")
        col_m = ctk.CTkFrame(stats, fg_color="transparent")
        col_r = ctk.CTkFrame(stats, fg_color="transparent")
        col_l.pack(side="left", expand=True, pady=16)
        col_m.pack(side="left", expand=True, pady=16)
        col_r.pack(side="left", expand=True, pady=16)

        ctk.CTkFrame(stats, width=1, fg_color=BORDER).pack(side="left", fill="y", pady=12)

        for w in stats.winfo_children():
            w.pack_forget()

        col_l.pack(side="left", expand=True, pady=16)
        ctk.CTkFrame(stats, width=1, fg_color=BORDER).pack(side="left", fill="y", pady=10)
        col_m.pack(side="left", expand=True, pady=16)
        ctk.CTkFrame(stats, width=1, fg_color=BORDER).pack(side="left", fill="y", pady=10)
        col_r.pack(side="left", expand=True, pady=16)

        self.lbl_current = self._stat_col(col_l,  "CURRENT",  "—")
        self.lbl_start   = self._stat_col(col_m,  "STARTED",  "—")
        self.lbl_checks  = self._stat_col(col_r,  "CHECKS",   "0")

        status_bar = ctk.CTkFrame(overlay, fg_color=FROST_1, corner_radius=10,
                                  border_width=1, border_color=BORDER)
        status_bar.pack(fill="x", padx=28, pady=(0, 14))

        self.status_dot = ctk.CTkLabel(
            status_bar, text="●",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_DIM,
        )
        self.status_dot.pack(side="left", padx=(14, 6), pady=11)

        self.status_label = ctk.CTkLabel(
            status_bar,
            text="Idle  —  enter your details and press Start",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=TEXT_MUTED,
        )
        self.status_label.pack(side="left", pady=11)

        log_header = ctk.CTkFrame(overlay, fg_color="transparent")
        log_header.pack(fill="x", padx=28, pady=(0, 6))

        ctk.CTkLabel(
            log_header,
            text="EVENT LOG",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=TEXT_DIM,
        ).pack(side="left")

        self.log_box = ctk.CTkTextbox(
            overlay,
            height=164,
            fg_color=FROST_1,
            border_color=BORDER,
            border_width=1,
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=TEXT_MUTED,
            corner_radius=12,
            scrollbar_button_color=FROST_2,
            scrollbar_button_hover_color=BORDER,
        )
        self.log_box.pack(fill="x", padx=28, pady=(0, 24))
        self.log_box.configure(state="disabled")


    def _field_label(self, parent, text: str):
        ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=18, pady=(14, 5))

    def _stat_col(self, parent, label: str, initial: str):
        ctk.CTkLabel(
            parent,
            text=label,
            font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
            text_color=TEXT_DIM,
        ).pack()
        lbl = ctk.CTkLabel(
            parent,
            text=initial,
            font=ctk.CTkFont(family="Consolas", size=24, weight="bold"),
            text_color=TEXT_PRIMARY,
        )
        lbl.pack()
        return lbl


    def _update_interval_label(self, val):
        v = int(val)
        self.interval_lbl.configure(text=f"{v}s")

    def _log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{ts}]  {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_status(self, text: str, color: str = TEXT_MUTED):
        self.status_label.configure(text=text, text_color=color)
        self.status_dot.configure(text_color=color)

    def _toggle_tracking(self):
        if not self._tracking:
            self._start_tracking()
        else:
            self._stop_tracking()

    def _start_tracking(self):
        email = self.email_entry.get().strip()
        url   = self.url_entry.get().strip()

        if not email or "@" not in email:
            self._set_status("⚠  Enter a valid email address.", ORANGE_EMBER)
            return
        if not url.startswith("http"):
            self._set_status("⚠  Enter a valid Amazon URL.", ORANGE_EMBER)
            return

        self._tracking    = True
        self._check_count = 0
        self.start_btn.configure(
            text="■   STOP TRACKING",
            fg_color=FROST_2,
            hover_color=BORDER,
            text_color=ORANGE_EMBER,
        )
        self._set_status("Fetching initial price…", ACCENT_ICE)
        self._log("— Tracker started —")
        self._log(f"URL  : {url[:55]}{'…' if len(url)>55 else ''}")
        self._log(f"Alert: {email}")

        self._thread = threading.Thread(
            target=self._tracking_loop,
            args=(url, email),
            daemon=True,
        )
        self._thread.start()

    def _stop_tracking(self):
        self._tracking = False
        self.start_btn.configure(
            text="▶   START TRACKING",
            fg_color=ACCENT_GLOW,
            hover_color=ACCENT_ICE,
            text_color=BG_DEEP,
        )
        self._set_status("Stopped.", TEXT_MUTED)
        self._log("— Tracker stopped —")


    def _tracking_loop(self, url: str, email: str):
        price = grab_price(url)
        if price is None:
            self.after(0, lambda: self._set_status("✗  Couldn't fetch price. Check the URL.", ORANGE_EMBER))
            self.after(0, lambda: self._log("ERROR: Could not fetch price."))
            self.after(0, self._stop_tracking)
            return

        self._last_price  = price
        self._start_price = price
        self.after(0, lambda p=price: (
            self._update_display(p, p, "start"),
            self._log(f"Starting price: ${p:.2f}"),
            self._set_status(f"Watching  ·  press Stop to quit", ACCENT_ICE),
        ))

        while self._tracking:
            interval = int(self.interval_slider.get())
            for _ in range(interval * 10):
                if not self._tracking:
                    return
                time.sleep(0.1)

            current = grab_price(url)
            self._check_count += 1
            count = self._check_count

            if current is None:
                self.after(0, lambda: self._log("WARNING: Failed to fetch — retrying next cycle"))
                continue

            last = self._last_price

            if current < last:
                change = last - current
                self.after(0, lambda c=current, l=last, ch=change: self._on_drop(c, l, ch, url, email))
            elif current > last:
                change = current - last
                self.after(0, lambda c=current, l=last, ch=change: self._on_rise(c, l, ch, url, email))
            else:
                sp = self._start_price
                self.after(0, lambda c=current, n=count, s=sp: (
                    self._log(f"Check #{n}  ·  ${c:.2f}  ·  no change"),
                    self._set_status(f"Watching  ·  check #{n} complete", ACCENT_ICE),
                    self._update_display(c, s, "same"),
                ))

            self._last_price = current


    def _on_drop(self, current, last, change, url, email):
        self._last_price = current
        self._update_display(current, self._start_price, "drop")
        self._log(f"Drop  ${last:.2f} → ${current:.2f}  (−${change:.2f})  · email sent")
        self._set_status(f"Price dropped ${change:.2f}!  Email sent.", GREEN_FROST)
        threading.Thread(target=send_email, args=(
            f"Price Dropped to ${current:.2f}!",
            f"""
            <div style="font-family:'Segoe UI',sans-serif;max-width:500px;margin:auto;
                        background:#0d1628;color:#deeeff;border-radius:12px;padding:32px">
              <div style="font-size:32px;margin-bottom:8px">❄ 💰</div>
              <h2 style="color:#5ddba5;margin:0 0 6px">Price Drop Detected</h2>
              <p style="color:#4a6a8a;font-size:14px;margin:0 0 24px">
                Good news — the price went down.
              </p>
              <table style="width:100%;font-size:15px;border-collapse:collapse">
                <tr style="border-bottom:1px solid #1e3356">
                  <td style="padding:10px 0;color:#4a6a8a">Was</td>
                  <td style="padding:10px 0;text-align:right;color:#4a6a8a"><s>${last:.2f}</s></td>
                </tr>
                <tr style="border-bottom:1px solid #1e3356">
                  <td style="padding:10px 0;font-weight:bold">Now</td>
                  <td style="padding:10px 0;text-align:right;font-weight:bold;
                             color:#5ddba5;font-size:20px">${current:.2f}</td>
                </tr>
                <tr>
                  <td style="padding:10px 0;color:#5ddba5">You save</td>
                  <td style="padding:10px 0;text-align:right;color:#5ddba5">${change:.2f}</td>
                </tr>
              </table>
              <a href="{url}" style="display:inline-block;margin-top:24px;
                 background:#5ddba5;color:#080e1a;padding:13px 28px;
                 text-decoration:none;border-radius:8px;font-weight:bold;font-size:15px">
                Buy Now →
              </a>
            </div>
            """,
            email,
        ), daemon=True).start()

    def _on_rise(self, current, last, change, url, email):
        self._last_price = current
        self._update_display(current, self._start_price, "rise")
        self._log(f"Rise  ${last:.2f} → ${current:.2f}  (+${change:.2f})  · email sent")
        self._set_status(f"📈  Price rose ${change:.2f}.  Email sent.", ORANGE_EMBER)
        threading.Thread(target=send_email, args=(
            f"Price Increased to ${current:.2f}",
            f"""
            <div style="font-family:'Segoe UI',sans-serif;max-width:500px;margin:auto;
                        background:#0d1628;color:#deeeff;border-radius:12px;padding:32px">
              <div style="font-size:32px;margin-bottom:8px">❄ 📈</div>
              <h2 style="color:#f09060;margin:0 0 6px">Price Increase Detected</h2>
              <p style="color:#4a6a8a;font-size:14px;margin:0 0 24px">
                The price went up since your last check.
              </p>
              <table style="width:100%;font-size:15px;border-collapse:collapse">
                <tr style="border-bottom:1px solid #1e3356">
                  <td style="padding:10px 0;color:#4a6a8a">Was</td>
                  <td style="padding:10px 0;text-align:right;color:#4a6a8a">${last:.2f}</td>
                </tr>
                <tr>
                  <td style="padding:10px 0;font-weight:bold">Now</td>
                  <td style="padding:10px 0;text-align:right;font-weight:bold;
                             color:#f09060;font-size:20px">${current:.2f}</td>
                </tr>
              </table>
              <a href="{url}" style="display:inline-block;margin-top:24px;
                 background:#4da6d6;color:#080e1a;padding:13px 28px;
                 text-decoration:none;border-radius:8px;font-weight:bold;font-size:15px">
                View Product →
              </a>
            </div>
            """,
            email,
        ), daemon=True).start()

    def _update_display(self, current: float, start: float, state: str):
        color_map = {
            "drop":  GREEN_FROST,
            "rise":  ORANGE_EMBER,
            "same":  TEXT_PRIMARY,
            "start": ACCENT_ICE,
        }
        self.lbl_current.configure(
            text=f"${current:.2f}",
            text_color=color_map.get(state, TEXT_PRIMARY),
        )
        if start is not None:
            self.lbl_start.configure(text=f"${start:.2f}", text_color=TEXT_MUTED)
        self.lbl_checks.configure(text=str(self._check_count), text_color=TEXT_MUTED)


    def on_close(self):
        self._tracking = False
        self.snow.stop()
        self.destroy()


if __name__ == "__main__":
    app = PriceTrackerApp()
    try:
        app.iconbitmap("favicon.ico")
    except Exception:
        pass
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
