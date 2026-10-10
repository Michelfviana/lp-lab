# PL Lab — Laboratório de Programação Linear

Aplicativo interativo do projeto de Pesquisa Operacional. Interface em português no navegador, servidor e solver em Python, sem dependências externas.

## Executar

Requer **Python 3.10 ou superior** e um navegador moderno.

```bash
python app.py
```

Abra **<http://127.0.0.1:8501>**. Para escolher outra porta: `python app.py --port 8502`. Encerre com Ctrl+C. O servidor aceita conexões apenas do próprio computador.

## Recursos

- Maximização e minimização, de 2 a 8 variáveis contínuas não negativas.
- Até 20 restrições com `<=`, `>=` e `=`. Coeficientes inteiros, decimais (ponto ou vírgula) e frações.
- Simplex de duas fases implementado no projeto, com aritmética racional exata e regra de Bland para evitar ciclos.
- Normalização de lados direitos negativos, variáveis de folga, excesso e artificiais; remoção de equações redundantes.
- Navegação pelos tableaux, destaque de coluna e linha pivô, teste da menor razão e opção de exibir frações ou decimais.
- Gráfico de duas variáveis com região viável, vértices, ponto ótimo, reta objetivo móvel, zoom, arraste e legenda interativa.
- Certificação de ótimo, inviabilidade e objetivo ilimitado; direção de melhoria no caso ilimitado.
- Análise das restrições ativas, folgas/excessos, identificação de degeneração e detecção de soluções alternativas quando há uma direção com passo positivo no tableau final.
- Exemplos de produção, minimização, inviabilidade, objetivo ilimitado, ótimos alternativos e três variáveis.
- Importação/exportação de modelos JSON, exportação da análise e tableaux CSV, relatório imprimível e histórico local dos seis últimos modelos resolvidos.

O exemplo do DOCX é `Max Z = 3x₁ + 5x₂`, sujeito a `x₁ <= 4`, `2x₂ <= 12`, `3x₁ + 2x₂ <= 18`. A solução é **x₁ = 2, x₂ = 6, Z = 36**.

## Modelo JSON

```json
{
  "sense": "max",
  "objective": [3, 5],
  "constraints": [
    {"coefficients": [1, 0], "operator": "<=", "rhs": 4},
    {"coefficients": [0, 2], "operator": "<=", "rhs": 12},
    {"coefficients": [3, 2], "operator": "<=", "rhs": 18}
  ]
}
```

Use strings para frações, como `"3/2"`. Modelos ficam no navegador por meio de `localStorage`; nenhum serviço externo recebe os dados. A análise permanece vinculada ao modelo resolvido e um aviso aparece quando você edita a entrada.

## Organização

- `app.py`: servidor HTTP e endpoint `POST /api/solve`.
- `solver.py`: validação, Simplex e vértices viáveis em duas dimensões.
- `static/`: interface, estilos e gráfico Canvas.
- `tests/test_solver.py`: casos matemáticos e de validação.

Execute os testes com `python -m unittest discover -s tests -v`.

## Limites

O aplicativo resolve PL contínua com todas as variáveis não negativas. Não resolve programação inteira, variáveis livres ou funções não lineares. Há um limite de 500 pivôs por fase. Os coeficientes aceitam magnitude e denominador de até 1 bilhão. A região no gráfico é recortada pela janela visível, que não indica que o conjunto viável seja limitado. A detecção de ótimos alternativos pelo tableau final pode não identificar alternativas que exigem pivôs degenerados prévios. A impressão inclui o tableau atualmente selecionado; a exportação CSV inclui todos.
