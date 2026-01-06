"""
Financial advisor guardrails and compliance rules
Ensures recommendations meet regulatory and safety requirements
"""

from typing import Dict, Tuple, List
from dataclasses import dataclass


@dataclass
class GuardrailViolation:
    severity: str  # "warning", "error"
    rule: str
    message: str
    action: str  # "proceed", "clarify", "escalate"


class FinancialGuardrails:
    """Enforce compliance and safety guardrails"""

    # Risk profile allocation limits
    PROFILE_LIMITS = {
        "conservador": {
            "conservador": (70, 100),  # Minimum 70% in conservative products
            "moderado": (0, 30),        # Maximum 30% in moderate products
            "agresivo": (0, 0)          # NO aggressive products for conservative profile
        },
        "moderado": {
            "conservador": (20, 60),
            "moderado": (30, 70),       # Increased minimum for moderate products
            "agresivo": (0, 30)         # Reduced max for aggressive products
        },
        "agresivo": {
            "conservador": (0, 30),
            "moderado": (10, 40),
            "agresivo": (40, 80)        # Increased minimum for aggressive products
        }
    }

    # Capital thresholds
    HIGH_CAPITAL_THRESHOLD = 100000  # USD
    RECOMMENDATION_THRESHOLD = 50000  # USD

    @staticmethod
    def validate_recommendation(
        client_profile: Dict,
        portfolio_allocation: List[Dict],
        expected_return: float
    ) -> Tuple[bool, List[GuardrailViolation]]:
        """
        Validate portfolio recommendation against all guardrails
        Returns (is_valid, list_of_violations)
        """

        violations = []

        # 1. Check allocation limits by profile
        risk_profile = client_profile.get("risk_profile", "moderado")
        limits = FinancialGuardrails.PROFILE_LIMITS.get(risk_profile, {})

        for alloc in portfolio_allocation:
            product_type = alloc.get("product_type", "moderado")
            percentage = alloc.get("percentage", 0)

            if product_type in limits:
                min_pct, max_pct = limits[product_type]
                if percentage < min_pct or percentage > max_pct:
                    violations.append(GuardrailViolation(
                        severity="warning",
                        rule="allocation_limits",
                        message=f"{product_type} allocation {percentage}% outside limits {min_pct}-{max_pct}%",
                        action="clarify"
                    ))

        # 2. Check high capital + novice investor
        amount = client_profile.get("available_amount_usd", 0)
        is_novice = client_profile.get("investment_experience", "low") == "low"
        is_high_risk = risk_profile == "agresivo"

        if (amount > FinancialGuardrails.HIGH_CAPITAL_THRESHOLD and
            is_novice and is_high_risk):
            violations.append(GuardrailViolation(
                severity="error",
                rule="high_capital_novice_aggressive",
                message=f"High capital (${amount:,.0f}) + novice investor + aggressive profile = escalate to advisor",
                action="escalate"
            ))

        # 3. Check return feasibility
        client_target = client_profile.get("target_return_pct", 0)
        if expected_return < client_target * 0.95:
            violations.append(GuardrailViolation(
                severity="warning",
                rule="return_feasibility",
                message=f"Portfolio return {expected_return:.2%} below target {client_target:.2%}",
                action="clarify"
            ))

        # 4. Check liquidity vs horizon mismatch
        horizon_months = client_profile.get("investment_horizon_months", 24)
        liquidity_pref = client_profile.get("liquidity_preference", "media")

        if horizon_months < 12 and liquidity_pref != "alta":
            violations.append(GuardrailViolation(
                severity="warning",
                rule="liquidity_horizon_mismatch",
                message=f"Short horizon ({horizon_months}m) with {liquidity_pref} liquidity preference",
                action="clarify"
            ))

        # 5. Add mandatory disclaimer
        violations.append(GuardrailViolation(
            severity="warning",
            rule="mandatory_disclaimer",
            message="DISCLAIMER: This is an educational recommendation, not investment advice. Verify with licensed advisor.",
            action="proceed"
        ))

        # Check if any error-level violations
        is_valid = not any(v.severity == "error" for v in violations)
        return (is_valid, violations)

    @staticmethod
    def needs_human_escalation(
        violations: List[GuardrailViolation]
    ) -> bool:
        """Check if recommendation needs human escalation"""
        return any(v.action == "escalate" for v in violations)

    @staticmethod
    def generate_disclaimer() -> str:
        """Generate mandatory disclaimer text"""
        return """
⚠️ AVISO IMPORTANTE:
- Esta es una RECOMENDACIÓN EDUCATIVA basada en tu perfil y objetivos.
- NO es consejo financiero profesional. No constituye una oferta de compra/venta.
- Debes verificar con un asesor certificado antes de invertir.
- Los retornos históricos no garantizan resultados futuros.
- Siempre lee los prospectos de cada producto financiero.
- Tu capital está sujeto a riesgo. No hay garantía de retorno.
- Esta recomendación se basa en datos al {date}. Puede cambiar.
- Riesgo de liquidez: algunos productos pueden no ser liquidables rápidamente.
        """

    @staticmethod
    def generate_explanation(
        portfolio_allocation: List[Dict],
        expected_return: float,
        expected_risk: str,
        client_profile: Dict
    ) -> str:
        """
        Generate educational explanation of the recommendation
        Following the Goal-Based Reflex Agent reasoning format
        """

        explanation = f"""
## Por qué esta cartera te conviene

### Tu Situación (Estado Inicial):
- Monto disponible: ${client_profile.get('available_amount_usd'):,.0f}
- Horizonte de inversión: {client_profile.get('investment_horizon_months')} meses
- Perfil de riesgo: {client_profile.get('risk_profile')} (preferencia liquidez: {client_profile.get('liquidity_preference')})
- Objetivo de retorno: {client_profile.get('target_return_pct'):.1%} anual

### Tus Metas Financieras:
- Retorno mínimo esperado: ≥ {client_profile.get('target_return_pct'):.1%} anual
- Riesgo aceptable: {expected_risk}
- Liquidez necesaria: {client_profile.get('liquidity_preference')}

### Estrategia Propuesta (Simulación de Escenarios):
La cartera que te recomendamos logra un equilibrio entre tus objetivos:

"""
        for alloc in portfolio_allocation:
            explanation += f"""
- **{alloc.get('product_name')}** ({alloc.get('percentage'):.0f}%)
  - Monto: ${alloc.get('amount'):,.0f}
  - Retorno esperado: {alloc.get('annual_rate'):.2%}
  - Características: {alloc.get('liquidity', 'media')} liquidez
"""

        explanation += f"""

### Métricas de la Cartera:
- **Retorno esperado**: {expected_return:.2%} anual (vs tu objetivo {client_profile.get('target_return_pct'):.1%}%)
- **Riesgo estimado**: {expected_risk}
- **Liquidez**: {client_profile.get('liquidity_preference')}

### Por qué esta combinación:
1. **Diversificación**: Combina productos conservadores (estabilidad) con moderados (crecimiento)
2. **Cumplimiento de metas**: Alcanza tu objetivo de retorno manteniendo tu perfil de riesgo
3. **Respeto a preferencias**: Se respetan los límites de tu perfil de riesgo ({client_profile.get('risk_profile')})
4. **Flexibilidad**: Todos los productos tienen opciones de recompra en caso de necesidad

### Próximos Pasos:
1. Revisa el prospecto de cada producto
2. Consulta con tu asesor financiero si tienes dudas
3. Una vez confirmado, podemos proceder con la inversión inicial
4. Revisaremos trimestralmente si el mercado cambia significativamente

¿Tienes preguntas o deseas ajustar algo?
        """

        return explanation

    @staticmethod
    def validate_data_sufficiency(
        client_profile: Dict
    ) -> Tuple[bool, str]:
        """
        Validate if we have enough data to make a recommendation
        Returns (is_sufficient, clarification_needed)
        """

        required_fields = [
            "risk_profile",
            "available_amount_usd",
            "investment_horizon_months",
            "target_return_pct"
        ]

        missing = [f for f in required_fields if f not in client_profile or client_profile[f] is None]

        if missing:
            return (False, f"Necesito clarificar: {', '.join(missing)}")

        # Additional validation
        if client_profile.get("available_amount_usd", 0) < 1000:
            return (False, "Monto mínimo requerido: $1,000 USD")

        if client_profile.get("investment_horizon_months", 0) < 6:
            return (False, "Horizonte mínimo recomendado: 6 meses")

        return (True, "")
