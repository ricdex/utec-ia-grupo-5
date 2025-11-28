"""
FinAdvisor Streamlit Frontend
Chat conversacional con recomendaciones de portafolio
"""

import streamlit as st
import requests
import json
from datetime import datetime
import os
from typing import Optional, Dict, List

# Page config
st.set_page_config(
    page_title="FinAdvisor",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .recommendation-box {
        background-color: #f0f8ff;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 5px solid #1f77b4;
        margin: 1rem 0;
    }
    .metrics-box {
        background-color: #f5f5f5;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #ffc107;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #28a745;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "client_id" not in st.session_state:
    st.session_state.client_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "api_endpoint" not in st.session_state:
    st.session_state.api_endpoint = os.getenv("API_ENDPOINT", "http://localhost:8000")
if "client_profile" not in st.session_state:
    st.session_state.client_profile = {}
if "recommendation" not in st.session_state:
    st.session_state.recommendation = None
if "portfolio_data" not in st.session_state:
    st.session_state.portfolio_data = None
if "capital_data" not in st.session_state:
    st.session_state.capital_data = None
if "model_name" not in st.session_state:
    st.session_state.model_name = None
if "available_models" not in st.session_state:
    st.session_state.available_models = {}

# API Helper Functions
def call_api(method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
    """Call API endpoint with error handling"""
    try:
        url = f"{st.session_state.api_endpoint}{endpoint}"

        if method.upper() == "GET":
            response = requests.get(url, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, timeout=30)
        else:
            st.error(f"Unsupported HTTP method: {method}")
            return None

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error ({response.status_code}): {response.text}")
            return None

    except requests.exceptions.ConnectionError:
        st.error(f"❌ No se puede conectar a la API en {st.session_state.api_endpoint}")
        return None
    except requests.exceptions.Timeout:
        st.error("⏱️ Timeout de la API (>30s)")
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None


def send_chat_message(client_id: str, message: str, model_name: Optional[str] = None) -> Optional[str]:
    """Send message to chat endpoint with optional model override"""
    data = {
        "client_id": client_id,
        "message": message
    }
    if model_name:
        data["model_name"] = model_name
    response = call_api("POST", "/chat", data)
    return response.get("response") if response else None


def get_recommendation(client_id: str, amount: float, risk_profile: str, months: int, target_return: float) -> Optional[Dict]:
    """Get portfolio recommendation"""
    response = call_api("POST", "/recommendation", {
        "client_id": client_id,
        "amount": amount,
        "risk_profile": risk_profile,
        "months": months,
        "target_return": target_return
    })
    return response if response else None


def get_client_profile(client_id: str) -> Optional[Dict]:
    """Get client profile"""
    response = call_api("GET", f"/profile/{client_id}")
    return response.get("profile") if response else None


def check_api_health() -> bool:
    """Check if API is available"""
    response = call_api("GET", "/health")
    return response is not None


def get_available_models() -> Dict:
    """Get list of available models from API"""
    response = call_api("GET", "/models")
    if response:
        return response
    return {
        "current": {"provider": "anthropic", "model": "claude-3-5-sonnet-20241022"},
        "available_providers": {
            "anthropic": [
                {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"},
                {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku"},
                {"id": "claude-3-opus-20250219", "name": "Claude 3 Opus"}
            ],
            "bedrock": []
        }
    }


# Sidebar
st.sidebar.markdown("## ⚙️ Configuración")

# API Endpoint configuration
api_endpoint = st.sidebar.text_input(
    "URL de la API",
    value=st.session_state.api_endpoint,
    help="Ej: http://localhost:8000 o https://<api-gateway-url>"
)
st.session_state.api_endpoint = api_endpoint

# Check API health
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.sidebar.button("🔍 Verificar Conexión API"):
        if check_api_health():
            st.sidebar.success("✅ API conectada")
        else:
            st.sidebar.error("❌ API no disponible")

with col2:
    if st.sidebar.button("🤖 Cargar Modelos"):
        models_info = get_available_models()
        st.session_state.available_models = models_info
        st.sidebar.success("✅ Modelos cargados")

st.sidebar.divider()

# Model Selection
st.sidebar.markdown("## 🤖 Modelo IA")

if st.session_state.available_models:
    models_info = st.session_state.available_models
    current_model = models_info.get("current", {}).get("model", "claude-3-5-sonnet-20241022")

    # Show current model
    st.sidebar.info(f"**Modelo actual**: {current_model.split('/')[-1]}")

    # Create model options
    anthropic_models = models_info.get("available_providers", {}).get("anthropic", [])
    bedrock_models = models_info.get("available_providers", {}).get("bedrock", [])

    selected_provider = st.sidebar.selectbox(
        "Proveedor",
        ["anthropic", "bedrock"] if bedrock_models else ["anthropic"],
        help="Elige entre Anthropic (Claude) o AWS Bedrock"
    )

    if selected_provider == "anthropic":
        models_list = anthropic_models
    else:
        models_list = bedrock_models

    if models_list:
        model_options = {m["name"]: m["id"] for m in models_list}
        selected_model_name = st.sidebar.selectbox(
            "Modelo",
            list(model_options.keys()),
            help="Selecciona el modelo de IA a usar"
        )
        st.session_state.model_name = model_options[selected_model_name]

        # Show model info
        selected_model_info = next((m for m in models_list if m["id"] == st.session_state.model_name), None)
        if selected_model_info:
            st.sidebar.caption(f"📝 {selected_model_info.get('description', '')}")
    else:
        st.sidebar.warning(f"No hay modelos disponibles para {selected_provider}")
else:
    st.sidebar.info("👈 Haz clic en 'Cargar Modelos' para ver opciones disponibles")

st.sidebar.divider()

# Client selection/creation
st.sidebar.markdown("## 👤 Cliente")

client_id = st.sidebar.text_input(
    "ID del Cliente",
    value=st.session_state.client_id or "",
    placeholder="Ej: CLI001"
)

if client_id:
    st.session_state.client_id = client_id

    if st.sidebar.button("📋 Cargar Perfil"):
        profile = get_client_profile(client_id)
        if profile:
            st.session_state.client_profile = profile
            st.sidebar.success(f"✅ Perfil cargado: {profile.get('name', 'Cliente')}")
        else:
            st.sidebar.error("No se pudo cargar el perfil")

st.sidebar.divider()

# Profile information
if st.session_state.client_profile:
    st.sidebar.markdown("### Información del Cliente")
    profile = st.session_state.client_profile

    st.sidebar.metric(
        "Monto Disponible",
        f"USD {profile.get('available_amount_usd', 0):,.0f}"
    )

    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.sidebar.write(f"**Perfil**: {profile.get('risk_profile', 'N/A')}")
    with col2:
        st.sidebar.write(f"**Horizonte**: {profile.get('investment_horizon_months', 'N/A')}m")

    st.sidebar.write(f"**Meta Retorno**: {profile.get('target_return_pct', 0):.1f}%")

# Main content
st.markdown("<div class='main-header'><h1>💰 FinAdvisor</h1><p>Asesor Financiero Impulsado por IA</p></div>", unsafe_allow_html=True)

if not st.session_state.client_id:
    st.info("👈 Por favor, ingresa un ID de cliente en la barra lateral para comenzar.")
    st.stop()

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["💬 Chat", "📊 Recomendación", "📈 Análisis", "💼 Mi Portafolio", "📉 Mercado"])

# TAB 1: Chat
with tab1:
    st.subheader("Conversación con FinAdvisor")

    # Display chat history
    chat_container = st.container()

    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            else:
                st.chat_message("assistant").write(msg["content"])

    # Chat input
    user_input = st.chat_input("Escribe tu pregunta o comentario...")

    if user_input:
        # Add user message to history
        st.session_state.messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })

        # Display user message
        st.chat_message("user").write(user_input)

        # Get response from API with selected model
        with st.spinner("Pensando..."):
            response = send_chat_message(
                st.session_state.client_id,
                user_input,
                model_name=st.session_state.model_name
            )

        if response:
            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().isoformat()
            })
            st.chat_message("assistant").write(response)
        else:
            st.error("No se pudo obtener respuesta de la API")

