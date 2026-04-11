"""
================================================================================
SCRIPT DE TELEMETRIA PARA DIAGNÓSTICO ESTEQUIOMÉTRICO - SCANNER OBD2 ELM 327 BLUETOOTH
================================================================================
Objetivo: Extrair dados brutos da injeção eletrônica (ECU) para diagnosticar 
falhas de hardware (bomba de combustível, bicos, entradas de ar falso) observando 
o comportamento da Malha Fechada (Closed Loop) e os ajustes de combustível (Fuel Trims).

Arquitetura: Síncrona forçada com proteção contra suspensão do sistema operacional 
e gravação atômica em disco para evitar perda de dados em falhas de energia ou vibração.
(Pois, perdi alguns dados por causa disso.)
================================================================================
"""

import obd
import csv
import time
import datetime
import os
import ctypes

# ------------------------------------------------------------------------------
# 1. MATRIZ DE DADOS (OS SENSORES DA VERDADE)
# ------------------------------------------------------------------------------
# Não solicitamos sensores aleatórios para não saturar a banda do Bluetooth.
# Isolamos estritamente as variáveis da equação de queima de combustível:
PIDS_ALVO = [
    obd.commands.RPM,               # Rotação: Define o ritmo do motor.
    obd.commands.ENGINE_LOAD,       # Carga do Motor: Mostra o quanto o motor está se esforçando (vácuo no coletor).
    obd.commands.THROTTLE_POS,      # Posição da Borboleta: Intenção de aceleração do motorista.
    obd.commands.MAF,               # Fluxo de Massa de Ar: A quantidade física de ar entrando (gramas/segundo).
    obd.commands.INTAKE_TEMP,       # Temperatura do Ar: Ar frio é mais denso, exigindo mais combustível.
    obd.commands.O2_B1S1,           # Sonda Lambda (Pré-Catalisador): A prova real da queima. Alterna entre rica (>0.45v) e pobre (<0.45v).
    obd.commands.SHORT_FUEL_TRIM_1, # STFT (Correção Imediata): A reação da ECU em tempo real para corrigir a sonda lambda (-25% a +25%).
    obd.commands.LONG_FUEL_TRIM_1,  # LTFT (Correção Histórica): A adaptação de longo prazo da ECU. Valores travados acima de +10% ou abaixo de -10% indicam falha mecânica crônica.
    obd.commands.TIMING_ADVANCE     # Avanço de Ignição: O ponto da faísca, afeta o torque e reage a batidas de pino (detonação).
]

# ------------------------------------------------------------------------------
# 2. CONTROLE DA CAMADA FÍSICA (API DO WINDOWS)
# ------------------------------------------------------------------------------
# Meu notebook desligava a tela e portas USB para poupar energia.
# No meio de um teste de rua, isso derrubava o adaptador Bluetooth e o script.
# Usamos a biblioteca 'ctypes' para conversar direto com o Kernel do Windows.
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

def bloquear_suspensao_windows():
    """Trava o gerenciamento de energia. O Windows é proibido de apagar a tela ou dormir."""
    if os.name == 'nt': # Verifica se o sistema operacional é Windows (NT)
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED
        )
        print("-> Regra de energia alterada: A tela do notebook e o sistema ficarão acordados.")

def restaurar_suspensao_windows():
    """Devolve o controle de energia ao padrão do Windows após o teste."""
    if os.name == 'nt':
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        print("-> Regra de energia restaurada ao padrão do sistema.")

# ------------------------------------------------------------------------------
# 3. MOTOR DE AQUISIÇÃO DE DADOS
# ------------------------------------------------------------------------------
def iniciar_telemetria(porta="COM5"):
    # Passo 1: Imuniza o PC contra desligamento de tela/portas USB
    bloquear_suspensao_windows()
    
    print(f"Estabelecendo conexão OBD2 na porta {porta}...")
    
    # Passo 2: Conexão. Usamos fast=False para garantir estabilidade máxima com 
    # adaptadores ELM327 podres, evitando que eles engasguem com excesso das requisições.
    connection = obd.OBD(porta, baudrate=38400, fast=False)
    
    if not connection.is_connected():
        print("Falha severa: Não foi possível conectar à ECU. Verifique o pareamento Bluetooth e a ignição.")
        restaurar_suspensao_windows() # Libera a tela se falhar
        return

    print("Conexão estabelecida. Iniciando gravação à prova de falhas.")
    
    # Gera um nome de arquivo único baseado na data e hora exatas do teste
    nome_arquivo = f"telemetria_mistura_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    cabecalhos = ["TIMESTAMP"] + [cmd.name for cmd in PIDS_ALVO]
    
    # Passo 3: Abertura do arquivo em modo contínuo (append/write).
    # newline='' evita que o Windows crie linhas em branco desnecessárias no CSV.
    with open(nome_arquivo, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(cabecalhos)
        file.flush() # Empurra o cabeçalho para o disco rígido imediatamente
        
        try:
            # O Loop Infinito: Só para se o usuário abortar (usem o CTRL+C para parar o script) ou houver erro
            while True:
                # Marca o tempo exato (com precisão de milissegundos) do início da varredura
                linha_atual = [datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]]
                
                # Varre a lista de sensores solicitando os dados um por um à centralina (ECU)
                for cmd in PIDS_ALVO:
                    resposta = connection.query(cmd)
                    if not resposta.is_null():
                        # Extrai apenas o número para o CSV, descartando a unidade (ex: tira o "RPM" e deixa só "850")
                        linha_atual.append(resposta.value.magnitude)
                    else:
                        # Se o carro não suportar o sensor ou ele estiver desligado, marca como NaN (Not a Number/Nada)
                        linha_atual.append("NaN")
                
                # Escreve a linha completa (snapshot daquele instante) no buffer da memória
                writer.writerow(linha_atual)
                
                # Passo 4: A BARREIRA CONTRA PERDA DE DADOS
                # O Python normalmente guarda os dados na RAM e grava no disco aos poucos para ser mais rápido.
                # No carro, se o scanner soltar ou o PC desligar, o que está na RAM é perdido.
                # Estes dois comandos abaixo obrigam o HD/SSD a gravar os dados a cada volta do loop.
                file.flush()
                os.fsync(file.fileno())
                
                # Imprime um resumo no console para o motorista saber que o sistema está vivo
                print(f"Log gravado: {linha_atual[0]} | RPM: {linha_atual[1]} | STFT: {linha_atual[7]} | LTFT: {linha_atual[8]}")
                
        # Tratamento de exceções para garantir que o script sempre feche de forma limpa
        except KeyboardInterrupt:
            # Ocorre quando o usuário aperta Ctrl+C no terminal
            print("\nTelemetria interrompida intencionalmente pelo usuário.")
        except Exception as e:
            # Ocorre se houver um crash lógico ou quebra na porta serial
            print(f"\nErro crítico no loop de varredura: {e}")
        finally:
            # Passo 5: O Encerramento. Este bloco executa sempre, independentemente de sucesso ou falha.
            connection.close()
            restaurar_suspensao_windows() # Devolve o poder de desligar a tela ao Windows
            print(f"Conexão encerrada. Dados seguros no arquivo: {nome_arquivo}")

# Ponto de entrada do script
if __name__ == "__main__":
    # IMPORTANTE: Altere "COM5" para a porta Bluetooth de SAÍDA configurada no seu Windows
    # (Procure no seu windows as configurações de bluethooh e veja a Porta COM de saída do seu scanner.)
    iniciar_telemetria("COM5")