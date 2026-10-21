from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import requests
import streamlit as st
from google.api_core.exceptions import GoogleAPICallError
from google.genai import Client
from google.genai.errors import APIError
from google.genai import types
import firebase_admin
from firebase_admin import credentials, firestore
from streamlit.errors import StreamlitSecretNotFoundError


SERVICE_ACCOUNT_FILENAME = "dia-dos-professores-4daed-firebase-adminsdk-fbsvc-deb2fee28f.json"
SERVICE_ACCOUNT_PATH = Path(__file__).resolve().parent / SERVICE_ACCOUNT_FILENAME


st.set_page_config(
    page_title="Homenagem aos professores | Dia dos Professores",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

THEMES: dict[str, dict[str, str]] = {
    "Neon": {
        "name": "Neon Cyber",
        "description": "Fundo espacial com acentos ciano fluorescente e brilho futurista.",
        "background": "#07111f",
        "surface": "#0d1b2b",
        "surface_card": "rgba(13, 27, 43, 0.75)",
        "surface_card_border": "rgba(53, 215, 255, 0.22)",
        "text": "#e5fbff",
        "text_heading": "#ffffff",
        "muted": "#8ea6be",
        "primary": "#35d7ff",
        "secondary": "#a78bfa",
        "accent": "#ffd166",
        "glow": "rgba(53, 215, 255, 0.2)",
        "glow_strong": "rgba(53, 215, 255, 0.45)",
        "badge_bg": "rgba(53, 215, 255, 0.12)",
        "badge_border": "rgba(53, 215, 255, 0.35)",
        "gradient_primary": "linear-gradient(135deg, #35d7ff 0%, #3b82f6 50%, #8b5cf6 100%)",
        "gradient_card": "linear-gradient(145deg, rgba(13, 27, 43, 0.9) 0%, rgba(7, 17, 31, 0.95) 100%)",
        "gradient_title": "linear-gradient(135deg, #35d7ff 0%, #a78bfa 50%, #f472b6 100%)",
        "chip_bg": "rgba(53, 215, 255, 0.08)",
        "dot_colors": "#07111f, #0d1b2b, #35d7ff, #a78bfa",
    },
    "Escuro": {
        "name": "Escuro Moderno",
        "description": "Estética minimalista em tons de ardósia, azul real e alto contraste.",
        "background": "#0b1120",
        "surface": "#121c30",
        "surface_card": "rgba(18, 28, 48, 0.8)",
        "surface_card_border": "rgba(98, 165, 255, 0.22)",
        "text": "#edf4ff",
        "text_heading": "#ffffff",
        "muted": "#94a3b8",
        "primary": "#62a5ff",
        "secondary": "#818cf8",
        "accent": "#f59e0b",
        "glow": "rgba(66, 143, 255, 0.2)",
        "glow_strong": "rgba(66, 143, 255, 0.45)",
        "badge_bg": "rgba(98, 165, 255, 0.12)",
        "badge_border": "rgba(98, 165, 255, 0.35)",
        "gradient_primary": "linear-gradient(135deg, #62a5ff 0%, #6366f1 50%, #a855f7 100%)",
        "gradient_card": "linear-gradient(145deg, rgba(18, 28, 48, 0.9) 0%, rgba(11, 17, 32, 0.95) 100%)",
        "gradient_title": "linear-gradient(135deg, #62a5ff 0%, #a78bfa 50%, #f472b6 100%)",
        "chip_bg": "rgba(98, 165, 255, 0.08)",
        "dot_colors": "#0b1120, #121c30, #62a5ff, #818cf8",
    },
    "Claro": {
        "name": "Claro Elegante",
        "description": "Visual acadêmico com fundo luminoso, texto azul marinho e detalhes azuis.",
        "background": "#f8faff",
        "surface": "#ffffff",
        "surface_card": "rgba(255, 255, 255, 0.95)",
        "surface_card_border": "rgba(23, 105, 224, 0.18)",
        "text": "#1a2744",
        "text_heading": "#0f172a",
        "muted": "#64748b",
        "primary": "#1769e0",
        "secondary": "#7c3aed",
        "accent": "#d97706",
        "glow": "rgba(23, 105, 224, 0.15)",
        "glow_strong": "rgba(23, 105, 224, 0.3)",
        "badge_bg": "rgba(23, 105, 224, 0.08)",
        "badge_border": "rgba(23, 105, 224, 0.25)",
        "gradient_primary": "linear-gradient(135deg, #1769e0 0%, #4f46e5 50%, #7c3aed 100%)",
        "gradient_card": "linear-gradient(145deg, #ffffff 0%, #f1f5f9 100%)",
        "gradient_title": "linear-gradient(135deg, #1769e0 0%, #7c3aed 50%, #db2777 100%)",
        "chip_bg": "rgba(23, 105, 224, 0.06)",
        "dot_colors": "#f8faff, #ffffff, #1769e0, #7c3aed",
    },
}

FIREWORKS_HTML = """
<style>
  .teacher-fireworks-hero {
    position: relative;
    min-height: 230px;
    overflow: hidden;
    border-radius: 26px;
    border: 1px solid rgba(53, 215, 255, 0.35);
    background:
      radial-gradient(ellipse at 50% 120%, rgba(30, 95, 175, 0.55), transparent 60%),
      radial-gradient(circle at 15% 20%, rgba(139, 92, 246, 0.28), transparent 45%),
      radial-gradient(circle at 85% 30%, rgba(53, 215, 255, 0.28), transparent 50%),
      linear-gradient(135deg, #050d18 0%, #0d1b2e 50%, #08111e 100%);
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.12);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 2.2rem 1.8rem;
    margin-bottom: 1.5rem;
  }
  .hero-badge-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 18px;
    border-radius: 999px;
    background: rgba(53, 215, 255, 0.15);
    border: 1px solid rgba(53, 215, 255, 0.45);
    color: #5ce1e6;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    box-shadow: 0 4px 18px rgba(53, 215, 255, 0.25);
    margin-bottom: 12px;
    z-index: 2;
    animation: badge-pulse 3s ease-in-out infinite alternate;
  }
  @keyframes badge-pulse {
    0% { transform: translateY(0); box-shadow: 0 4px 18px rgba(53, 215, 255, 0.25); }
    100% { transform: translateY(-2px); box-shadow: 0 8px 28px rgba(53, 215, 255, 0.45); }
  }
  .hero-main-title {
    font-size: 2.4rem;
    font-weight: 800;
    margin: 0;
    line-height: 1.2;
    background: linear-gradient(135deg, #ffffff 0%, #c4eeff 45%, #ffd166 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.02em;
    z-index: 2;
  }
  .hero-sub-title {
    font-size: 1.05rem;
    color: #b0cce3;
    margin-top: 10px;
    max-width: 680px;
    line-height: 1.55;
    z-index: 2;
    font-weight: 400;
  }
  .stars-layer {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background-image: 
      radial-gradient(1.5px 1.5px at 8% 22%, #ffffff, transparent),
      radial-gradient(2px 2px at 22% 38%, #ffd166, transparent),
      radial-gradient(1.5px 1.5px at 38% 18%, #5ce1e6, transparent),
      radial-gradient(2px 2px at 62% 28%, #ffffff, transparent),
      radial-gradient(1.5px 1.5px at 78% 15%, #f472b6, transparent),
      radial-gradient(2px 2px at 92% 42%, #ffd166, transparent),
      radial-gradient(1.5px 1.5px at 84% 78%, #5ce1e6, transparent),
      radial-gradient(1.5px 1.5px at 12% 82%, #ffffff, transparent);
    opacity: 0.85;
  }
  .firework-burst {
    position: absolute;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    pointer-events: none;
  }
  .f1 {
    left: 16%;
    bottom: 30px;
    color: #35d7ff;
    box-shadow: 
      0 -48px currentColor, 0 48px currentColor,
      48px 0 currentColor, -48px 0 currentColor,
      34px 34px currentColor, -34px 34px currentColor,
      34px -34px currentColor, -34px -34px currentColor,
      0 -72px #ffe066, 72px 0 #ffe066, -72px 0 #ffe066, 0 72px #ffe066;
    animation: burst-anim 3.2s ease-out infinite;
  }
  .f2 {
    left: 84%;
    bottom: 45px;
    color: #ff6b9d;
    box-shadow: 
      0 -42px currentColor, 0 42px currentColor,
      42px 0 currentColor, -42px 0 currentColor,
      30px 30px currentColor, -30px 30px currentColor,
      30px -30px currentColor, -30px -30px currentColor,
      0 -64px #35d7ff, 64px 0 #35d7ff, -64px 0 #35d7ff, 0 64px #35d7ff;
    animation: burst-anim 3.4s ease-out infinite 1.1s;
  }
  .f3 {
    left: 50%;
    bottom: 22px;
    color: #ffe066;
    box-shadow: 
      0 -55px currentColor, 0 55px currentColor,
      55px 0 currentColor, -55px 0 currentColor,
      39px 39px currentColor, -39px 39px currentColor,
      39px -39px currentColor, -39px -39px currentColor,
      0 -80px #a78bfa, 80px 0 #a78bfa, -80px 0 #a78bfa, 0 80px #a78bfa;
    animation: burst-anim 2.9s ease-out infinite 2s;
  }
  @keyframes burst-anim {
    0% { opacity: 0; transform: scale(0.05); }
    15% { opacity: 1; }
    65% { opacity: 0.9; transform: scale(1); }
    100% { opacity: 0; transform: scale(1.35); }
  }
  @media (prefers-reduced-motion: reduce) {
    .f1, .f2, .f3 { animation: none; opacity: 0.4; }
    .hero-badge-pill { animation: none; }
  }
</style>
<div class="teacher-fireworks-hero" role="banner" aria-label="Homenagem com fogos de artifício aos professores">
  <div class="stars-layer"></div>
  <span class="firework-burst f1"></span>
  <span class="firework-burst f2"></span>
  <span class="firework-burst f3"></span>
  <div class="hero-badge-pill">
    <span>✨ 15 DE OUTUBRO • DIA DOS PROFESSORES ✨</span>
  </div>
  <h1 class="hero-main-title">Homenagem Especial aos Professores</h1>
  <p class="hero-sub-title">
    Celebrando a dedicação, a generosidade e a paixão por ensinar que inspiram nossos passos na tecnologia e na engenharia.
  </p>
</div>
"""


class FirebaseAuthError(Exception):
    """An authentication error returned by Firebase Authentication."""


def get_secret_section(name: str) -> Any:
    try:
        return st.secrets.get(name, {})
    except StreamlitSecretNotFoundError:
        return {}


def firebase_auth_request(endpoint: str, payload: dict[str, str], api_key: str) -> dict[str, Any]:
    response = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:{endpoint}",
        params={"key": api_key},
        json=payload,
        timeout=20,
    )
    body = response.json()
    if not response.ok:
        message = body.get("error", {}).get("message", "AUTHENTICATION_FAILED")
        messages = {
            "EMAIL_EXISTS": "Esse e-mail já possui uma conta.",
            "EMAIL_NOT_FOUND": "Não encontramos uma conta com esse e-mail.",
            "INVALID_PASSWORD": "A senha informada está incorreta.",
            "INVALID_LOGIN_CREDENTIALS": "E-mail ou senha incorretos.",
            "WEAK_PASSWORD": "A senha não atende à política de segurança configurada no Firebase.",
            "INVALID_EMAIL": "Informe um endereço de e-mail válido.",
            "OPERATION_NOT_ALLOWED": "Ative o método e-mail/senha no Firebase Authentication.",
            "TOO_MANY_ATTEMPTS_TRY_LATER": "Muitas tentativas. Aguarde um pouco e tente novamente.",
        }
        raise FirebaseAuthError(messages.get(message, f"Firebase recusou a solicitação: {message}"))
    return body


