# PL Lab — Laboratório de Programação Linear

Aplicativo interativo do projeto de Pesquisa Operacional. Interface em português no navegador, servidor e solver em Python, sem dependências externas.

## Executar

Requer **Python 3.10 ou superior** e um navegador moderno.

```bash
python app.py
```

Abra **<http://127.0.0.1:8501>**. Para escolher outra porta: `python app.py --port 8502`. Encerre com Ctrl+C. O servidor aceita conexões apenas do próprio computador.

## Servidor

A versão publicada está em **<https://lp-lab.duckdns.org>**. O servidor Ubuntu roda o app como serviço systemd e o Nginx encaminha as requisições HTTPS. O certificado TLS é emitido pelo Let's Encrypt e renovado pelo Certbot.

Para consultar o serviço no servidor:

```bash
ssh ubuntu@lp-lab.duckdns.org 'sudo systemctl status lp-lab'
ssh ubuntu@lp-lab.duckdns.org 'sudo journalctl -u lp-lab -f'
```

O endereço usa DuckDNS. Se o IP público do servidor mudar, atualize o registro `lp-lab` no painel DuckDNS para apontar ao novo IP e confira a conectividade HTTPS.

## Deploy automático pelo GitHub

O workflow `.github/workflows/deploy.yml` roda os testes em cada `push` para `main`. Depois que a configuração do SSH estiver pronta e o deploy habilitado, ele envia o app ao servidor, reinicia `lp-lab.service` e verifica a resposta da aplicação. Alterações em outras branches não publicam o site.

### Configuração inicial

1. Gere uma chave exclusiva para o deploy no seu computador:

   ```bash
   ssh-keygen -t ed25519 -C "github-actions-lp-lab" -f ~/.ssh/lp-lab-actions -N ""
   ```

2. Instale **apenas a chave pública** no usuário de deploy do servidor:

   ```bash
   cat ~/.ssh/lp-lab-actions.pub | ssh ubuntu@lp-lab.duckdns.org 'sudo tee -a /home/lpdeploy/.ssh/authorized_keys >/dev/null && sudo chown lpdeploy:lpdeploy /home/lpdeploy/.ssh/authorized_keys && sudo chmod 600 /home/lpdeploy/.ssh/authorized_keys'
   ```

3. No GitHub, abra **Settings → Secrets and variables → Actions** do repositório. Crie o secret `DEPLOY_SSH_KEY` com o conteúdo de `~/.ssh/lp-lab-actions` (a chave privada). Nunca coloque essa chave no código, em um commit ou nesta conversa.

4. Na aba **Variables**, crie `DEPLOY_ENABLED` com o valor `true`. O deploy fica desabilitado até esse passo.

Depois, valide com um commit pequeno e faça `git push origin main`. Veja o resultado em **Actions** no GitHub. Se os testes falharem, o deploy não é executado. O host SSH está definido no workflow e sua chave pública verificada fica em `.github/deploy_known_hosts`.

O workflow usa `actions/checkout` v7.0.1, fixado em um commit verificado, e permite ler o conteúdo do repositório. O deploy autentica pelo usuário restrito `lpdeploy`; a chave pública do servidor está fixada em `.github/deploy_known_hosts`, e a chave privada fica armazenada como secret do GitHub Actions.

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