# TAB 2: Recommendation
with tab2:
    st.subheader("Obtener Recomendación de Portafolio")

    if not st.session_state.client_profile:
        st.warning("⚠️ Carga primero el perfil del cliente desde la barra lateral")
    else:
        profile = st.session_state.client_profile

        # Input form
        col1, col2 = st.columns(2)

        with col1:
            amount = st.number_input(
                "Monto a Invertir (USD)",
                value=profile.get("available_amount_usd", 50000),
                min_value=1000,
                step=5000
            )

            risk_profile = st.selectbox(
                "Perfil de Riesgo",
                ["conservador", "moderado", "agresivo"],
                index=["conservador", "moderado", "agresivo"].index(profile.get("risk_profile", "moderado"))
            )

        with col2:
            months = st.number_input(
                "Horizonte de Inversión (meses)",
                value=profile.get("investment_horizon_months", 24),
                min_value=6,
                step=6
            )

            target_return = st.number_input(
                "Retorno Objetivo Anual (%)",
                value=profile.get("target_return_pct", 8.0),
                min_value=0.0,
                max_value=50.0,
                step=0.5
            )

        if st.button("🎯 Generar Recomendación", type="primary"):
            with st.spinner("Analizando opciones de inversión..."):
                recommendation = get_recommendation(
                    st.session_state.client_id,
                    amount,
                    risk_profile,
                    months,
                    target_return
                )

            if recommendation:
                st.session_state.recommendation = recommendation

                # Display recommendation
                st.markdown("<div class='recommendation-box'>", unsafe_allow_html=True)

                # Allocations
                st.markdown("### 📋 Asignación Recomendada")

                allocations = recommendation.get("recommendation", {}).get("allocations", [])

                if allocations:
                    df_allocations = []
                    for alloc in allocations:
                        df_allocations.append({
                            "Producto": alloc["product_name"],
                            "Porcentaje": f"{alloc['percentage']:.1f}%",
                            "Monto USD": f"${alloc['amount']:,.0f}",
                            "Retorno Anual": f"{alloc['annual_rate']:.2%}"
                        })

                    st.dataframe(df_allocations, use_container_width=True)

                # Metrics
                st.markdown("### 📊 Métricas de la Cartera")

                metrics = recommendation.get("recommendation", {}).get("metrics", {})

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        "Retorno Esperado",
                        f"{metrics.get('expected_return', 0):.2%}"
                    )

                with col2:
                    st.metric(
                        "Volatilidad",
                        f"{metrics.get('expected_volatility', 0):.2%}"
                    )

                with col3:
                    st.metric(
                        "Sharpe Ratio",
                        f"{metrics.get('sharpe_ratio', 0):.3f}"
                    )

                with col4:
                    st.metric(
                        "Liquidez",
                        metrics.get('expected_liquidity', 'media').capitalize()
                    )

                # Data Source Information
                st.markdown("### 📊 Información de Datos")

                data_source = recommendation.get("recommendation", {}).get("data_source", "Base de datos")
                note = recommendation.get("recommendation", {}).get("note", "")

                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"📌 Fuente: {data_source}")
                with col2:
                    if note:
                        st.success(f"✓ {note}")

                # Guardrails
                st.markdown("### ✅ Validación")

                guardrails = recommendation.get("guardrails", {})

                if guardrails.get("is_valid"):
                    st.markdown(
                        "<div class='success-box'>✅ Recomendación válida según guardrails</div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        "<div class='warning-box'>⚠️ Requiere revisión de restricciones</div>",
                        unsafe_allow_html=True
                    )

                if guardrails.get("needs_escalation"):
                    st.markdown(
                        "<div class='warning-box'>⚠️ Caso de riesgo alto - Requiere revisión humana</div>",
                        unsafe_allow_html=True
                    )

                # Disclaimer
                if guardrails.get("disclaimer"):
                    st.markdown(
                        "<div class='warning-box'>" + guardrails.get("disclaimer", "").replace("\n", "<br>") + "</div>",
                        unsafe_allow_html=True
                    )

                st.markdown("</div>", unsafe_allow_html=True)

            else:
                st.error("No se pudo generar la recomendación")