def initialize_firestore(service_account: Any, project_id: str) -> Any:
    import firebase_admin
    from firebase_admin import credentials, firestore

    try:
        app = firebase_admin.get_app(project_id)
    except ValueError:
        app = firebase_admin.initialize_app(
            credentials.Certificate(service_account),
            {"projectId": project_id},
            name=project_id,
        )
    return firestore.client(app=app)


@st.cache_resource
def get_firestore_client_from_file(service_account_path: str, modified_ns: int) -> Any:
    import firebase_admin
    from firebase_admin import firestore

    path = Path(service_account_path)
    service_account = json.loads(path.read_text(encoding="utf-8"))
    project_id = str(service_account["project_id"])
    try:
        app = firebase_admin.get_app(project_id)
    except ValueError:
        app = firebase_admin.initialize_app(
            credentials.Certificate(str(path)),
            {"projectId": project_id},
            name=project_id,
        )
    return firestore.client(app=app)


@st.cache_resource
def get_firestore_client_from_secret(service_account_json: str) -> Any:
    service_account = json.loads(service_account_json)
    project_id = str(service_account["project_id"])
    return initialize_firestore(service_account, project_id)


def get_firebase_config() -> Any:
    config = get_secret_section("firebase")
    api_key = (config or {}).get("api_key") or os.getenv("FIREBASE_API_KEY")
    if not api_key:
        return None
    return {"api_key": str(api_key)}


def get_firestore() -> Any | None:
    configured_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE")
    firebase_config = get_secret_section("firebase")
    secret_path = (firebase_config or {}).get("service_account_file")
    if configured_path:
        credential_path = Path(configured_path)
    elif secret_path:
        credential_path = Path(str(secret_path))
        if not credential_path.is_absolute():
            credential_path = Path(__file__).resolve().parent / credential_path
    else:
        credential_path = SERVICE_ACCOUNT_PATH

    if credential_path.is_file():
        if firebase_config and firebase_config.get("project_id"):
            credential_metadata = json.loads(credential_path.read_text(encoding="utf-8"))
            if credential_metadata.get("project_id") != firebase_config["project_id"]:
                raise ValueError(
                    "O project_id configurado no secrets.toml não corresponde "
                    "ao projeto da conta de serviço."
                )
        return get_firestore_client_from_file(
            str(credential_path.resolve()),
            credential_path.stat().st_mtime_ns,
        )

    service_account_json = (firebase_config or {}).get("service_account_json")
    if service_account_json:
        return get_firestore_client_from_secret(str(service_account_json))
    return None


