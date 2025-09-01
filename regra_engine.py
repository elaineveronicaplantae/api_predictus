from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
import json
from pathlib import Path

@dataclass
class ResultadoRegra:
    inclui: bool
    motivo: str

def normaliza(s: str) -> str:
    return (s or "").strip().lower()

def valor_num(v: Any) -> float:
    try:
        return float(str(v).replace(".", "").replace(",", "."))
    except Exception:
        try:
            return float(v)
        except Exception:
            return 0.0

def carrega_config(path: str | Path) -> Dict[str, Any]:
    # --- LINHA CORRIGIDA ---
    # Alterado de "utf-8" para "utf-8-sig" para ignorar o caractere BOM
    with open(path, encoding="utf-8-sig") as f:
        cfg = json.load(f)
    
    cfg["_status_exclusao_norm"] = {normaliza(x) for x in cfg["status_exclusao"]}
    return cfg

def avalia(reg: Dict[str, Any], cfg: Dict[str, Any]) -> ResultadoRegra:
    # --- ETAPA 1: REGRAS DE EXCLUSÃO ---
    status = normaliza(reg.get("Status", ""))
    if status in cfg["_status_exclusao_norm"]:
        return ResultadoRegra(False, "Excluído por status")

    # --- ETAPA 2: REGRAS DE INCLUSÃO ---
    valor_causa = valor_num(reg.get("Valor da Causa"))

    for regra in cfg["regras_inclusao"]:
        todas_condicoes_satisfeitas = True
        
        for campo, condicao in regra["condicoes"].items():
            valor_processo = reg.get(campo)
            
            if isinstance(condicao, list):
                if normaliza(valor_processo) not in {normaliza(c) for c in condicao}:
                    todas_condicoes_satisfeitas = False
                    break
            
            elif isinstance(condicao, dict) and "min" in condicao:
                if valor_causa < float(condicao["min"]):
                    todas_condicoes_satisfeitas = False
                    break
        
        if todas_condicoes_satisfeitas:
            return ResultadoRegra(True, regra["motivo"])

    return ResultadoRegra(False, "Não atende às regras de inclusão")
