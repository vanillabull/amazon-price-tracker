"""
Amazon Price Tracker 
pip install customtkinter requests beautifulsoup4 resend
"""

import resend
import requests
import threading
import time
from datetime import datetime
from bs4 import BeautifulSoup
import customtkinter as ctk

resend.api_key = "PASTE_YOUR_API_KEY_HERE" # <---- Im using resend api, get an API key and paste it here

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


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
    except Exception as e:
        return None


class PriceTrackerApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Price Tracker")
        self.geometry("680x720")
        self.resizable(False, False)
        self.configure(fg_color="#0f0f14")

        self._tracking      = False
        self._thread        = None
        self._last_price    = None
        self._check_count   = 0

        self._build_ui()


    def _build_ui(self):

        header = ctk.CTkFrame(self, fg_color="#0f0f14", corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(
            header,
            text="◈  PRICE TRACKER",
            font=ctk.CTkFont(family="Courier New", size=22, weight="bold"),
            text_color="#00e5ff",
        ).pack(pady=(28, 2))

        ctk.CTkLabel(
            header,
            text="Amazon price monitor with email alerts",
            font=ctk.CTkFont(size=12),
            text_color="#505070",
        ).pack(pady=(0, 20))

        ctk.CTkFrame(self, height=1, fg_color="#1e1e2e").pack(fill="x", padx=24)

        card = ctk.CTkFrame(self, fg_color="#13131a", corner_radius=14)
        card.pack(fill="x", padx=24, pady=20)

        ctk.CTkLabel(
            card, text="YOUR EMAIL",
            font=ctk.CTkFont(family="Courier New", size=10, weight="bold"),
            text_color="#505070",
        ).pack(anchor="w", padx=20, pady=(18, 4))

        self.email_entry = ctk.CTkEntry(
            card,
            placeholder_text="you@example.com",
            height=42,
            fg_color="#0a0a0f",
            border_color="#1e1e2e",
            border_width=1,
            text_color="#e0e0f0",
            font=ctk.CTkFont(size=13),
        )
        self.email_entry.pack(fill="x", padx=20)

        ctk.CTkLabel(
            card, text="AMAZON PRODUCT URL",
            font=ctk.CTkFont(family="Courier New", size=10, weight="bold"),
            text_color="#505070",
        ).pack(anchor="w", padx=20, pady=(14, 4))

        self.url_entry = ctk.CTkEntry(
            card,
            placeholder_text="https://www.amazon.com/dp/...",
            height=42,
            fg_color="#0a0a0f",
            border_color="#1e1e2e",
            border_width=1,
            text_color="#e0e0f0",
            font=ctk.CTkFont(size=13),
        )
        self.url_entry.pack(fill="x", padx=20)

        ctk.CTkLabel(
            card, text="CHECK INTERVAL (seconds)",
            font=ctk.CTkFont(family="Courier New", size=10, weight="bold"),
            text_color="#505070",
        ).pack(anchor="w", padx=20, pady=(14, 4))

        self.interval_slider = ctk.CTkSlider(
            card,
            from_=30, to=3600,
            number_of_steps=71,
            button_color="#00e5ff",
            button_hover_color="#00b8cc",
            progress_color="#00e5ff",
            fg_color="#1e1e2e",
        )
        self.interval_slider.set(60)
        self.interval_slider.pack(fill="x", padx=20)
        self.interval_slider.configure(command=self._update_interval_label)

        self.interval_label = ctk.CTkLabel(
            card, text="60 seconds",
            font=ctk.CTkFont(family="Courier New", size=11),
            text_color="#00e5ff",
        )
        self.interval_label.pack(anchor="e", padx=24, pady=(2, 18))

        self.start_btn = ctk.CTkButton(
            self,
            text="▶  START TRACKING",
            height=48,
            font=ctk.CTkFont(family="Courier New", size=14, weight="bold"),
            fg_color="#00e5ff",
            hover_color="#00b8cc",
            text_color="#0a0a0f",
            corner_radius=10,
            command=self._toggle_tracking,
        )
        self.start_btn.pack(fill="x", padx=24, pady=(0, 16))

        price_card = ctk.CTkFrame(self, fg_color="#13131a", corner_radius=14)
        price_card.pack(fill="x", padx=24, pady=(0, 16))
        price_card.columnconfigure((0, 1, 2), weight=1)

        self._stat_block(price_card, "CURRENT PRICE", 0).pack(side="left", expand=True, padx=8, pady=16)
        self.current_price_label = ctk.CTkLabel(
            price_card,
            text="—",
            font=ctk.CTkFont(family="Courier New", size=32, weight="bold"),
            text_color="#ffffff",
        )

        col_left   = ctk.CTkFrame(price_card, fg_color="transparent")
        col_mid    = ctk.CTkFrame(price_card, fg_color="transparent")
        col_right  = ctk.CTkFrame(price_card, fg_color="transparent")
        col_left.pack(side="left", expand=True, pady=16)
        col_mid.pack(side="left", expand=True, pady=16)
        col_right.pack(side="left", expand=True, pady=16)

        ctk.CTkLabel(col_left, text="CURRENT PRICE",
                     font=ctk.CTkFont(family="Courier New", size=9, weight="bold"),
                     text_color="#505070").pack()
        self.lbl_current = ctk.CTkLabel(col_left, text="—",
                                        font=ctk.CTkFont(family="Courier New", size=26, weight="bold"),
                                        text_color="#ffffff")
        self.lbl_current.pack()

        ctk.CTkLabel(col_mid, text="STARTING PRICE",
                     font=ctk.CTkFont(family="Courier New", size=9, weight="bold"),
                     text_color="#505070").pack()
        self.lbl_start = ctk.CTkLabel(col_mid, text="—",
                                      font=ctk.CTkFont(family="Courier New", size=26, weight="bold"),
                                      text_color="#7070a0")
        self.lbl_start.pack()

        ctk.CTkLabel(col_right, text="CHECKS DONE",
                     font=ctk.CTkFont(family="Courier New", size=9, weight="bold"),
                     text_color="#505070").pack()
        self.lbl_checks = ctk.CTkLabel(col_right, text="0",
                                       font=ctk.CTkFont(family="Courier New", size=26, weight="bold"),
                                       text_color="#7070a0")
        self.lbl_checks.pack()
        self.status_frame = ctk.CTkFrame(self, fg_color="#13131a", corner_radius=10)
        self.status_frame.pack(fill="x", padx=24, pady=(0, 16))

        self.status_dot = ctk.CTkLabel(
            self.status_frame, text="●",
            font=ctk.CTkFont(size=13),
            text_color="#303050",
        )
        self.status_dot.pack(side="left", padx=(16, 6), pady=12)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Idle — enter details above and press Start",
            font=ctk.CTkFont(family="Courier New", size=12),
            text_color="#505070",
        )
        self.status_label.pack(side="left", pady=12)
        ctk.CTkLabel(
            self, text="EVENT LOG",
            font=ctk.CTkFont(family="Courier New", size=10, weight="bold"),
            text_color="#505070",
        ).pack(anchor="w", padx=28, pady=(0, 6))

        self.log_box = ctk.CTkTextbox(
            self,
            height=190,
            fg_color="#0a0a0f",
            border_color="#1e1e2e",
            border_width=1,
            font=ctk.CTkFont(family="Courier New", size=12),
            text_color="#7070a0",
            corner_radius=10,
        )
        self.log_box.pack(fill="x", padx=24, pady=(0, 24))
        self.log_box.configure(state="disabled")

    def _stat_block(self, parent, label, col):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(frame, text=label,
                     font=ctk.CTkFont(family="Courier New", size=9, weight="bold"),
                     text_color="#505070").pack()
        return frame


    def _update_interval_label(self, val):
        v = int(val)
        self.interval_label.configure(text=f"{v} second{'s' if v != 1 else ''}")

    def _log(self, message: str, color: str = "#7070a0"):
        ts  = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}]  {message}\n"
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_status(self, text: str, color: str = "#505070"):
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
            self._set_status("⚠  Enter a valid email address.", "#ff6b35")
            return
        if not url.startswith("http"):
            self._set_status("⚠  Enter a valid Amazon URL.", "#ff6b35")
            return

        self._tracking    = True
        self._check_count = 0
        self.start_btn.configure(
            text="■  STOP TRACKING",
            fg_color="#1e1e2e",
            hover_color="#2a2a3a",
            text_color="#ff6b35",
        )
        self._set_status("Fetching initial price…", "#00e5ff")
        self._log("Tracker started.")
        self._log(f"URL: {url[:60]}{'…' if len(url) > 60 else ''}")
        self._log(f"Sending alerts to: {email}")

        self._thread = threading.Thread(
            target=self._tracking_loop,
            args=(url, email),
            daemon=True,
        )
        self._thread.start()

    def _stop_tracking(self):
        self._tracking = False
        self.start_btn.configure(
            text="▶  START TRACKING",
            fg_color="#00e5ff",
            hover_color="#00b8cc",
            text_color="#0a0a0f",
        )
        self._set_status("Stopped.", "#505070")
        self._log("Tracker stopped.")

    def _tracking_loop(self, url: str, email: str):
        # Fetch initial price
        price = grab_price(url)
        if price is None:
            self.after(0, lambda: self._set_status("✗  Couldn't fetch price. Check the URL.", "#ff6b35"))
            self.after(0, lambda: self._log("ERROR: Could not fetch price from URL."))
            self.after(0, self._stop_tracking)
            return

        self._last_price = price
        self.after(0, lambda: self._update_price_display(price, price, "start"))
        self.after(0, lambda: self._log(f"Starting price: ${price:.2f}"))
        self.after(0, lambda: self._set_status(f"Watching — last check just now", "#00e5ff"))

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
                self.after(0, lambda: self._log("WARNING: Failed to fetch price, retrying..."))
                continue

            last = self._last_price

            if current < last:
                change = last - current
                self.after(0, lambda c=current, l=last, ch=change: self._on_drop(c, l, ch, url, email))
            elif current > last:
                change = current - last
                self.after(0, lambda c=current, l=last, ch=change: self._on_rise(c, l, ch, url, email))
            else:
                self.after(0, lambda c=current, n=count: (
                    self._log(f"Check #{n}: Price unchanged at ${c:.2f}"),
                    self._set_status(f"Watching — check #{n} complete", "#00e5ff"),
                    self._update_price_display(c, self._last_price, "same"),
                ))

            self._last_price = current

    def _on_drop(self, current, last, change, url, email):
        self._last_price = current
        self._update_price_display(current, last, "drop")
        self._log(f"Price drop: ${last:.2f} → ${current:.2f}  (saved ${change:.2f})")
        self._set_status(f"Price dropped ${change:.2f}! Email sent.", "#22c55e")
        threading.Thread(target=send_email, args=(
            f"Price Dropped to ${current:.2f}!",
            f"""
            <div style="font-family:sans-serif;max-width:480px;margin:auto">
              <h2 style="color:#16a34a;margin-bottom:4px">💰 Price Drop!</h2>
              <p style="color:#555;font-size:14px">Good news — the price went down.</p>
              <table style="width:100%;font-size:15px;border-collapse:collapse;margin:16px 0">
                <tr style="border-bottom:1px solid #eee">
                  <td style="padding:8px 0;color:#888">Was</td>
                  <td style="padding:8px 0;text-align:right"><s>${last:.2f}</s></td>
                </tr>
                <tr style="border-bottom:1px solid #eee">
                  <td style="padding:8px 0;font-weight:bold">Now</td>
                  <td style="padding:8px 0;text-align:right;font-weight:bold;color:#16a34a">${current:.2f}</td>
                </tr>
                <tr>
                  <td style="padding:8px 0;color:#16a34a">You save</td>
                  <td style="padding:8px 0;text-align:right;color:#16a34a">${change:.2f}</td>
                </tr>
              </table>
              <a href="{url}" style="display:inline-block;background:#16a34a;color:#fff;padding:12px 24px;
                 text-decoration:none;border-radius:6px;font-weight:bold">Buy Now →</a>
            </div>
            """,
            email,
        ), daemon=True).start()

    def _on_rise(self, current, last, change, url, email):
        self._last_price = current
        self._update_price_display(current, last, "rise")
        self._log(f"Price rise:  ${last:.2f} → ${current:.2f}  (+${change:.2f})")
        self._set_status(f"Price rose ${change:.2f}. Email sent.", "#ff6b35")
        threading.Thread(target=send_email, args=(
            f"Price Increased to ${current:.2f}",
            f"""
            <div style="font-family:sans-serif;max-width:480px;margin:auto">
              <h2 style="color:#dc2626;margin-bottom:4px">📈 Price Increase</h2>
              <p style="color:#555;font-size:14px">The price went up since last check.</p>
              <table style="width:100%;font-size:15px;border-collapse:collapse;margin:16px 0">
                <tr style="border-bottom:1px solid #eee">
                  <td style="padding:8px 0;color:#888">Was</td>
                  <td style="padding:8px 0;text-align:right">${last:.2f}</td>
                </tr>
                <tr>
                  <td style="padding:8px 0;font-weight:bold">Now</td>
                  <td style="padding:8px 0;text-align:right;font-weight:bold;color:#dc2626">${current:.2f}</td>
                </tr>
              </table>
              <a href="{url}" style="display:inline-block;background:#2563eb;color:#fff;padding:12px 24px;
                 text-decoration:none;border-radius:6px;font-weight:bold">View Product →</a>
            </div>
            """,
            email,
        ), daemon=True).start()

    def _update_price_display(self, current: float, start: float, state: str):
        colors = {"drop": "#22c55e", "rise": "#ff6b35", "same": "#ffffff", "start": "#ffffff"}
        self.lbl_current.configure(text=f"${current:.2f}", text_color=colors.get(state, "#fff"))
        self.lbl_start.configure(text=f"${start:.2f}")
        self.lbl_checks.configure(text=str(self._check_count))


if __name__ == "__main__":
    app = PriceTrackerApp()
    app.iconbitmap("favicon.ico")
    app.mainloop()