# TAB 4: Mi Portafolio
with tab4:
    st.subheader("Mi Portafolio Actual")

    if not st.session_state.client_id:
        st.warning("⚠️ Carga primero un cliente")
    else:
        col1, col2 = st.columns([2, 1])

        with col1:
            if st.button("🔄 Actualizar Portafolio", key="refresh_portfolio"):
                # Get contracted products
                response = call_api("POST", "/chat", {
                    "client_id": st.session_state.client_id,
                    "message": "cuales son los productos que tengo hasta ahora"
                })
                st.session_state.portfolio_data = response if response else None
                st.rerun()

        with col2:
            if st.button("💰 Ver Capital Invertido", key="get_capital"):
                response = call_api("POST", "/chat", {
                    "client_id": st.session_state.client_id,
                    "message": "cual es el capital que tengo hasta ahora invertido"
                })
                st.session_state.capital_data = response if response else None
                st.rerun()

        # Display portfolio data
        if "portfolio_data" in st.session_state and st.session_state.portfolio_data:
            st.markdown("### 📋 Productos Contratados")
            st.info(st.session_state.portfolio_data.get("response", "Sin productos contratados"))

        if "capital_data" in st.session_state and st.session_state.capital_data:
            st.markdown("### 💵 Capital Invertido")
            st.info(st.session_state.capital_data.get("response", "No hay información de capital invertido"))

