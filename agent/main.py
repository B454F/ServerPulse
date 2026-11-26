
import threading
import queue
from tkinter import messagebox

import customtkinter as ctk

from config import (
    load_config,
    clear_config,
    DEFAULT_API_URL
)

from pairing import pair_device
from mqtt_client import MQTTService


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ServerPulseApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("ServerPulse Agent v2.0")
        self.geometry("620x720")
        self.resizable(True, True)
        self.minsize(560, 680)
        self.configure(fg_color="#0b1120")

        self.service = None
        self.config_data = None
        self.events = queue.Queue()
        self.connection_generation = 0

        self.protocol(
            "WM_DELETE_WINDOW",
            self.close_app
        )

        self.after(100, self.process_events)

        try:
            saved_config = load_config()
        except Exception:
            saved_config = None

        if saved_config:
            self.show_connected(saved_config)
        else:
            self.show_pairing()

    def reset_screen(self):
        for widget in self.winfo_children():
            widget.destroy()

    def header(self, subtitle):

        ctk.CTkLabel(
            self,
            text="SERVERPULSE",
            font=("Segoe UI", 29, "bold"),
            text_color="#38bdf8"
        ).pack(pady=(25, 3))

        ctk.CTkLabel(
            self,
            text=subtitle,
            font=("Segoe UI", 13),
            text_color="#94a3b8"
        ).pack(pady=(0, 20))

    def show_pairing(self):

        self.reset_screen()

        self.header("Cloud Infrastructure Monitoring")

        card = ctk.CTkFrame(
            self,
            fg_color="#131d2e",
            corner_radius=15
        )

        card.pack(
            padx=45,
            pady=10,
            fill="both",
            expand=True
        )

        ctk.CTkLabel(
            card,
            text="Connect your device",
            font=("Segoe UI", 23, "bold")
        ).pack(pady=(22, 5))

        ctk.CTkLabel(
            card,
            text="Link this device to your ServerPulse account.",
            text_color="#94a3b8"
        ).pack(pady=(0, 20))

        ctk.CTkLabel(
            card,
            text="Server URL"
        ).pack(anchor="w", padx=30)

        self.server_entry = ctk.CTkEntry(
            card,
            height=42
        )

        self.server_entry.insert(
            0,
            DEFAULT_API_URL
        )

        self.server_entry.pack(
            padx=30,
            pady=(5, 15),
            fill="x"
        )

        ctk.CTkLabel(
            card,
            text="Device pairing code"
        ).pack(anchor="w", padx=30)

        self.code_entry = ctk.CTkEntry(
            card,
            height=42,
            placeholder_text="SP-XXXX-XXXX-XXXX-XXXX"
        )

        self.code_entry.pack(
            padx=30,
            pady=(5, 18),
            fill="x"
        )

        self.connect_button = ctk.CTkButton(
            card,
            text="Connect Device",
            height=45,
            font=("Segoe UI", 14, "bold"),
            command=self.begin_pairing
        )

        self.connect_button.pack(
            padx=30,
            fill="x"
        )

        self.message_label = ctk.CTkLabel(
            card,
            text="",
            wraplength=450
        )

        self.message_label.pack(pady=12)

        ctk.CTkLabel(
            self,
            text="Secure MQTT over TLS",
            text_color="#64748b"
        ).pack(pady=12)

    def begin_pairing(self):

        url = self.server_entry.get().strip()
        code = self.code_entry.get().strip()

        if not url or not code:
            self.message_label.configure(
                text="Enter server URL and pairing code.",
                text_color="#f87171"
            )
            return

        self.connect_button.configure(
            state="disabled",
            text="Connecting..."
        )

        self.message_label.configure(
            text="Provisioning device...",
            text_color="#38bdf8"
        )

        def worker():
            try:
                config = pair_device(url, code)
                self.events.put(("paired", config))

            except Exception as error:
                self.events.put((
                    "pairing_error",
                    str(error)
                ))

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    def show_connected(self, config):

        self.reset_screen()

        self.config_data = config

        self.header("Device Monitoring")

        self.status_label = ctk.CTkLabel(
            self,
            text="Connecting...",
            font=("Segoe UI", 19, "bold"),
            text_color="#fbbf24"
        )

        self.status_label.pack(pady=5)

        ctk.CTkLabel(
            self,
            text=config["device_name"],
            text_color="#94a3b8"
        ).pack()

        metrics = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        metrics.pack(
            fill="x",
            padx=30,
            pady=22
        )

        self.metric_labels = {}
        self.metric_bars = {}

        for index, (name, color) in enumerate([
            ("CPU", "#38bdf8"),
            ("RAM", "#a78bfa"),
            ("Disk", "#fbbf24")
        ]):

            card = ctk.CTkFrame(
                metrics,
                fg_color="#131d2e",
                corner_radius=12
            )

            card.grid(
                row=0,
                column=index,
                padx=5,
                sticky="nsew"
            )

            metrics.grid_columnconfigure(
                index, weight=1
            )

            ctk.CTkLabel(
                card,
                text=name,
                text_color="#94a3b8"
            ).pack(pady=(15, 5))

            label = ctk.CTkLabel(
                card,
                text="--%",
                font=("Segoe UI", 27, "bold")
            )

            label.pack(pady=5)

            bar = ctk.CTkProgressBar(
                card,
                width=125,
                progress_color=color
            )

            bar.set(0)
            bar.pack(padx=12, pady=(5, 20))

            self.metric_labels[name] = label
            self.metric_bars[name] = bar

        info = ctk.CTkFrame(
            self,
            fg_color="#131d2e",
            corner_radius=12
        )

        info.pack(
            padx=35,
            fill="x"
        )

        details = [
            ("Server", config["mqtt"]["host"]),
            ("Protocol", "MQTT / TLS"),
            ("Port", str(config["mqtt"]["port"])),
            ("Interval", "5 seconds + sampling")
        ]

        for name, value in details:

            row = ctk.CTkFrame(
                info,
                fg_color="transparent"
            )

            row.pack(
                fill="x",
                padx=15,
                pady=5
            )

            ctk.CTkLabel(
                row,
                text=name,
                text_color="#94a3b8"
            ).pack(side="left")

            ctk.CTkLabel(
                row,
                text=value
            ).pack(side="right")

        self.last_update = ctk.CTkLabel(
            self,
            text="Waiting for telemetry...",
            text_color="#94a3b8"
        )

        self.last_update.pack(pady=12)

        self.connection_button = ctk.CTkButton(
            self,
            text="Disconnect",
            height=40,
            command=self.toggle_connection
        )

        self.connection_button.pack(
            fill="x",
            padx=35,
            pady=5
        )

        ctk.CTkButton(
            self,
            text="Unpair Device",
            fg_color="#991b1b",
            hover_color="#b91c1c",
            height=40,
            command=self.disconnect_device
        ).pack(
            fill="x",
            padx=35,
            pady=5
        )

        self.start_connection()

    def start_connection(self):

        self.connection_generation += 1
        generation = self.connection_generation

        self.update_status("Connecting...")

        try:
            self.service = MQTTService(
                self.config_data,
                lambda status: self.events.put(
                    ("status", (generation, status))
                ),
                lambda data: self.events.put(
                    ("telemetry", (generation, data))
                )
            )

            self.service.start()

            self.connection_button.configure(
                text="Disconnect",
                fg_color="#475569",
                hover_color="#334155"
            )

        except Exception:

            self.stop_connection()
            self.update_status("Unable to start MQTT")

    def stop_connection(self):

        self.connection_generation += 1

        if self.service:
            self.service.stop()
            self.service = None

        self.update_status("Disconnected")

        self.connection_button.configure(
            text="Connect",
            fg_color="#2563eb",
            hover_color="#1d4ed8"
        )

        self.last_update.configure(
            text="Telemetry stopped"
        )

        for name in self.metric_labels:
            self.metric_labels[name].configure(
                text="--%"
            )
            self.metric_bars[name].set(0)

    def toggle_connection(self):

        if self.service:
            self.stop_connection()
        else:
            self.start_connection()

    def process_events(self):

        try:
            while True:

                event, value = self.events.get_nowait()

                if event == "paired":
                    self.show_connected(value)

                elif event == "pairing_error":
                    self.message_label.configure(
                        text=value,
                        text_color="#f87171"
                    )

                    self.connect_button.configure(
                        state="normal",
                        text="Connect Device"
                    )

                elif event in ("status", "telemetry"):

                    generation, payload = value

                    if (
                        self.service
                        and generation == self.connection_generation
                    ):
                        if event == "status":
                            self.update_status(payload)
                        else:
                            self.update_metrics(payload)

        except queue.Empty:
            pass

        self.after(100, self.process_events)

    def update_status(self, status):

        if status == "Connected":
            color = "#34d399"
        elif status == "Disconnected":
            color = "#94a3b8"
        elif (
            "denied" in status.lower()
            or "failed" in status.lower()
            or "rejected" in status.lower()
            or "error" in status.lower()
        ):
            color = "#f87171"
        else:
            color = "#fbbf24"

        self.status_label.configure(
            text=status,
            text_color=color
        )

    def update_metrics(self, data):

        for name, key in [
            ("CPU", "cpu"),
            ("RAM", "ram"),
            ("Disk", "disk")
        ]:

            value = data[key]["usage"]

            self.metric_labels[name].configure(
                text=f"{value:.1f}%"
            )

            self.metric_bars[name].set(
                max(0, min(1, value / 100))
            )

        self.last_update.configure(
            text="Telemetry published"
        )

    def disconnect_device(self):

        confirmed = messagebox.askyesno(
            "Unpair Device",
            "Remove this device's saved local credentials?\n\n"
            "Use the web dashboard to revoke server access.",
            parent=self
        )

        if not confirmed:
            return

        self.stop_connection()

        try:
            clear_config()
        except Exception as error:
            messagebox.showerror(
                "Unpair failed",
                str(error),
                parent=self
            )
            return

        self.config_data = None
        self.show_pairing()

    def close_app(self):

        if self.service:
            self.service.stop()

        self.destroy()


if __name__ == "__main__":
    app = ServerPulseApp()
    app.mainloop()
