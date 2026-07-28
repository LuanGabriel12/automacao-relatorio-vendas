from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd
from openpyxl import load_workbook

from src.relatorio_vendas import (
    calcular_kpis,
    converter_numero_brasileiro,
    criar_analises,
    executar_pipeline,
    limpar_vendas,
)


class TestRelatorioVendas(unittest.TestCase):
    def test_conversao_de_numero_brasileiro(self):
        self.assertEqual(converter_numero_brasileiro("R$ 1.234,56"), 1234.56)
        self.assertEqual(converter_numero_brasileiro("89,90"), 89.90)
        self.assertEqual(converter_numero_brasileiro("1200.50"), 1200.50)

    def test_limpeza_e_calculo_do_faturamento(self):
        dados = pd.DataFrame(
            [
                {
                    "data": "01/01/2026",
                    "pedido": "P-1",
                    "loja": "Centro",
                    "produto": "Notebook",
                    "categoria": "Informática",
                    "quantidade": "2",
                    "preco_unitario": "3.000,00",
                    "arquivo_origem": "teste.csv",
                },
                {
                    "data": "02/01/2026",
                    "pedido": "P-2",
                    "loja": "Online",
                    "produto": "Mouse",
                    "categoria": "Acessórios",
                    "quantidade": "0",
                    "preco_unitario": "100,00",
                    "arquivo_origem": "teste.csv",
                },
                {
                    "data": "01/01/2026",
                    "pedido": "P-1",
                    "loja": "Centro",
                    "produto": "Notebook",
                    "categoria": "Informática",
                    "quantidade": "2",
                    "preco_unitario": "3.000,00",
                    "arquivo_origem": "copia.csv",
                },
            ]
        )

        vendas, inconsistencias, duplicados = limpar_vendas(dados)

        self.assertEqual(len(vendas), 1)
        self.assertEqual(len(inconsistencias), 2)
        self.assertEqual(duplicados, 1)
        self.assertEqual(vendas.iloc[0]["faturamento"], 6000.00)

    def test_ordenacao_da_analise_por_loja(self):
        vendas = pd.DataFrame(
            [
                {
                    "loja": "Centro",
                    "produto": "A",
                    "categoria": "X",
                    "pedido": "1",
                    "quantidade": 1,
                    "faturamento": 100.0,
                    "mes": "2026-01",
                },
                {
                    "loja": "Online",
                    "produto": "B",
                    "categoria": "Y",
                    "pedido": "2",
                    "quantidade": 2,
                    "faturamento": 500.0,
                    "mes": "2026-01",
                },
            ]
        )

        analises = criar_analises(vendas)
        kpis = calcular_kpis(vendas, pd.DataFrame())

        self.assertEqual(analises["por_loja"].iloc[0]["loja"], "Online")
        self.assertEqual(kpis["faturamento_total"], 600.0)
        self.assertEqual(kpis["pedidos_unicos"], 2)

    def test_criacao_do_arquivo_excel(self):
        with TemporaryDirectory() as pasta_temporaria:
            raiz = Path(pasta_temporaria)
            entrada = raiz / "entrada"
            entrada.mkdir()
            saida = raiz / "relatorio.xlsx"
            log = raiz / "execucao.log"

            pd.DataFrame(
                [
                    {
                        "Data": "01/01/2026",
                        "Pedido": "P-1",
                        "Loja": "Centro",
                        "Produto": "Notebook",
                        "Categoria": "Informática",
                        "Quantidade": "1",
                        "Preço Unitário": "3000,00",
                    },
                    {
                        "Data": "01/02/2026",
                        "Pedido": "P-2",
                        "Loja": "Online",
                        "Produto": "Mouse",
                        "Categoria": "Acessórios",
                        "Quantidade": "2",
                        "Preço Unitário": "100,00",
                    },
                ]
            ).to_csv(entrada / "vendas.csv", sep=";", index=False)

            resultado = executar_pipeline(entrada, saida, log)
            workbook = load_workbook(saida)

            self.assertTrue(saida.exists())
            self.assertEqual(resultado["registros_validos"], 2)
            self.assertEqual(
                workbook.sheetnames,
                [
                    "Resumo",
                    "Vendas_Limpas",
                    "Por_Loja",
                    "Por_Produto",
                    "Por_Categoria",
                    "Por_Mes",
                    "Inconsistencias",
                ],
            )
            self.assertEqual(len(workbook["Resumo"]._charts), 2)


if __name__ == "__main__":
    unittest.main()