# TAB 5: Mercado
with tab5:
    st.subheader("Desempeño del Mercado")

    if not st.session_state.client_id:
        st.warning("⚠️ Carga primero un cliente")
    else:
        if st.button("📊 Ver Desempeño del Mercado", key="get_market"):
            with st.spinner("Obteniendo datos del mercado..."):
                response = call_api("POST", "/chat", {
                    "client_id": st.session_state.client_id,
                    "message": "como va el mercado de mis productos hasta ahora"
                })

            if response:
                st.markdown(response.get("response", "No se pudo obtener información del mercado"))
            else:
                st.error("Error al obtener datos del mercado")

        st.divider()

        st.markdown("### 📈 Información de Productos")
        st.markdown("""
        Este tab muestra el desempeño actual del mercado para tus productos invertidos.

        **Información incluida:**
        - Precios actuales de productos
        - Rendimiento YTD (Año hasta hoy)
        - Volatilidad esperada
        - Componentes accionarios (NASDAQ) si aplica
        - Tickers y sectores de los subyacentes

        Haz clic en el botón arriba para obtener información actualizada.
        """)

# TAB 3: Analysis
with tab3:
    st.subheader("Análisis y Educación Financiera")

    info_tab1, info_tab2, info_tab3 = st.tabs(["📚 Conceptos", "🎯 Metas", "⚠️ Riesgos"])

    with info_tab1:
        st.markdown("""
        ### Conceptos Financieros Clave

        **Perfil de Riesgo**
        - **Conservador**: Prioriza capital seguro sobre retorno. Ideal para corto plazo.
        - **Moderado**: Balance entre riesgo y retorno. Recomendado para largo plazo.
        - **Agresivo**: Busca máximo retorno. Requiere horizonte largo (>5 años).

        **Diversificación**
        La diversificación reduce riesgo distribuyendo inversiones entre múltiples productos.
        Una cartera bien diversificada puede lograr mejores retornos con menos volatilidad.

        **Retorno vs Riesgo**
        - Retorno esperado: Ganancia anual promedio esperada
        - Volatilidad: Variabilidad del precio (mayor = más riesgo)
        - Sharpe Ratio: Medida de retorno ajustada por riesgo (mayor = mejor)
        """)

    with info_tab2:
        st.markdown("""
        ### Establecer Metas Financieras

        **Pasos para definir tus metas:**

        1. **Horizonte de Tiempo**: ¿Cuánto tiempo puedes dejar invertido?
           - Corto plazo: 6-12 meses
           - Medio plazo: 1-3 años
           - Largo plazo: >3 años

        2. **Monto Disponible**: ¿Cuánto capital tienes para invertir?
           - Minimo recomendado: USD 1,000
           - Considere mantener emergencia: 3-6 meses gastos

        3. **Retorno Objetivo**: ¿Cuánto esperas ganar anualmente?
           - Conservador: 3-5%
           - Moderado: 6-9%
           - Agresivo: 10-15%+

        4. **Tolerancia al Riesgo**: ¿Cuánta volatilidad puedes soportar?
        """)

    with info_tab3:
        st.markdown("""
        ### Riesgos y Consideraciones

        **Riesgos Principales:**
        - **Riesgo de Mercado**: Fluctuaciones en precio de activos
        - **Riesgo de Crédito**: Incapacidad del emisor de pagar
        - **Riesgo de Liquidez**: Dificultad para vender rápido
        - **Riesgo de Inflación**: Pérdida de poder adquisitivo

        **Guardrails Implementados:**
        ✅ Límites de asignación por perfil de riesgo
        ✅ Validación de objetivos alcanzables
        ✅ Diversificación mínima requerida
        ✅ Disclaimer obligatorio antes de invertir

        **⚠️ Descargo de Responsabilidad:**
        Esta es una **herramienta educativa**, no asesoría profesional.
        Consult con un asesor financiero certificado antes de invertir.
        """)

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.9em; margin-top: 2rem;'>
    <p>FinAdvisor v1.0 | Asesor Financiero Impulsado por IA</p>
    <p>Para soporte, ver documentación: <a href='#'>DEPLOYMENT_GUIDE.md</a></p>
</div>
""", unsafe_allow_html=True)