def save_profile(identity: dict[str, str], theme: str) -> bool:
    database = get_firestore()
    if database is None:
        return False
    from firebase_admin import firestore

    database.collection("users").document(identity["uid"]).set(
        {
            "display_name": identity["name"],
            "email": identity["email"],
            "theme": theme,
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    return True


def load_profile(identity: dict[str, str]) -> dict[str, Any]:
    database = get_firestore()
    if database is None:
        return {}
    profile = database.collection("users").document(identity["uid"]).get()
    return profile.to_dict() or {} if profile.exists else {}


def save_chat_message(identity: dict[str, str], role: str, content: str) -> bool:
    database = get_firestore()
    if database is None:
        return False
    from firebase_admin import firestore

    database.collection("users").document(identity["uid"]).collection("chat_messages").add(
        {
            "role": role,
            "content": content,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )
    return True


def load_chat_messages(identity: dict[str, str]) -> list[dict[str, str]]:
    database = get_firestore()
    if database is None:
        return []
    from firebase_admin import firestore

    documents = (
        database.collection("users")
        .document(identity["uid"])
        .collection("chat_messages")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(100)
        .stream()
    )
    messages = [document.to_dict() or {} for document in documents]
    messages.reverse()
    return [
        {"role": message["role"], "content": message["content"]}
        for message in messages
        if message.get("role") in {"user", "assistant"} and message.get("content")
    ]


def save_learning_activity(identity: dict[str, str], answer: str) -> bool:
    database = get_firestore()
    if database is None:
        return False
    from firebase_admin import firestore

    database.collection("users").document(identity["uid"]).collection("activities").add(
        {
            "type": "cybersecurity_quiz",
            "answer": answer,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )
    return True


def get_google_identity() -> dict[str, str] | None:
    if not getattr(st.user, "is_logged_in", False):
        return None
    email = str(getattr(st.user, "email", "") or "")
    subject = str(getattr(st.user, "sub", "") or email)
    if not email or not subject:
        st.error("O Google não retornou um e-mail ou identificador válido para esta conta.")
        return None
    return {
        "uid": f"google_{subject}",
        "email": email,
        "name": str(getattr(st.user, "name", "") or email.split("@")[0]),
        "provider": "google",
    }


def get_active_identity() -> dict[str, str] | None:
    return st.session_state.get("identity") or get_google_identity()


def apply_theme(theme_name: str) -> None:
    palette = THEMES.get(theme_name, THEMES["Neon"])
    st.html(
        f"""
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

          :root {{
            --bg-color: {palette["background"]};
            --surface-color: {palette["surface"]};
            --text-color: {palette["text"]};
            --primary-color: {palette["primary"]};
            --secondary-color: {palette["secondary"]};
            --muted-color: {palette["muted"]};
            --glow-color: {palette["glow"]};
            --glow-strong: {palette["glow_strong"]};
          }}

          html, body, [class*="css"], .stApp {{
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
          }}

          code, pre, .stCodeBlock {{
            font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
          }}

          .stApp {{
            background:
              radial-gradient(ellipse at 85% 5%, {palette["glow"]}, transparent 36%),
              radial-gradient(ellipse at 15% 95%, {palette["glow"]}, transparent 32%),
              {palette["background"]};
            color: {palette["text"]};
          }}

          /* Sidebar Customization */
          section[data-testid="stSidebar"] {{
            background-color: {palette["surface"]} !important;
            border-right: 1px solid {palette["surface_card_border"]};
          }}

          /* Buttons */
          .stButton > button {{
            border-radius: 14px !important;
            font-weight: 600 !important;
            letter-spacing: 0.02em !important;
            transition: all 0.25s cubic-bezier(0.2, 0.8, 0.2, 1) !important;
            border: 1px solid {palette["surface_card_border"]} !important;
          }}
          .stButton > button:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 24px {palette["glow"]} !important;
            border-color: {palette["primary"]} !important;
          }}
          .stButton > button[kind="primary"] {{
            background: {palette["gradient_primary"]} !important;
            color: #ffffff !important;
            border: none !important;
            box-shadow: 0 4px 20px {palette["glow_strong"]} !important;
          }}
          .stButton > button[kind="primary"]:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 30px {palette["glow_strong"]} !important;
            filter: brightness(1.1) !important;
          }}

          /* Form Inputs */
          div[data-baseweb="input"] {{
            border-radius: 12px !important;
            background-color: {palette["surface"]} !important;
            border: 1px solid {palette["surface_card_border"]} !important;
            transition: all 0.2s ease !important;
          }}
          div[data-baseweb="input"]:focus-within {{
            border-color: {palette["primary"]} !important;
            box-shadow: 0 0 0 3px {palette["glow"]} !important;
          }}

          /* Containers with borders */
          div[data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: 18px !important;
            border-color: {palette["surface_card_border"]} !important;
            background: {palette["surface_card"]} !important;
            backdrop-filter: blur(12px) !important;
            transition: all 0.25s ease !important;
          }}
          div[data-testid="stVerticalBlockBorderWrapper"]:hover {{
            border-color: {palette["primary"]} !important;
            box-shadow: 0 10px 30px {palette["glow"]} !important;
          }}

          /* Chat Message styling */
          div[data-testid="stChatMessage"] {{
            border-radius: 18px !important;
            padding: 1.1rem 1.3rem !important;
            margin-bottom: 0.85rem !important;
            border: 1px solid {palette["surface_card_border"]} !important;
            background: {palette["surface_card"]} !important;
            backdrop-filter: blur(10px) !important;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08) !important;
          }}

          /* Custom Classes */
          .tribute-card {{
            position: relative;
            padding: 2.2rem 2.5rem;
            border-radius: 24px;
            background: {palette["gradient_card"]};
            border: 1px solid {palette["surface_card_border"]};
            box-shadow: 0 18px 48px {palette["glow"]};
            backdrop-filter: blur(16px);
            margin: 1.5rem 0 2rem 0;
            overflow: hidden;
            animation: card-rise 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) both;
          }}
          .tribute-seal-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.2rem;
            border-bottom: 1px solid {palette["surface_card_border"]};
            padding-bottom: 0.8rem;
          }}
          .tribute-seal-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 14px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            background: {palette["badge_bg"]};
            border: 1px solid {palette["badge_border"]};
            color: {palette["primary"]};
          }}
          .tribute-date {{
            font-size: 0.82rem;
            color: {palette["muted"]};
            font-weight: 500;
          }}
          .tribute-heading {{
            font-size: 1.6rem;
            font-weight: 800;
            color: {palette["text_heading"]};
            margin-bottom: 1rem;
            letter-spacing: -0.01em;
          }}
          .tribute-text {{
            font-size: 1.05rem;
            line-height: 1.85;
            color: {palette["muted"]};
            margin-bottom: 1.2rem;
          }}
          .tribute-text strong {{
            color: {palette["primary"]};
          }}
          .tribute-footer {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-top: 1.5rem;
            padding-top: 1.2rem;
            border-top: 1px dashed {palette["surface_card_border"]};
          }}
          .tribute-signature-label {{
            display: block;
            font-size: 0.85rem;
            color: {palette["muted"]};
            font-style: italic;
          }}
          .tribute-signature-names {{
            display: block;
            font-size: 1.15rem;
            font-weight: 700;
            color: {palette["text_heading"]};
            margin-top: 4px;
          }}
          .tribute-icon-stamp {{
            font-size: 2.4rem;
            opacity: 0.8;
          }}

          /* Metrics */
          .metric-card {{
            background: {palette["surface_card"]};
            border: 1px solid {palette["surface_card_border"]};
            border-radius: 18px;
            padding: 1.2rem 1.4rem;
            text-align: center;
            backdrop-filter: blur(12px);
            transition: all 0.25s ease;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.05);
            height: 100%;
          }}
          .metric-card:hover {{
            transform: translateY(-3px);
            border-color: {palette["primary"]};
            box-shadow: 0 10px 25px {palette["glow"]};
          }}
          .metric-icon {{
            font-size: 1.9rem;
            margin-bottom: 0.35rem;
          }}
          .metric-value {{
            font-size: 1.2rem;
            font-weight: 800;
            color: {palette["text_heading"]};
            margin-bottom: 0.25rem;
          }}
          .metric-label {{
            font-size: 0.82rem;
            color: {palette["muted"]};
            line-height: 1.4;
          }}

          /* Tech Pills */
          .tech-pill {{
            display: inline-block;
            padding: 3px 10px;
            margin: 3px 4px 3px 0;
            border-radius: 999px;
            font-size: 0.74rem;
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
            background: {palette["badge_bg"]};
            border: 1px solid {palette["badge_border"]};
            color: {palette["primary"]};
          }}

          /* Auth Box */
          .auth-hero-box {{
            padding: 2.2rem;
            border-radius: 24px;
            background: {palette["gradient_card"]};
            border: 1px solid {palette["surface_card_border"]};
            box-shadow: 0 18px 45px {palette["glow"]};
            backdrop-filter: blur(14px);
            height: 100%;
          }}
          .auth-feature-item {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
            margin-bottom: 1.2rem;
          }}
          .auth-feature-icon {{
            font-size: 1.3rem;
            background: {palette["badge_bg"]};
            border: 1px solid {palette["badge_border"]};
            padding: 6px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
          }}

          /* IoT Mockup Terminal */
          .iot-terminal {{
            background: #060e19;
            border: 1px solid rgba(53, 215, 255, 0.3);
            border-radius: 16px;
            padding: 1rem 1.2rem;
            font-family: 'JetBrains Mono', monospace;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
            margin-bottom: 1rem;
          }}
          .iot-terminal-bar {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 10px;
          }}
          .iot-terminal-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
          }}
          .dot-red {{ background: #ff5f56; }}
          .dot-yellow {{ background: #ffbd2e; }}
          .dot-green {{ background: #27c93f; }}
          .iot-terminal-title {{
            font-size: 0.78rem;
            color: #8bb2d1;
            margin-left: 6px;
            font-weight: 500;
          }}

          /* Theme Preview Cards */
          .theme-preview-card {{
            padding: 1.2rem;
            border-radius: 16px;
            border: 1px solid {palette["surface_card_border"]};
            background: {palette["surface_card"]};
            text-align: center;
            cursor: pointer;
            transition: all 0.25s ease;
          }}
          .theme-preview-card:hover {{
            transform: translateY(-3px);
            border-color: {palette["primary"]};
          }}
          .theme-preview-active {{
            border-color: {palette["primary"]} !important;
            box-shadow: 0 8px 25px {palette["glow"]} !important;
          }}
          .palette-dots {{
            display: flex;
            gap: 6px;
            justify-content: center;
            margin: 10px 0;
          }}
          .color-dot {{
            width: 18px;
            height: 18px;
            border-radius: 50%;
            border: 1px solid rgba(255, 255, 255, 0.2);
          }}

          @keyframes card-rise {{
            from {{ opacity: 0; transform: translateY(24px); }}
            to {{ opacity: 1; transform: translateY(0); }}
          }}
          @media (prefers-reduced-motion: reduce) {{
            .tribute-card {{ animation: none; }}
          }}
        </style>
        """
    )


def render_authentication() -> None:
    st.html(
        """
        <div style="text-align: center; padding: 1.8rem 0 1rem 0;">
          <span style="display: inline-block; padding: 4px 16px; border-radius: 999px; background: rgba(53, 215, 255, 0.12); border: 1px solid rgba(53, 215, 255, 0.35); color: #35d7ff; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.16em;">
            ✦ CELEBRAÇÃO ACADÊMICA • HOMENAGEM COLETIVA ✦
          </span>
          <h1 style="font-size: 2.4rem; font-weight: 800; margin: 0.8rem 0 0.2rem 0; letter-spacing: -0.02em;">
            Para todos os professores
          </h1>
          <p style="font-size: 1.05rem; opacity: 0.8; max-width: 600px; margin: 0 auto;">
            Uma homenagem a todos os professores que inspiram, ensinam e fazem parte da nossa trajetória.
          </p>
        </div>
        """
    )

    left_col, right_col = st.columns([1.1, 1], gap="large")

    with left_col:
        st.html(
            """
            <div class="auth-hero-box">
              <span class="tribute-seal-badge">🎓 PLATAFORMA DE HOMENAGEM</span>
              <h3 style="font-size: 1.5rem; font-weight: 800; margin: 0.8rem 0 0.8rem 0;">
                Bem-vindo ao espaço comemorativo!
              </h3>
              <p style="font-size: 0.95rem; line-height: 1.6; opacity: 0.85; margin-bottom: 1.5rem;">
                Este espaço foi criado para agradecer a todos os professores que compartilham
                conhecimento, incentivam novas ideias e contribuem para nossa formação.
              </p>
              
              <div class="auth-feature-item">
                <div class="auth-feature-icon">🎖️</div>
                <div>
                  <strong style="display: block; font-size: 0.95rem;">Mural de Gratidão</strong>
                  <span style="font-size: 0.85rem; opacity: 0.8;">Homenagem dedicada e reconhecimento ao impacto em nossa formação.</span>
                </div>
              </div>

              <div class="auth-feature-item">
                <div class="auth-feature-icon">🔬</div>
                <div>
                  <strong style="display: block; font-size: 0.95rem;">Laboratório de Ideias</strong>
                  <span style="font-size: 0.85rem; opacity: 0.8;">Desafios práticos de cibersegurança e simulação de telemetria IoT com ESP32.</span>
                </div>
              </div>

              <div class="auth-feature-item">
                <div class="auth-feature-icon">🤖</div>
                <div>
                  <strong style="display: block; font-size: 0.95rem;">Conversa com IA (Gemini)</strong>
                  <span style="font-size: 0.85rem; opacity: 0.8;">Assistente educacional interativa treinada nos tópicos lecionados pelo professor.</span>
                </div>
              </div>

              <div class="auth-feature-item">
                <div class="auth-feature-icon">🎨</div>
                <div>
                  <strong style="display: block; font-size: 0.95rem;">Experiência Personalizada</strong>
                  <span style="font-size: 0.85rem; opacity: 0.8;">Temas Neon, Escuro e Claro salvos em nuvem via Firebase.</span>
                </div>
              </div>
            </div>
            """
        )

    with right_col:
        with st.container(border=True):
            mode = st.segmented_control(
                "Acesso",
                options=["Entrar", "Criar conta"],
                default="Entrar",
                key="auth_mode",
                width="stretch",
            )
            firebase = get_firebase_config()

            if mode == "Criar conta":
                with st.form("register_form"):
                    name = st.text_input("Seu nome completo ou apelido")
                    email = st.text_input("E-mail para identificação")
                    password = st.text_input("Senha (mínimo 6 caracteres)", type="password")
                    confirmation = st.text_input("Confirme sua senha", type="password")
                    submitted = st.form_submit_button(
                        "Criar minha conta",
                        type="primary",
                        width="stretch",
                        disabled=firebase is None,
                    )
                if submitted:
                    if not name.strip() or not email.strip():
                        st.error("Por favor, preencha seu nome e seu e-mail.")
                    elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()):
                        st.error("Informe um formato de e-mail válido.")
                    elif len(password) < 6:
                        st.error("A senha precisa ter pelo menos 6 caracteres.")
                    elif password != confirmation:
                        st.error("As duas senhas informadas não conferem.")
                    else:
                        try:
                            account = firebase_auth_request(
                                "signUp",
                                {
                                    "email": email.strip(),
                                    "password": password,
                                    "displayName": name.strip(),
                                    "returnSecureToken": "true",
                                },
                                str(firebase["api_key"]),
                            )
                            identity = {
                                "uid": account["localId"],
                                "email": account["email"],
                                "name": name.strip(),
                                "provider": "password",
                            }
                            try:
                                if not save_profile(identity, "Neon"):
                                    st.warning(
                                        "A conta foi criada, mas o perfil não pôde ser gravado no Firestore."
                                    )
                            except (
                                GoogleAPICallError,
                                ValueError,
                                KeyError,
                                RuntimeError,
                            ) as error:
                                st.error(f"A conta foi criada, mas o perfil não foi salvo: {error}")
                            st.session_state.identity = identity
                            st.session_state.theme_choice = "Neon"
                            st.session_state.profile_loaded_for = identity["uid"]
                            st.success("Conta criada com sucesso! Bem-vindo(a) à homenagem!")
                            st.rerun()
                        except (FirebaseAuthError, requests.RequestException, ValueError, KeyError) as error:
                            st.error(f"Não foi possível criar sua conta: {error}")
            else:
                with st.form("login_form"):
                    email = st.text_input("Seu e-mail")
                    password = st.text_input("Sua senha", type="password")
                    submitted = st.form_submit_button(
                        "Entrar na plataforma",
                        type="primary",
                        width="stretch",
                        disabled=firebase is None,
                    )
                if submitted:
                    try:
                        account = firebase_auth_request(
                            "signInWithPassword",
                            {
                                "email": email.strip(),
                                "password": password,
                                "returnSecureToken": "true",
                            },
                            str(firebase["api_key"]),
                        )
                        st.session_state.identity = {
                            "uid": account["localId"],
                            "email": account["email"],
                            "name": account.get("displayName") or account["email"].split("@")[0],
                            "provider": "password",
                        }
                        st.rerun()
                    except (FirebaseAuthError, requests.RequestException, ValueError, KeyError) as error:
                        st.error(f"Não foi possível entrar: {error}")

            if firebase is None:
                st.info(
                    "💡 Dica de configuração: configure a Web API Key em firebase.api_key no arquivo de segredos "
                    "para habilitar login por e-mail e senha."
                )

            st.divider()
            google_configured = bool(get_secret_section("auth").get("google"))
            if st.button(
                "Entrar com Google Workspace",
                icon=":material/login:",
                width="stretch",
                disabled=not google_configured,
            ):
                st.login("google")
            if not google_configured:
                st.caption("🔒 O login via Google será ativado após configurar as credenciais OIDC.")


def render_home(identity: dict[str, str]) -> None:
    st.html(FIREWORKS_HTML)

    # Metric Highlight Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.html(
            """
            <div class="metric-card">
              <div class="metric-icon">💡</div>
              <div class="metric-value">Curiosidade Ativa</div>
              <div class="metric-label">Incentivo constante a questionar e construir</div>
            </div>
            """
        )
    with m2:
        st.html(
            """
            <div class="metric-card">
              <div class="metric-icon">⚡</div>
              <div class="metric-value">5 Grandes Áreas</div>
              <div class="metric-label">Hardware, Software, IA, IoT e Cibersegurança</div>
            </div>
            """
        )
    with m3:
        st.html(
            """
            <div class="metric-card">
              <div class="metric-icon">🛡️</div>
              <div class="metric-value">Ética & Defesa</div>
              <div class="metric-label">Tecnologia a serviço da proteção e da sociedade</div>
            </div>
            """
        )
    with m4:
        st.html(
            """
            <div class="metric-card">
              <div class="metric-icon">🚀</div>
              <div class="metric-value">Futuro em Ação</div>
              <div class="metric-label">Aulas práticas que preparam para o mercado real</div>
            </div>
            """
        )

    st.write("")

    # Tribute Card (Carta de Agradecimento)
    st.html(
        f"""
        <div class="tribute-card">
          <div class="tribute-seal-row">
            <span class="tribute-seal-badge">🎖️ HOMENAGEM DE HONRA AO MÉRITO ACADÊMICO</span>
            <span class="tribute-date">15 de Outubro • Dia dos Professores</span>
          </div>
          <div class="tribute-content">
            <h2 class="tribute-heading">Ao nosso querido mestre Nilton,</h2>
            <p class="tribute-text">
              Obrigado por compartilhar tanto conhecimento com tanta paciência, entusiasmo e paixão contínua. 
              Por sempre nos desafiar a pensar criticamente, a explorar os fundamentos e por nos mostrar que aprender 
              não é apenas memorizar teoremas, mas <strong>construir, experimentar, codificar e transformar ideias em soluções reais</strong>.
            </p>
            <p class="tribute-text">
              Seja na precisão dos circuitos elétricos, na lógica elegante de Python e C++, na responsabilidade da cibersegurança 
              ou na construção de sistemas completos, cada projeto e cada desafio proposto em aula deixaram marcas indeléveis em nossa 
              visão profissional e pessoal. Que sua dedicação continue acendendo o brilho da curiosidade em gerações de alunos.
            </p>
            <div class="tribute-footer">
              <div class="tribute-signature">
                <span class="tribute-signature-label">Com imensa admiração, respeito e gratidão,</span>
                <strong class="tribute-signature-names">Raphael Campos Squilaro, seus alunos e colegas.</strong>
              </div>
              <div class="tribute-icon-stamp">🎓</div>
            </div>
          </div>
        </div>
        """
    )

    st.html(
        """
        <div style="margin: 2rem 0 1rem 0;">
          <span class="tribute-seal-badge">🌐 MULTIDISCIPLINARIDADE</span>
          <h2 style="font-size: 1.8rem; font-weight: 800; margin: 0.5rem 0 0.2rem 0;">
            Um Universo de Conhecimento e Ideias
          </h2>
          <p style="font-size: 0.95rem; opacity: 0.8;">
            Os pilares tecnológicos que o professor Nilton domina, conecta e transmite em suas aulas:
          </p>
        </div>
        """
    )

    areas = [
        (
            ":material/shield:",
            "Cibersegurança Defensiva",
            "Segurança & Redes",
            "Curiosidade com responsabilidade ética: proteger ecossistemas digitais, modelar ameaças e pensar como defensor em profundidade.",
            ["SIEM", "Firewall", "Zero Trust", "Hardening", "Wireshark"],
        ),
        (
            ":material/electric_bolt:",
            "Engenharia Elétrica",
            "Hardware & Potência",
            "A energia e os circuitos fundamentais que transformam teoria em movimento, automação e soluções de alta eficiência.",
            ["Circuitos", "Sinais", "Potência", "Eletrônica", "Filtros"],
        ),
        (
            ":material/memory:",
            "Inteligência Artificial & Python",
            "Modelos & Dados",
            "Algoritmos preditivos, redes neurais e processamento analítico com Python para resolver problemas práticos e escaláveis.",
            ["Python 3.12", "Gemini", "NumPy", "Scikit-Learn", "Automação"],
        ),
        (
            ":material/sensors:",
            "IoT com C++ & ESP32",
            "Embarcados & Sensores",
            "Pequenos dispositivos, grandes impactos: sensores conectados à nuvem transmitindo telemetria em tempo real com baixo consumo.",
            ["C++20", "ESP32", "MQTT", "GPIO", "I2C / SPI"],
        ),
        (
            ":material/phone_android:",
            "Flutter, Java & Spring Boot",
            "Full Stack & Mobile",
            "Aplicações multiplataforma completas: da experiência do usuário no dispositivo móvel até microsserviços de backend robustos.",
            ["Flutter", "Java 21", "Spring Boot", "REST APIs", "Clean Arch"],
        ),
    ]

    cols = st.columns(3)
    for idx, (icon, title, category, description, tags) in enumerate(areas):
        with cols[idx % 3]:
            with st.container(border=True):
                st.markdown(
                    f"<span style='font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.7;'>{category}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"### {icon} {title}")
                st.write(description)
                pills_html = "".join([f"<span class='tech-pill'>{tag}</span>" for tag in tags])
                st.html(f"<div style='margin-top: 10px;'>{pills_html}</div>")


TEACHER_TRIBUTES = {
    "Professor Nilton": (
        ":material/electric_bolt:",
        "Obrigado por compartilhar tantos conhecimentos com entusiasmo e por incentivar a "
        "curiosidade, o pensamento crítico e a criação de soluções. Suas aulas e desafios em "
        "tecnologia e engenharia contribuíram para minha formação e continuarão inspirando "
        "novos projetos e aprendizados.",
        ["Engenharia", "Computação", "Tecnologia", "Cibersegurança", "Python e C++"],
    ),
    "Professor Clayton": (
        ":material/code:",
        "Obrigado por me ensinar sobre desenvolvimento backend, Java, Spring Boot e Next.js. "
        "Seu conhecimento e dedicação contribuíram para ampliar minha visão sobre como construir "
        "aplicações e transformar ideias em projetos.",
        ["Backend", "Java", "Spring Boot", "Next.js"],
    ),
    "Professor Delago": (
        ":material/settings:",
        "Obrigado por compartilhar conhecimentos fundamentais sobre sistemas operacionais, "
        "arquitetura de redes e HTML. Suas aulas ajudaram a ampliar minha compreensão sobre "
        "os sistemas e as tecnologias que sustentam a web.",
        ["Sistemas operacionais", "Arquitetura de redes", "HTML"],
    ),
    "Professor Sander": (
        ":material/movie:",
        "Obrigado por apresentar o universo da multimídia e por contribuir com minha formação "
        "nessa área. Seu trabalho inspira novas formas de criar e comunicar por meio da tecnologia.",
        ["Multimídia"],
    ),
    "Professor Caio": (
        ":material/sports_esports:",
        "Obrigado por compartilhar seus conhecimentos sobre desenvolvimento de jogos e por "
        "mostrar mais uma possibilidade de criação, experimentação e expressão com a tecnologia.",
        ["Desenvolvimento de jogos"],
    ),
    "Professora Alessandra": (
        ":material/database:",
        "Obrigado por ensinar sobre banco de dados e por contribuir para minha compreensão de "
        "como organizar, armazenar e trabalhar com informações.",
        ["Banco de dados"],
    ),
    "Professora Marcela Raboni": (
        ":material/volunteer_activism:",
        "Com carinho e saudade, homenageio a professora Marcela Raboni. Sou grato por tudo que "
        "me ensinou sobre soft skills, levantamento de requisitos, além de um pouco de Java e "
        "banco de dados. Seus ensinamentos e sua lembrança seguem fazendo parte da minha trajetória.",
        ["Soft skills", "Levantamento de requisitos", "Java", "Banco de dados"],
    ),
}


def render_teacher_tribute(teacher: str) -> None:
    icon, message, subjects = TEACHER_TRIBUTES[teacher]
    is_memorial = teacher == "Professora Marcela Raboni"

    st.title(teacher, icon=icon)
    st.caption(
        "Homenagem em memória, com carinho e saudade"
        if is_memorial
        else "Uma homenagem especial no Dia dos Professores"
    )
    with st.container(border=True):
        st.subheader("Com gratidão" if not is_memorial else "Com carinho e saudade")
        st.write(message)
        for subject in subjects:
            st.badge(subject)


def render_lab(identity: dict[str, str]) -> None:
    st.html(
        """
        <div style="margin-bottom: 1.5rem;">
          <span class="tribute-seal-badge">🔬 ESPAÇO PRÁTICO • ENGENHARIA & CÓDIGO</span>
          <h1 style="font-size: 2.2rem; font-weight: 800; margin: 0.5rem 0 0.2rem 0;">
            Laboratório de Ideias & Experimentação
          </h1>
          <p style="font-size: 1rem; opacity: 0.8;">
            Missões e simulações interativas inspiradas nas disciplinas e desafios lecionados pelo professor Nilton.
          </p>
        </div>
        """
    )

    left, right = st.columns([1, 1], gap="medium")

    with left:
        with st.container(border=True):
            st.html(
                """
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                  <span class="tribute-seal-badge">🛡️ DESAFIO #01 • CIBERSEGURANÇA</span>
                  <span style="font-size: 0.75rem; opacity: 0.7;">Nível: Defesa Ativa</span>
                </div>
                """
            )
            st.markdown("### :material/security: Defesa em Camadas (Defense in Depth)")
            st.write(
                "Em sistemas corporativos e aplicações modernas, qual das práticas abaixo oferece "
                "a maior proteção contra sequestro de contas e credenciais vazadas?"
            )
            answer = st.radio(
                "Selecione a resposta ideal:",
                [
                    "Usar a mesma senha complexa em todos os servidores e serviços da empresa",
                    "Ativar autenticação multifator (MFA/2FA) com chaves físicas ou TOTP e usar senhas únicas gerenciadas",
                    "Compartilhar as senhas de administrador apenas por canais internos de chat",
                ],
                key="cyber_quiz",
            )
            if st.button("Verificar resposta", type="primary", key="check_quiz", icon=":material/task_alt:"):
                if answer == "Ativar autenticação multifator (MFA/2FA) com chaves físicas ou TOTP e usar senhas únicas gerenciadas":
                    st.success(
                        "Excelente! O modelo de Defesa em Profundidade garante que, mesmo no caso "
                        "de um vazamento de credencial, a camada secundária impeça a invasão."
                    )
                else:
                    st.info(
                        "Dica de segurança: considere o risco do ponto único de falha e a importância "
                        "de barreiras multifatoriais para mitigar credenciais vazadas."
                    )
                try:
                    if not save_learning_activity(identity, answer):
                        st.warning("Nota: A resposta foi validada, mas o Firestore não está conectado para persistência.")
                except (GoogleAPICallError, ValueError, KeyError, RuntimeError) as error:
                    st.error(f"Não foi possível salvar o registro da atividade: {error}")

    with right:
        with st.container(border=True):
            st.html(
                """
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                  <span class="tribute-seal-badge">📡 BANCADA IoT • ESP32 & C++</span>
                  <span style="font-size: 0.75rem; opacity: 0.7;">Microcontroladores</span>
                </div>
                """
            )
            st.markdown("### :material/developer_board: Telemetria e Alerta Inteligente")
            st.write(
                "Um microcontrolador ESP32 conectado a um sensor térmico monitora o ambiente "
                "e despacha alertas em tempo real via Wi-Fi."
            )

            # Simulated interactive slider
            simulated_temp = st.slider(
                "Simulador de Temperatura do Sensor (°C)",
                min_value=15.0,
                max_value=50.0,
                value=26.5,
                step=0.5,
                key="temp_slider",
            )

            # Terminal window representation
            if simulated_temp > 35.0:
                status_html = f"<span style='color: #ff5f56; font-weight: 700;'>🔥 ALERTA: Temp {simulated_temp}°C excede 35.0°C! Acionando cooler e enviando MQTT...</span>"
            else:
                status_html = f"<span style='color: #27c93f; font-weight: 700;'>🟢 NORMAL: Temp {simulated_temp}°C estável. Operação segura.</span>"

            st.html(
                f"""
                <div class="iot-terminal">
                  <div class="iot-terminal-bar">
                    <span class="iot-terminal-dot dot-red"></span>
                    <span class="iot-terminal-dot dot-yellow"></span>
                    <span class="iot-terminal-dot dot-green"></span>
                    <span class="iot-terminal-title">ESP32-WROOM-32 • Serial Monitor (115200 baud)</span>
                  </div>
                  <div style="font-size: 0.82rem; line-height: 1.5; color: #b8daf5;">
                    [INFO] Wi-Fi conectado: SSID="Lab-Nilton-5G", IP: 192.168.1.108<br>
                    [DATA] Leitura Sensor DHT22 / Termopar: {simulated_temp:.1f} °C<br>
                    {status_html}
                  </div>
                </div>
                """
            )

            st.code(
                "// Lógica C++ para ESP32\n"
                "if (temperaturaAtual > LIMITE_CRITICO) {\n"
                "    digitalWrite(PINO_RELE_COOLER, HIGH);\n"
                '    mqttClient.publish("telemetria/alerta", "TEMPERATURA_ALTA");\n'
                '    Serial.printf("[ALERTA] Temperatura crítica: %.1f C\\n", temperaturaAtual);\n'
                "}",
                language="cpp",
            )

    st.write("")
    with st.container(border=True):
        st.html(
            """
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
              <span class="tribute-seal-badge">🧠 NÚCLEO DE IA • PYTHON</span>
              <span style="font-size: 0.75rem; opacity: 0.7;">Machine Learning</span>
            </div>
            """
        )
        st.markdown("### :material/psychology: Detecção de Anomalias em Sensores")
        st.write(
            "Em projetos de ponta ensinados pelo professor Nilton, modelos de inteligência artificial em Python "
            "são integrados a fluxos de engenharia para identificar padrões incomuns antes que falhas aconteçam."
        )

        p1, p2, p3, p4 = st.columns(4)
        with p1:
            st.html(
                """
                <div style="padding: 10px; border-radius: 12px; background: rgba(53, 215, 255, 0.08); border: 1px solid rgba(53, 215, 255, 0.2); text-align: center;">
                  <strong style="display: block; font-size: 0.85rem;">1. Coleta Sensor</strong>
                  <span style="font-size: 0.75rem; opacity: 0.7;">ESP32 via MQTT</span>
                </div>
                """
            )
        with p2:
            st.html(
                """
                <div style="padding: 10px; border-radius: 12px; background: rgba(53, 215, 255, 0.08); border: 1px solid rgba(53, 215, 255, 0.2); text-align: center;">
                  <strong style="display: block; font-size: 0.85rem;">2. Limpeza NumPy</strong>
                  <span style="font-size: 0.75rem; opacity: 0.7;">Filtro de ruído e normalização</span>
                </div>
                """
            )
        with p3:
            st.html(
                """
                <div style="padding: 10px; border-radius: 12px; background: rgba(53, 215, 255, 0.08); border: 1px solid rgba(53, 215, 255, 0.2); text-align: center;">
                  <strong style="display: block; font-size: 0.85rem;">3. Inferência ML</strong>
                  <span style="font-size: 0.75rem; opacity: 0.7;">Isolation Forest / Z-Score</span>
                </div>
                """
            )
        with p4:
            st.html(
                """
                <div style="padding: 10px; border-radius: 12px; background: rgba(53, 215, 255, 0.08); border: 1px solid rgba(53, 215, 255, 0.2); text-align: center;">
                  <strong style="display: block; font-size: 0.85rem;">4. Decisão Humana</strong>
                  <span style="font-size: 0.75rem; opacity: 0.7;">Engenheiro no controle</span>
                </div>
                """
            )


def render_chat() -> None:
    st.html(
        """
        <div style="margin-bottom: 1.5rem;">
          <span class="tribute-seal-badge">🤖 ASSISTENTE EDUCACIONAL INTELIGENTE</span>
          <h1 style="font-size: 2.2rem; font-weight: 800; margin: 0.5rem 0 0.2rem 0;">
            Conversa com IA
          </h1>
          <p style="font-size: 1rem; opacity: 0.8;">
            Tire dúvidas, discuta projetos e explore temas de Python, Cibersegurança, Engenharia Elétrica, IoT e Arquitetura.
          </p>
        </div>
        """
    )

    gemini_config = get_secret_section("gemini")
    api_key = str(gemini_config.get("api_key") or os.getenv("GEMINI_API_KEY", ""))
    model = str(gemini_config.get("model") or "gemini-3.8-flash")
    if not api_key:
        st.info("💡 Para conversar com a IA, configure `gemini.api_key` no arquivo de segredos ou defina a variável `GEMINI_API_KEY`.")
        return

    identity = get_active_identity()
    owner = identity["uid"] if identity else "anonymous"
    if st.session_state.get("chat_owner") != owner:
        st.session_state.chat_owner = owner
        try:
            st.session_state.chat_messages = (
                load_chat_messages(identity) if identity else []
            )
        except (GoogleAPICallError, ValueError, KeyError, RuntimeError) as error:
            st.session_state.chat_messages = []
            st.error(f"Não foi possível carregar o histórico do Firestore: {error}")
    if identity:
        try:
            if get_firestore() is None:
                st.warning(
                    "O histórico desta conversa não será salvo na nuvem: conta de serviço do Firestore não configurada."
                )
        except (GoogleAPICallError, ValueError, KeyError, RuntimeError) as error:
            st.error(f"Não foi possível conectar ao Firestore: {error}")

    # Prompt suggestions bar
    st.markdown("##### 💡 Sugestões rápidas para perguntar:")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("🛡️ Cibersegurança em APIs", use_container_width=True):
            st.session_state["pending_prompt"] = "Quais são as melhores práticas de segurança defensiva para proteger APIs REST contra ataques?"
    with c2:
        if st.button("📡 Projeto com ESP32 e C++", use_container_width=True):
            st.session_state["pending_prompt"] = "Como planejar a arquitetura de um projeto IoT com ESP32 enviando telemetria por MQTT em C++?"
    with c3:
        if st.button("🧠 IA com Python e Sensores", use_container_width=True):
            st.session_state["pending_prompt"] = "Como implementar uma detecção de anomalias simples em Python para leituras de sensores industriais?"
    with c4:
        if st.button("⚡ Circuitos e Eletrônica", use_container_width=True):
            st.session_state["pending_prompt"] = "Qual é a importância de capacitores de desacoplamento e isolamento galvânico em circuitos de potência?"

    # Empty State Banner
    if not st.session_state.get("chat_messages"):
        st.html(
            """
            <div style="padding: 2rem; border-radius: 20px; background: rgba(53, 215, 255, 0.05); border: 1px dashed rgba(53, 215, 255, 0.3); text-align: center; margin: 1.5rem 0;">
              <span style="font-size: 2.5rem; display: block; margin-bottom: 0.5rem;">🎓</span>
              <h3 style="font-size: 1.3rem; font-weight: 700; margin-bottom: 0.5rem;">Olá! Como posso ajudar você nos estudos hoje?</h3>
              <p style="font-size: 0.95rem; opacity: 0.8; max-width: 550px; margin: 0 auto;">
                Faça uma pergunta sobre programação, circuitos elétricos, redes seguras ou selecione uma das sugestões acima.
              </p>
            </div>
            """
        )

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle suggested prompt or input
    pending_prompt = st.session_state.pop("pending_prompt", None)
    chat_prompt = st.chat_input("Pergunte sobre um projeto, circuito, código ou tecnologia...")
    prompt = pending_prompt or chat_prompt

    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        if identity:
            try:
                if not save_chat_message(identity, "user", prompt):
                    st.warning("Sua mensagem não pôde ser gravada no Firestore.")
            except (GoogleAPICallError, ValueError, KeyError, RuntimeError) as error:
                st.error(f"Não foi possível salvar sua mensagem: {error}")
        conversation = [
            {
                "role": "user" if message["role"] == "user" else "model",
                "parts": [{"text": message["content"]}],
            }
            for message in st.session_state.chat_messages
        ]
        system_instruction = (
            "Você é uma assistente educacional acolhedora e altamente técnica, participando da "
            "homenagem ao professor Nilton no Dia dos Professores. Responda em português brasileiro, "
            "com clareza, incentivo pedagógico e precisão técnica. Auxilie em cibersegurança defensiva, "
            "engenharia elétrica, inteligência artificial, Python, IoT com C++, Flutter, Java e Spring Boot. "
            "Para cibersegurança, forneça exclusivamente orientações em contexto autorizado, ético, "
            "defensivo e educacional."
        )
        try:
            client = Client(api_key=api_key)
            with st.chat_message("assistant"):
                stream = client.models.generate_content_stream(
                    model=model,
                    contents=conversation,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                    ),
                )
                response = st.write_stream(
                    chunk.text for chunk in stream if chunk.text
                )
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": str(response)}
            )
            if identity:
                try:
                    if not save_chat_message(identity, "assistant", str(response)):
                        st.warning("A resposta da IA não foi salva no Firestore.")
                except (GoogleAPICallError, ValueError, KeyError, RuntimeError) as error:
                    st.error(f"Não foi possível salvar a resposta da IA: {error}")
        except APIError as error:
            st.error(
                f"O Gemini não conseguiu responder. Verifique a chave e o modelo configurados. ({error})"
            )


def render_profile(identity: dict[str, str]) -> None:
    st.html(
        """
        <div style="margin-bottom: 1.5rem;">
          <span class="tribute-seal-badge">👤 CONFIGURAÇÕES DE USUÁRIO</span>
          <h1 style="font-size: 2.2rem; font-weight: 800; margin: 0.5rem 0 0.2rem 0;">
            Meu Perfil & Preferências
          </h1>
          <p style="font-size: 1rem; opacity: 0.8;">
            Personalize a aparência da plataforma e guarde suas preferências salvas em nuvem.
          </p>
        </div>
        """
    )

    initial = (identity.get("name") or "U")[0].upper()
    provider_name = "Google Workspace" if identity["provider"] == "google" else "Firebase Authentication"

    with st.container(border=True):
        st.html(
            f"""
            <div style="display: flex; align-items: center; gap: 20px; padding: 0.5rem 0;">
              <div style="width: 72px; height: 72px; border-radius: 50%; background: linear-gradient(135deg, #35d7ff, #a78bfa); display: flex; align-items: center; justify-content: center; font-size: 2rem; font-weight: 800; color: #ffffff; box-shadow: 0 8px 24px rgba(53, 215, 255, 0.4);">
                {initial}
              </div>
              <div>
                <h3 style="font-size: 1.4rem; font-weight: 800; margin: 0;">{identity['name']}</h3>
                <span style="font-size: 0.95rem; opacity: 0.8;">{identity['email']}</span>
                <div style="margin-top: 6px;">
                  <span class="tribute-seal-badge">🔒 {provider_name}</span>
                  <span class="tech-pill">Homenageador Ativo</span>
                </div>
              </div>
            </div>
            """
        )

    st.write("")
    st.markdown("### :material/palette: Escolha o Tema Visual")
    st.caption("Ajuste a paleta de cores para se adaptar ao seu estilo e ambiente de iluminação.")

    current_theme = st.session_state.get("theme_choice", "Neon")

    # Visual Theme Cards
    t_cols = st.columns(3)
    for idx, (theme_key, theme_data) in enumerate(THEMES.items()):
        is_active = (theme_key == current_theme)
        active_class = "theme-preview-active" if is_active else ""
        dots = "".join([f"<span class='color-dot' style='background: {c.strip()};'></span>" for c in theme_data["dot_colors"].split(",")])
        with t_cols[idx]:
            st.html(
                f"""
                <div class="theme-preview-card {active_class}">
                  <strong style="font-size: 1.1rem; display: block;">{theme_data['name']}</strong>
                  <div class="palette-dots">{dots}</div>
                  <span style="font-size: 0.8rem; opacity: 0.75; display: block; line-height: 1.4;">
                    {theme_data['description']}
                  </span>
                </div>
                """
            )

    st.write("")
    selected_theme = st.segmented_control(
        "Selecione o tema ativo:",
        options=list(THEMES),
        default=current_theme,
        key="theme_choice",
    )
    apply_theme(selected_theme or "Neon")

    st.write("")
    if st.button("Salvar preferência de tema", type="primary", icon=":material/save:"):
        try:
            if save_profile(identity, selected_theme or "Neon"):
                st.success("🎉 Preferência salva com sucesso no seu perfil do Firebase!")
            else:
                st.info(
                    "A preferência foi aplicada a esta sessão. Para salvá-la em nuvem, "
                    "configure a conta de serviço do Firestore."
                )
        except (GoogleAPICallError, ValueError, KeyError, RuntimeError) as error:
            st.error(f"Não foi possível salvar o perfil no Firestore: {error}")


def main() -> None:
    identity = get_active_identity()
    if identity is None:
        apply_theme("Neon")
        render_authentication()
        return

    if st.session_state.get("profile_loaded_for") != identity["uid"]:
        try:
            profile = load_profile(identity)
            if not profile:
                save_profile(identity, "Neon")
            saved_theme = profile.get("theme", "Neon")
            st.session_state.theme_choice = saved_theme if saved_theme in THEMES else "Neon"
            st.session_state.profile_loaded_for = identity["uid"]
        except (GoogleAPICallError, ValueError, KeyError, RuntimeError) as error:
            st.error(f"Não foi possível carregar o perfil do Firestore: {error}")
            st.session_state.theme_choice = "Neon"
            st.session_state.profile_loaded_for = identity["uid"]

    apply_theme(st.session_state.get("theme_choice", "Neon"))

    with st.sidebar:
        user_initial = (identity.get("name") or "U")[0].upper()
        st.html(
            f"""
            <div style="padding: 0.8rem 0 1.2rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 1rem;">
              <div style="display: flex; align-items: center; gap: 12px;">
                <div style="width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, #35d7ff, #a78bfa); display: flex; align-items: center; justify-content: center; font-size: 1.2rem; font-weight: 800; color: #ffffff;">
                  {user_initial}
                </div>
                <div>
                  <strong style="display: block; font-size: 1rem; line-height: 1.2;">{identity['name']}</strong>
                  <span style="font-size: 0.75rem; color: #27c93f; font-weight: 600;">● Conectado</span>
                </div>
              </div>
            </div>
            """
        )

        st.markdown("### :material/explore: Navegação")
        page_options = [
            "Início",
            *TEACHER_TRIBUTES,
            "Laboratório",
            "Conversa com IA",
            "Meu perfil",
        ]
        if st.session_state.get("current_page") not in page_options:
            st.session_state.current_page = "Início"
        page = st.selectbox(
            "Selecione uma página:",
            options=page_options,
            index=0,
            key="current_page",
            width="stretch",
        )

        st.divider()

        st.html(
            """
            <div style="padding: 10px; border-radius: 14px; background: rgba(53, 215, 255, 0.06); border: 1px solid rgba(53, 215, 255, 0.15); margin-bottom: 1rem;">
              <span style="font-size: 0.75rem; font-weight: 700; color: #35d7ff; letter-spacing: 0.08em; text-transform: uppercase;">
                ✨ MENSAGEM DO DIA
              </span>
              <p style="font-size: 0.8rem; line-height: 1.45; margin-top: 4px; opacity: 0.85;">
                "Ensinar não é transferir conhecimento, mas criar as possibilidades para a sua própria produção."
              </p>
              <span style="font-size: 0.72rem; opacity: 0.6; display: block; text-align: right;">— Paulo Freire</span>
            </div>
            """
        )

        if st.button("Encerrar sessão", icon=":material/logout:", width="stretch"):
            st.session_state.pop("identity", None)
            st.session_state.pop("chat_messages", None)
            st.session_state.pop("chat_owner", None)
            if identity["provider"] == "google":
                st.logout()
            st.rerun()

    if page == "Laboratório":
        render_lab(identity)
    elif page in TEACHER_TRIBUTES:
        render_teacher_tribute(page)
    elif page == "Conversa com IA":
        render_chat()
    elif page == "Meu perfil":
        render_profile(identity)
    else:
        render_home(identity)


main()
