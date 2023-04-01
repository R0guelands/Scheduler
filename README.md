# <center>Scheduler</center>

## 1. Propósito

O Scheduler é um projeto que visa a criação de um sistema de agendamento de tarefas, que pode ser utilizado por qualquer pessoa que precise de um sistema de agendamento de tarefas. Feito em python, o sistema é capaz de agendar tarefas diárias, semanais e mensais, além de ser capaz de criar http triggers, que são tarefas que são executadas quando uma requisição http é feita para um determinado endpoint.

Uma tarefa nada mais é que um projeto Python válido colocado dentro da pasta "projects". Para ser válida, uma tarefa deve conter um main.py e um .venv. O main.py é o arquivo que será executado quando a tarefa for executada, e o .venv é o arquivo que contém as dependências da tarefa. 

Adicionalmente, o Scheduler possui um sistema de logs, que é capaz de registrar todas as execuções de tarefas, e também de registrar erros que ocorreram durante a execução de uma tarefa. Para isso funcionar, é necessário que o arquivo main.py da aplicação instale e use o módulo "logger" do Scheduler, que pode ser baixado [aqui](https://github.com/R0guelands/logconfig).

## 2. Como instalar

1. Instale python 3.11.0 ou superior
2. Instale nodejs v19.0.0 ou superior
3. Clone o repositório
4. Navegue até a pasta do repositório
5. Crie um ambiente virtual python com o comando:
```bash
python -m venv .venv
```
6. Ative o ambiente virtual com o comando:
```bash
source .venv/bin/activate
```
7. Instale as dependências do projeto com o comando:
```bash
pip install -r requirements.txt
```
8. Instale as dependências do frontend com o comando:
```bash
npm install
```
9. Crie uma pasta chamada "projects" na raiz do repositório
10. Crie uma pasta chamada "logs" na raiz do repositório
11. Crie um arquivo chamado .env na raiz do repositório
12. Adicione as seguintes variáveis de ambiente no arquivo .env:
```bash
MONGO_CONNECTION_STRING=<string de conexão do mongodb>
```
13. Instale pm2, que irá manter o servidor rodando em segundo plano, com o comando:
```bash
npm install pm2 -g
```
14. Inicie o servidor com o comando:
```bash
pm2 start server.py --interpreter .venv/bin/python
```
 Caso queira que o servidor seja iniciado automaticamente quando o computador for ligado, execute o comando:
```bash
pm2 startup
```
e siga as instruções que aparecerem na tela


15. Acesse o frontend do Scheduler em http://localhost:5000


## 3. Como usar

Usar o Scheduler é muito simples. Primeiro, crie um projeto Python válido dentro da pasta "projects". Depois, vá até o frontend do Scheduler. Seu projeto deve aparecer na lista. Agora basta clicar no botão "Edit" e configurar a tarefa. Caso tenha dúvidas de como inserir o json de configuração, basta clicar acessar o arquivo txt "exemplo.txt" do repositório.



