# Datalogger OBD2: Script para Diagnóstico Estequiométrico usando SCANNER OBD2 ELM 327 BLUETOOTH

Este repositório contém script Python focado em extrair telemetria bruta e ininterrupta da injeção eletrônica via protocolo OBD2 usando um **SCANNER OBD2 ELM 327 BLUETOOTH** daqueles bem barato e podre, solução para quem é **LISO**. 

Ao contrário de aplicativos de painel visual, esta ferramenta foi arquitetada especificamente para registrar os valores dos sensores e ajudar nos diagnósticos de problema nas peças de injeção (falhas em bombas de combustível, bicos injetores entupidos ou entradas de ar falso), monitorando o comportamento da Malha Fechada (Closed Loop) e os ajustes de combustível (Short e Long Term Fuel Trims).

## O Problema que Resolvemos
Aplicativos e scripts de telemetria comuns falham no ambiente automotivo devido a dois gargalos:
1. **Perda de Pacotes por Suspensão:** O sistema operacional do notebook frequentemente entra em modo de economia de energia, desligando portas USB/Bluetooth e quebrando a comunicação serial no meio de um teste de rua.
2. **Perda de Dados em Crash:** Em caso de desconexão bruta (cabo solto, trepidação ou falha de software), os dados retidos na memória RAM são perdidos antes de serem gravados no disco.
3. **Falta de software acessível e confiável:** Nunca achei nenhum aplicativo que leia o **SCANNER OBD2 ELM 327 BLUETOOTH** de forma satisfatória e registre em um arquivo para análise de dados posterior.

## Arquitetura e Solução
* **Prevenção de Suspensão (API do Windows):** Integração com a biblioteca `ctypes` para invocar o `SetThreadExecutionState` do Kernel do Windows, travando o gerenciamento de energia. O notebook não apaga a tela e não desliga o rádio Bluetooth enquanto o motor estiver sendo monitorado.
* **I/O Flush Atômico:** Gravação síncrona com `os.fsync()`. Cada linha de log (snapshot de milissegundos) é forçada fisicamente para o disco rígido assim que é lida. Se houver falha de energia, os dados até a fração de segundo anterior estão salvos no CSV.
* **Seleção Estrita de PIDs:** O script requisita apenas as variáveis que compõem a equação de queima estequiométrica, evitando saturar a banda do adaptador ELM327 ruim com PIDs inúteis.

## Pré-requisitos
* Adaptador OBD2 (ELM327 Bluetooth).
* Python 3.8+ instalado.
* Sistema Operacional: Windows (devido à dependência da API `ctypes.windll`, mas se você fizer um port para Linux me avisa que eu quero também).

**Instalação das dependências:**
```bash
pip install obd
```

# Como Utilizar
1. Pareie o seu adaptador ELM327 com o notebook via Bluetooth.
2. Descubra qual é a porta COM de Saída (Outgoing/Saída) que o Windows gerou para ele acessando: Configurações > Bluetooth e Dispositivos > Mais opções de Bluetooth > Portas COM.
3. Abra o arquivo do script no seu editor de código e altere a variável na última linha para bater com a sua porta (ex: mude para "COM6").
4. Vá para o carro, vire a chave (apenas ignição ou motor ligado) e rode o script no terminal:
```bash
python datalogger_mistura.py
```
