# Observatório do Turismo do Sul de Minas Gerais 🏔️📊

Este projeto é fruto do **Trabalho de Conclusão de Curso (TCC)** do curso de **Engenharia de Computação** do **IFSULDEMINAS - Campus Poços de Caldas**.  

Trata-se de uma **plataforma de Engenharia de Dados** voltada para a **coleta, tratamento e visualização de indicadores estatísticos do setor turístico** na região Sul de Minas Gerais, abrangendo um total de **146 municípios**.

---

## 🎯 Objetivo

O objetivo central é **prover inteligência de dados** para gestores e pesquisadores do setor, permitindo a **análise precisa do ecossistema turístico regional** através de processos automatizados de **ETL (Extract, Transform, Load)**.

---

## 🚀 Tecnologias Utilizadas

O projeto foi construído utilizando as seguintes tecnologias:

- **Linguagem:** [Python 3.x](https://www.python.org/)  
- **Web Framework:** [Django](https://www.djangoproject.com/)  
- **Processamento Assíncrono:** [Celery](https://docs.celeryq.dev/)  
- **Broker/Mensageria:** [Redis](https://redis.io/)  
- **Containerização:** [Docker](https://www.docker.com/) & Docker Compose  
- **Banco de Dados:** PostgreSQL (sugerido por padrão no Django/Docker)

---

## 📊 Fontes de Dados e ETL

A plataforma consome e integra dados de fontes governamentais oficiais para compor o cenário econômico do turismo:

- **Receita Federal:** Dados de estabelecimentos (CNPJs) filtrados por **CNAEs** (Classificação Nacional de Atividades Econômicas) diretamente vinculados ao turismo.  
- **RAIS (Relação Anual de Informações Sociais):** Dados históricos sobre vínculos empregatícios.  
- **CAGED (Cadastro Geral de Empregados e Desempregados):** Dados atualizados sobre movimentação de pessoal (admissões e demissões).  

### Fluxo de Engenharia de Dados

1. **Extração:** Scripts automatizados buscam arquivos brutos das fontes citadas.  
2. **Tratamento:** Limpeza, padronização e georreferenciamento para as 146 cidades do Sul de Minas.  
3. **Carga:** Armazenamento estruturado para consultas por API.  
4. **Agendamento:** O Celery gerencia a periodicidade das tarefas de atualização de dados de forma assíncrona, garantindo que a interface web permaneça responsiva.

---

## 📈 Funcionalidades Principais

Através da API, é possível gerar relatórios sobre:

- **Número de estabelecimentos por município:** Visualização da densidade de empresas turísticas.  
- **Saldo de funcionários:** Acompanhamento do crescimento ou retração do setor ao longo do tempo *(Admissões vs Demissões)*.  
- **Estoque acumulado:** Total de empregos ativos no setor por região.  
- **Filtros Inteligentes:** Refinamento de busca por CNAE específico, cidade ou períodos temporais customizados.

---

## 🛠️ Como Executar o Projeto

Certifique-se de ter o [Docker](https://www.docker.com/) instalado em sua máquina.<br>
Instale também o gerenciador de pacotes uv [UV](https://docs.astral.sh/uv/)

Clone o repositório:

```bash
git clone https://github.com/Danbr23/Plataforma-de-Dados-do-Observat-rio-do-Turismo-do-Sul-de-Minas-Gerais.git
cd Plataforma-de-Dados-do-Observat-rio-do-Turismo-do-Sul-de-Minas-Gerais
uv sync
docker compose up --build
```
Acesse: http://localhost:8000/admin


## 🎓 Créditos

- Autor: Daniel Peçanha Pereira
- Orientação: Straus Michalsky
- Instituição: IFSULDEMINAS - Campus Poços de Caldas
- Curso: Engenharia de Computação


docker compose exec -t django uv run python manage.py create_manager cidade <usuario> <email> <slug-da-cidade>
uv run python manage.py create_manager igr <usuario> <email> <slug-da-igr>

gestor_pocos
1234@Abcd
teste@gmail.com