import asyncio
import aiohttp
import time
import random
import threading
import tkinter as tk
from collections import deque
import matplotlib.pyplot as plt
import csv

# uvloop opcional
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except:
    pass

TARGET_HTTP = "http://185.245.180.79"

CONCURRENCY = 50
SIMULATED_LATENCY = (0.05, 0.2)

metrics = {
    "requests": 0,
    "errors": 0,
    "rtt": [],
    "online": True
}

rps_history = deque(maxlen=120)
rtt_history = deque(maxlen=120)
err_history = deque(maxlen=120)

lock = asyncio.Lock()

# ---------------- HTTP WORKER ----------------

async def http_worker(session):

    while True:

        await asyncio.sleep(random.uniform(*SIMULATED_LATENCY))
        start = time.time()

        try:

            async with session.get(TARGET_HTTP) as resp:
                await resp.text()

            rtt = time.time() - start

            async with lock:
                metrics["requests"] += 1
                metrics["rtt"].append(rtt)
                metrics["online"] = True

        except:

            async with lock:
                metrics["errors"] += 1
                metrics["online"] = False


# ---------------- METRICS ----------------

async def metrics_loop():

    last_requests = 0

    while True:

        await asyncio.sleep(1)

        async with lock:

            total = metrics["requests"]
            errors = metrics["errors"]

            rps = total - last_requests
            last_requests = total

            if metrics["rtt"]:
                avg_rtt = sum(metrics["rtt"]) / len(metrics["rtt"])
                metrics["rtt"].clear()
            else:
                avg_rtt = 0

            online = metrics["online"]

        rps_history.append(rps)
        rtt_history.append(avg_rtt)
        err_history.append(errors)

        print(f"STATUS={'ONLINE' if online else 'DOWN'} | RPS={rps} | RTT={avg_rtt:.3f}")


# ---------------- DASHBOARD ----------------

def dashboard():

    plt.ion()
    fig, ax = plt.subplots()

    while True:

        ax.clear()

        ax.plot(list(rps_history), label="RPS")
        ax.plot(list(rtt_history), label="RTT")
        ax.plot(list(err_history), label="Errors")

        ax.set_title("NOC Performance Monitor")
        ax.legend()

        plt.pause(1)


# ---------------- GUI ----------------

class NOC_GUI:

    def __init__(self, root):

        self.root = root

        root.title("Network Operations Monitor")

        self.status = tk.Label(root, text="ONLINE", bg="green", fg="white",
                               font=("Arial", 16), width=20)

        self.status.pack(pady=10)

        self.info = tk.Label(root, text="", font=("Consolas", 11), justify="left")
        self.info.pack()

        self.export = tk.Button(root, text="Export Report", command=self.export_report)
        self.export.pack(pady=10)

        self.last_requests = 0

        self.update_ui()


    def export_report(self):

        with open("load_test_report.csv", "w", newline="") as f:

            writer = csv.writer(f)

            writer.writerow(["RPS", "RTT", "Errors"])

            for i in range(len(rps_history)):
                writer.writerow([rps_history[i], rtt_history[i], err_history[i]])

        print("Relatório exportado")


    def update_ui(self):

        total = metrics["requests"]
        errors = metrics["errors"]

        rps = total - self.last_requests
        self.last_requests = total

        avg_rtt = 0
        if metrics["rtt"]:
            avg_rtt = sum(metrics["rtt"]) / len(metrics["rtt"])

        if metrics["online"]:
            self.status.config(text="ONLINE", bg="green")
        else:
            self.status.config(text="SERVICE DOWN", bg="red")
            self.root.bell()   # alerta sonoro

        text = f"""
Target: {TARGET_HTTP}

Requests/sec: {rps}
Total Requests: {total}
Errors: {errors}
Avg RTT: {round(avg_rtt,3)} s
"""

        self.info.config(text=text)

        self.root.after(1000, self.update_ui)


# ---------------- MAIN ----------------

async def main():

    connector = aiohttp.TCPConnector(limit=CONCURRENCY)

    async with aiohttp.ClientSession(connector=connector) as session:

        tasks = []

        for _ in range(CONCURRENCY):
            tasks.append(asyncio.create_task(http_worker(session)))

        tasks.append(asyncio.create_task(metrics_loop()))

        await asyncio.gather(*tasks)


# ---------------- RUN ----------------

if __name__ == "__main__":

    threading.Thread(target=dashboard, daemon=True).start()

    threading.Thread(target=lambda: asyncio.run(main()), daemon=True).start()

    root = tk.Tk()
    app = NOC_GUI(root)
    root.mainloop()