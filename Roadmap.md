# Roadmap do Produto: AI-SDLC Compass (até 30 de novembro)

> **Nota:** Rascunho para validação.  
> **Datas fixas:** 23 Out (Avaliação Peer 1) | 30 Nov (Avaliação Peer 2 e Entregas Finais) | 2 a 5 Dez (Apresentações).  
> Prioridades e requisitos alinhados com os Requisitos e Use Cases.

---

## 1. Visão Geral por Fases

| Fase | Período | Objetivo | Resultado no Fim |
| :--- | :--- | :--- | :--- |
| **F0: Fundação** | 5 a 16 Out | Definir o que vamos construir e como | Requisitos, UCs, UI, stack e arquitetura fechados. Repositório e acesso ao GenAI a funcionar. |
| **F1: Scanner e Inputs** | 12 a 30 Out | Obter sinais do repositório e dados da equipa | Scanner v1 (Python, JS, Java) e formulário da equipa a funcionar. Demo na Peer 1 (23 out). |
| **F2: AI Engine** | 26 Out a 13 Nov | Gerar o diagnóstico por fase do SDLC | Diagnóstico das 6 fases em formato validado, com prioridade e justificação. |
| **F3: Relatório e Fluxo Completo** | 9 a 20 Nov | Juntar tudo de ponta a ponta | Fluxo completo na UI, com exportação de PDF e secção de âmbito. Funcionalidades congeladas a 20 nov. |
| **F4: Avaliação e Documentação** | 16 a 27 Nov | Medir a qualidade e documentar | Testes com vários repositórios e perfis, prompts afinados, limitações e caminho enterprise documentados. |
| **F5: Fecho** | 23 a 30 Nov | Entregar | Polimento, entregas finais (30 nov) e preparação do pitch. |

---

## 2. Plano Semana a Semana

| Semana | Início | Foco | Marco |
| :---: | :---: | :--- | :--- |
| **S1** | 5 Out | Requisitos, use cases, desenho da UI, primeira versão de stack e arquitetura, reunião com a Accenture | |
| **S2** | 12 Out | Fechar stack e arquitetura. Setup do repositório e CI. Acesso ao GenAI e primeira chamada. Decidir âmbito (formulário fixo vs agentes e chatbot). Definir o JSON de sinais. | **16 Out:** Base técnica pronta |
| **S3** | 19 Out | Scanner v1. Formulário da equipa. Primeiro prompt testado com dados à mão. | **23 Out:** Peer 1 |
| **S4** | 26 Out | Scanner completo (RF03 a RF08). Perfil contextual. Primeira geração de diagnóstico por fase. | |
| **S5** | 2 Nov | Diagnóstico estável e validado (JSON). Priorização e justificação das recomendações. Início do template do relatório. | **6 Nov:** Diagnóstico ponta a ponta |
| **S6** | 9 Nov | Exportação de PDF. Ligação da UI ao backend. Fluxo completo: repositório, equipa, diagnóstico, relatório. | |
| **S7** | 16 Nov | Avaliação: repositórios de teste, perfis de equipa, consistência. Iterar nos prompts. Pedir feedback à Accenture. | **20 Nov:** Funcionalidades congeladas |
| **S8** | 23 Nov | Documentação técnica, limitações do PoC e caminho enterprise. Correções. Começar o pitch. | **27 Nov:** Avaliação e documentação completas |
| **S9** | 30 Nov | Entregas finais. | **30 Nov:** Entregas e Peer 2 |
| **Pitch** | 2 a 5 Dez | Apresentações, pitches e defesas | |

---

## 3. Marcos principais (Milestones)

| Data | Marco | O que tem de estar feito |
| :---: | :--- | :--- |
| **16 Out** | **M1: Base Técnica** | Stack e arquitetura decididas. Repositório, CI e acesso ao GenAI a funcionar. Esquemas de dados definidos. |
| **23 Out** | **M2: Peer 1** | Demo mínima: scanner a extrair sinais e uma chamada ao GenAI com um diagnóstico de teste. |
| **6 Nov** | **M3: Diagnóstico** | Geração das 6 fases em JSON validado, com prioridade e justificação. |
| **20 Nov** | **M4: Feature Freeze** | Fluxo completo com PDF. A partir daqui só correções e avaliação. |
| **27 Nov** | **M5: Qualidade** | Avaliação feita, prompts afinados, documentação completa. |
| **30 Nov** | **M6: Entrega** | Entregas finais e peer 2. |

---

## 4. Dependências e Decisões Críticas

| Decisão ou Dependência | Preciso Até | Bloqueia |
| :--- | :---: | :--- |
| Serviço de GenAI e acesso ou créditos (Accenture) | **12 Out** | F1 (primeiro prompt), F2 |
| Âmbito: formulário fixo ou agentes e chatbot | **16 Out** | Arquitetura, UC de contexto da equipa e de geração |
| Idioma do relatório e template (Accenture) | **23 Out** | F3 (PDF) |
| Repositórios de teste (Accenture ou nossos) | **26 Out** | F1 (testar o scanner), F4 |
| Permissão para enviar excertos de código ao GenAI | **26 Out** | Desenho do prompt e RNF07 |

---

## 5. Fora do Âmbito (PoC até 30 nov)

*(Apenas avançar com estes itens após a M4 e se a avaliação estiver a correr bem)*

| Funcionalidade / Item | Referência |
| :--- | :--- |
| Perguntas dinâmicas ao utilizador com base em lacunas | RF-A |
| Chatbot de aconselhamento | RF-B |
| Ecrã do avaliador na UI (caso a avaliação seja por scripts) | UC12 a UC17 |
| Histórico de avaliações | RF32 |

---

## 6. Visão Além do PoC (Futuro / Escala Enterprise)

*(Apenas para documentação do caminho para escala enterprise - RF24, RNF17)*

| Área de Expansão | Descrição |
| :--- | :--- |
| **Análise de Código** | Mais linguagens e suporte a ferramentas de análise estática (SonarQube, Tree-Sitter). |
| **Integração ALM** | Integração direta com Jira, Azure DevOps e GitHub Projects (substituindo inputs manuais). |
| **Escalabilidade** | Suporte a repositórios grandes e monorepos via chunking e índices vetoriais. |
| **Agentes Autónomos** | Agentes equipados com ferramentas para execução automática de linters e testes. |

