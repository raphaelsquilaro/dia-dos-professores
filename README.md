# Homenagem ao professor Nilton

Aplicação Streamlit para celebrar o Dia dos Professores com fogos de artifício,
mensagens de agradecimento, homenagens a professores, laboratório de ideias,
perfil personalizável e chat educacional com IA.

A navegação lateral oferece uma página dedicada a cada professor homenageado:
Nilton, Clayton, Vanderlei, Delago, Sander, Caio, Alessandra e uma homenagem
em memória da professora Marcela Raboni. A tela de login também apresenta a
homenagem como dedicada a todos os professores.

## Executar localmente

Requer Python 3.11 ou superior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
streamlit run app.py
```

Edite `.streamlit/secrets.toml` com suas próprias credenciais. Esse arquivo e
arquivos de conta de serviço do Firebase são ignorados pelo Git; nunca publique
chaves de API nem a chave privada da conta de serviço.

## Firebase Authentication

1. No console do projeto `dia-dos-professores`, habilite **Authentication** e o
   método **E-mail/senha**.
2. Em **Configurações do projeto > Geral**, copie a **Web API Key** para
   `firebase.api_key` no arquivo de segredos (ou defina `FIREBASE_API_KEY`).
3. As contas criadas e autenticadas por e-mail/senha usam o Firebase
   Authentication.
4. Crie o banco **Cloud Firestore**. A aplicação lê o caminho configurado em
   `firebase.service_account_file` (por padrão,
   `dia-dos-professores-4daed-firebase-adminsdk-fbsvc-deb2fee28f.json`) para
   salvar nome, e-mail e tema no documento `users/{uid}`. O caminho no TOML é
   relativo à pasta principal do projeto. Para usar outro caminho via ambiente,
   defina `FIREBASE_SERVICE_ACCOUNT_FILE`. Em ambiente publicado, a credencial
   também pode ser fornecida em `firebase.service_account_json` no arquivo de
   segredos.
5. Restrinja a conta de serviço ao mínimo necessário e não compartilhe seu JSON.

O nome, e-mail e tema são salvos no Firestore. Também são salvos o histórico da
conversa com IA (`users/{uid}/chat_messages`) e as respostas ao desafio
(`users/{uid}/activities`). A senha é gerenciada pelo Firebase Authentication e
nunca é copiada para o Firestore. Sem uma credencial de conta de serviço
disponível, o login/cadastro continua usando Firebase Authentication, mas os
dados de perfil, conversa e atividades ficam apenas na sessão atual; a aplicação
avisa quando uma gravação não puder ser feita.

## Login com Google

1. No Google Cloud Console, crie um cliente OAuth do tipo **Aplicativo da Web**.
2. Cadastre `http://localhost:8501/oauth2callback` como URI de redirecionamento
   autorizada; em produção, use o domínio HTTPS publicado pela aplicação.
3. Preencha `[auth]` e `[auth.google]` em `.streamlit/secrets.toml`. Gere um
   `cookie_secret` aleatório e forte.
4. Para que contas Google também sejam usuários do Firebase Authentication,
   habilite Google como provedor no Firebase. O login OIDC desta aplicação
   autentica no Google; a persistência adicional do perfil é feita no Firestore.

## Conversa com IA

Preencha `gemini.api_key` e `gemini.model`. Alternativamente, defina a variável
de ambiente `GEMINI_API_KEY`. A conversa usa a API Gemini com respostas em
streaming. Para usuários autenticados, o histórico também é salvo no Firestore;
sem login, ele permanece somente na sessão atual do Streamlit.

## Temas e conteúdo

O perfil permite alternar entre os temas claro, escuro e neon azul. O laboratório
inclui uma pergunta de segurança defensiva e uma ideia de projeto IoT em C++.
