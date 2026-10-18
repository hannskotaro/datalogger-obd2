# Datalogger OBD2 — Diagnóstico Estequiométrico via ELM327 Bluetooth

Script em Python para extração contínua de telemetria bruta da injeção eletrônica (ECU) via protocolo OBD2 utilizando interfaces Bluetooth ELM327 de baixo custo.

Ao contrário de aplicativos focados apenas em painéis visuais em tempo real, esta ferramenta foi desenhada para gravação contínua de sensores e diagnóstico de falhas mecânicas no sistema de injeção (queda de pressão na bomba de combustível, bicos injetores obstruídos ou entradas falsas de ar), monitorando o comportamento da Malha Fechada (*Closed Loop*) e os ajustes de combustível (*Short Term* e *Long Term Fuel Trims*).

## Problemas Resolvidos

Coletas de telemetria em testes de rua costumam falhar por três motivos:
1. **Queda de conexão por suspensão do sistema:** O gerenciamento de energia do notebook desliga portas seriais/Bluetooth ao apagar a tela, interrompendo a leitura no meio do percurso.
2. **Perda de buffer em desconexões abruptas:** Em caso de perda de sinal Bluetooth, trepidação ou desligamento da ignição, os dados retidos em memória RAM são perdidos antes da gravação no arquivo.
3. **Saturação de banda em interfaces ELM327:** Adaptadores Bluetooth genéricos possuem alta latência e baixa taxa de transferência quando consultados com dezenas de parâmetros simultâneos.

## Arquitetura da Solução

* **Bloqueio de Suspensão (Windows Kernel API):** Uso de `ctypes` para invocar `SetThreadExecutionState` no kernel do Windows, impedindo que o sistema suspenda a sessão ou desligue o rádio Bluetooth durante a captura.
* **Gravação Síncrona (`os.fsync`):** Cada leitura recebida da ECU é descarregada imediatamente do buffer do sistema operacional para o disco em formato CSV, garantindo que nenhuma amostra anterior seja perdida em caso de queda de conexão.
* **Filtragem Estrita de PIDs:** Consulta restrita às variáveis necessárias para análise da mistura ar/combustível, maximizando a taxa de amostragem (*polling rate*) em interfaces ELM327 Bluetooth.

## Pré-requisitos

* Adaptador OBD2 compatível com ELM327 (Bluetooth).
* Python 3.8+.
* Windows (devido à chamada direta a `ctypes.windll.kernel32`).

```bash
pip install obd
```

## Como Utilizar

1. Pareie o adaptador ELM327 com o notebook via Bluetooth.
2. Identifique a porta COM de saída (*Outgoing*) atribuída pelo Windows em: **Configurações > Bluetooth e Dispositivos > Mais opções de Bluetooth > Portas COM**.
3. Ajuste a variável da porta serial no final do arquivo `datalogger-obd2.py` (ex.: `"COM6"`).
4. Com a ignição ligada ou o motor em funcionamento, execute:

```bash
python datalogger-obd2.py
```
